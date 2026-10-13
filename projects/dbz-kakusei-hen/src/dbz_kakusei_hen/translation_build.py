"""Validated planning and application of Kakusei Hen text translations."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from snesworkbench.errors import WorkstationError
from snesworkbench.manifests import manifest_int, read_manifest, read_manifest_collection
from snesworkbench.patching import BuildResult, bounded_write, changed_offsets, sha256, write_snes_checksum
from snesworkbench.rom import cpu_to_offset, parse_cpu_address

from .allocator import (
    Allocation,
    CandidateGap,
    FreeSpaceRegion,
    StreamAllocator,
    validate_allocation,
)
from .glyphs import EncodedText, encode_text_layout
from .pointer_update import write_pointer
from .scenario import (
    TEXT_PRESENTATION_ADDRESS,
    TEXT_PRESENTATION_BANK,
    TEXT_PRESENTATION_FIRST_SELECTOR,
    TEXT_SELECTOR_LAST,
    TEXT_TABLE_RANGES,
    TextPresentation,
    TextSelectorSlot,
    TextStream,
    decode_text_slots,
    decode_text_stream,
    decode_unique_text_streams,
    glyph_source,
)


PATCH_FIELDS = {
    "id": str,
    "original_address": str,
    "original_offset": int,
    "original_length": int,
    "source_sha256": str,
    "english": list,
    "status": str,
    "notes": str,
}
PATCH_OPTIONAL_FIELDS = {"max_line_length": int}
REFERENCE_FIELDS = {
    "id": str,
    "reference_type": str,
    "reference_address": str,
    "reference_offset": int,
    "message_index": int,
    "pointer_format": str,
    "target_address": str,
    "target_offset": int,
}
RANGE_FIELDS = {
    "name": str,
    "rom_start": int,
    "rom_end": int,
    "cpu_start": str,
    "cpu_end": str,
    "bank": int,
    "alignment": int,
    "evidence": str,
    "confidence": str,
}


def _hex(value: object, field: str) -> int:
    return manifest_int(value, field, hexadecimal=True)


@dataclass(frozen=True)
class TranslationRecord:
    """One patch joined to its authoritative selector reference."""

    id: str
    selector: int
    original_bank: int
    original_address: int
    original_offset: int
    original_length: int
    source_sha256: str
    english: tuple[str, ...]
    max_line_length: int | None
    status: str
    notes: str
    reference_offset: int
    pointer_format: str


@dataclass(frozen=True)
class TranslationPlan:
    record: TranslationRecord
    slot: TextSelectorSlot
    source_stream: TextStream
    encoded: EncodedText
    allocation: Allocation

    @property
    def needs_pointer_update(self) -> bool:
        return self.allocation.strategy != "in-place"


def visible_line_character_limit(presentation: TextPresentation) -> int | None:
    """Return the confirmed packed-Latin visual width for a presentation."""

    if presentation.kind == "wide_marker":
        return 28
    if presentation.kind == "context_pair":
        return 21
    return None


def validate_visible_line_width(
    record: TranslationRecord, presentation: TextPresentation
) -> None:
    """Reject authored lines that would wrap mid-word in the visible text box."""

    confirmed_limit = visible_line_character_limit(presentation)
    if confirmed_limit is None:
        if record.max_line_length is not None:
            raise WorkstationError(
                f"{record.id} selector ${record.selector:04X} has unconfirmed "
                f"{presentation.kind} presentation and must omit max_line_length"
            )
        return
    if record.max_line_length is None:
        raise WorkstationError(
            f"{record.id} selector ${record.selector:04X} uses {presentation.kind} "
            f"presentation and must declare max_line_length = {confirmed_limit}"
        )
    if record.max_line_length != confirmed_limit:
        raise WorkstationError(
            f"{record.id} selector ${record.selector:04X} declares max_line_length = "
            f"{record.max_line_length}; {presentation.kind} requires {confirmed_limit}"
        )
    for line_number, line in enumerate(record.english, start=1):
        if len(line) > confirmed_limit:
            raise WorkstationError(
                f"{record.id} selector ${record.selector:04X} line {line_number} "
                f"has {len(line)} characters; {presentation.kind} permits {confirmed_limit}"
            )


def load_translation_manifests(
    patches_path: str | Path, references_path: str | Path
) -> list[TranslationRecord]:
    """Join tracked patch and reference manifests by stable ``id``."""

    patches = read_manifest_collection(
        patches_path, PATCH_FIELDS, optional_fields=PATCH_OPTIONAL_FIELDS
    )
    references = read_manifest(references_path, REFERENCE_FIELDS)
    by_id: dict[str, dict[str, str]] = {}
    for reference in references:
        if reference["reference_type"] != "command_08_selector":
            continue
        identifier = reference["id"]
        if identifier in by_id:
            raise WorkstationError(f"duplicate reference id {identifier!r}")
        by_id[identifier] = reference

    records = []
    seen: set[str] = set()
    for patch in patches:
        identifier = patch["id"]
        if identifier in seen:
            raise WorkstationError(f"duplicate patch id {identifier!r}")
        seen.add(identifier)
        try:
            reference = by_id.pop(identifier)
        except KeyError as error:
            raise WorkstationError(f"patch {identifier!r} has no reference record") from error
        selector = _hex(reference["message_index"], f"{identifier} selector")
        bank, address = parse_cpu_address(patch["original_address"].removeprefix("$"))
        target_bank, target_address = parse_cpu_address(reference["target_address"].removeprefix("$"))
        offset = _hex(patch["original_offset"], f"{identifier} original offset")
        target_offset = _hex(reference["target_offset"], f"{identifier} target offset")
        if (bank, address, offset) != (target_bank, target_address, target_offset):
            raise WorkstationError(f"patch and reference locations disagree for {identifier!r}")
        try:
            length = manifest_int(patch["original_length"], f"{identifier} original length")
        except WorkstationError as error:
            raise WorkstationError(f"invalid original length for {identifier!r}") from error
        english = patch["english"]
        if not english:
            raise WorkstationError(f"patch {identifier!r} has an empty English line array")
        if any(not isinstance(line, str) for line in english):
            raise WorkstationError(f"patch {identifier!r} has a non-string English line")
        if any("\n" in line or "\r" in line for line in english):
            raise WorkstationError(f"patch {identifier!r} has an embedded English line break")
        max_line_length = patch.get("max_line_length")
        if max_line_length is not None and max_line_length not in {21, 28}:
            raise WorkstationError(
                f"patch {identifier!r} has invalid max_line_length {max_line_length!r}"
            )
        if max_line_length is not None:
            for line_number, line in enumerate(english, start=1):
                if len(line) > max_line_length:
                    raise WorkstationError(
                        f"patch {identifier!r} line {line_number} has {len(line)} characters; "
                        f"max_line_length is {max_line_length}"
                    )
        records.append(
            TranslationRecord(
                id=identifier,
                selector=selector,
                original_bank=bank,
                original_address=address,
                original_offset=offset,
                original_length=length,
                source_sha256=patch["source_sha256"],
                english=tuple(english),
                max_line_length=max_line_length,
                status=patch["status"],
                notes=patch["notes"],
                reference_offset=_hex(reference["reference_offset"], f"{identifier} reference offset"),
                pointer_format=reference["pointer_format"],
            )
        )
    if by_id:
        raise WorkstationError(f"reference {sorted(by_id)[0]!r} has no patch record")
    return records


def load_translations_from_tsv(tsv_path: str | Path) -> list[TranslationRecord]:
    """Reject the old unsafe single-manifest API with actionable guidance."""

    raise WorkstationError(
        f"{tsv_path} does not contain selectors; load patches.tsv and references.tsv together"
    )


def load_reviewed_free_regions(ranges_path: str | Path) -> list[FreeSpaceRegion]:
    """Load only ranges explicitly named and reviewed as text free space.

    Existing translated-stream and glyph-storage ranges are intentionally not
    allocation pools. A future allocation range must use a ``free_text_`` name,
    ``confirmed`` confidence, and half-open conversion of its inclusive manifest end.
    """

    rows = read_manifest(ranges_path, RANGE_FIELDS)
    regions = []
    for row in rows:
        if not row["name"].startswith("free_text_"):
            continue
        if row["confidence"] != "confirmed":
            raise WorkstationError(
                f"allocation range {row['name']!r} is not confirmed"
            )
        bank = _hex(row["bank"], f"{row['name']} bank")
        start = _hex(row["rom_start"], f"{row['name']} ROM start")
        end = _hex(row["rom_end"], f"{row['name']} ROM end") + 1
        try:
            alignment = manifest_int(row["alignment"], f"{row['name']} alignment")
        except WorkstationError as error:
            raise WorkstationError(f"invalid alignment for {row['name']!r}") from error
        regions.append(
            FreeSpaceRegion(bank, start, end, alignment, row["name"])
        )
    return regions


def map_unverified_candidate_gaps(original: bytes, minimum_size: int = 64) -> list[CandidateGap]:
    """Report structural gaps without authorizing them for allocation."""

    if minimum_size < 1:
        raise WorkstationError("candidate-gap minimum size must be positive")
    slots = decode_text_slots(original)
    streams = decode_unique_text_streams(original, slots)
    banks = sorted({table.bank for table in TEXT_TABLE_RANGES})
    occupied: dict[int, list[tuple[int, int]]] = {bank: [] for bank in banks}
    for stream in streams:
        occupied[stream.bank].append((stream.offset, stream.end_offset))
    for table in TEXT_TABLE_RANGES:
        start = cpu_to_offset(table.bank, table.address, "lorom")
        occupied[table.bank].append((start, start + table.count * 2))
    presentation_start = cpu_to_offset(
        TEXT_PRESENTATION_BANK, TEXT_PRESENTATION_ADDRESS, "lorom"
    )
    presentation_size = (
        TEXT_SELECTOR_LAST - TEXT_PRESENTATION_FIRST_SELECTOR + 1
    ) * 2
    occupied[TEXT_PRESENTATION_BANK].append(
        (presentation_start, presentation_start + presentation_size)
    )

    gaps = []
    for bank in banks:
        bank_start = (bank & 0x7F) * 0x8000
        bank_end = min(bank_start + 0x8000, len(original))
        merged: list[list[int]] = []
        for start, end in sorted(occupied[bank]):
            start = max(start, bank_start)
            end = min(end, bank_end)
            if start >= end:
                continue
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        cursor = bank_start
        for start, end in merged:
            if start - cursor >= minimum_size:
                gaps.append(CandidateGap(bank, cursor, start))
            cursor = max(cursor, end)
        if bank_end - cursor >= minimum_size:
            gaps.append(CandidateGap(bank, cursor, bank_end))
    return gaps


def _reserved_text_intervals(original: bytes) -> list[tuple[int, int, str]]:
    slots = decode_text_slots(original)
    intervals = [
        (stream.offset, stream.end_offset, f"text stream {stream.cpu_address}")
        for stream in decode_unique_text_streams(original, slots)
    ]
    for table in TEXT_TABLE_RANGES:
        start = cpu_to_offset(table.bank, table.address, "lorom")
        intervals.append((start, start + table.count * 2, "text pointer table"))
    presentation_start = cpu_to_offset(
        TEXT_PRESENTATION_BANK, TEXT_PRESENTATION_ADDRESS, "lorom"
    )
    presentation_size = (
        TEXT_SELECTOR_LAST - TEXT_PRESENTATION_FIRST_SELECTOR + 1
    ) * 2
    intervals.append(
        (
            presentation_start,
            presentation_start + presentation_size,
            "text presentation table",
        )
    )
    return intervals


def validate_reviewed_free_regions(
    original: bytes, regions: list[FreeSpaceRegion]
) -> None:
    """Reject reviewed regions that collide with any confirmed text structure."""

    for region in regions:
        for start, end, description in _reserved_text_intervals(original):
            if region.rom_start < end and start < region.rom_end:
                raise WorkstationError(
                    f"allocation range {region.name!r} overlaps {description} at "
                    f"ROM ${max(region.rom_start, start):06X}"
                )


def _validate_record(
    original: bytes,
    record: TranslationRecord,
    slot: TextSelectorSlot,
) -> TextStream:
    if record.pointer_format != "16-bit same-bank LoROM pointer":
        raise WorkstationError(f"unsupported pointer format for {record.id}: {record.pointer_format!r}")
    if slot.is_null:
        raise WorkstationError(f"{record.id} selector ${record.selector:04X} is null")
    if slot.pointer_bank != record.original_bank or slot.target_address != record.original_address:
        raise WorkstationError(f"{record.id} no longer resolves to its recorded source address")
    if slot.pointer_offset != record.reference_offset or slot.target_offset != record.original_offset:
        raise WorkstationError(f"{record.id} recorded ROM offsets do not match the selector table")
    stream = decode_text_stream(
        original, bank=slot.pointer_bank, address=slot.target_address,
        selectors=(record.selector,),
    )
    if len(stream.data) != record.original_length:
        raise WorkstationError(
            f"{record.id} source length is {len(stream.data)}; expected {record.original_length}"
        )
    if hashlib.sha256(stream.data).hexdigest() != record.source_sha256:
        raise WorkstationError(f"{record.id} source SHA-256 does not match the supported ROM")
    return stream


def plan_translations(
    original: bytes,
    records: list[TranslationRecord],
    free_regions: list[FreeSpaceRegion],
) -> list[TranslationPlan]:
    """Validate and allocate every implemented record without modifying the ROM."""

    validate_reviewed_free_regions(original, free_regions)
    slots = decode_text_slots(original)
    allocator = StreamAllocator(free_regions)
    implemented = [record for record in records if record.status == "implemented"]
    if len({record.selector for record in implemented}) != len(implemented):
        raise WorkstationError("implemented translation records repeat a selector")

    validated: list[tuple[TranslationRecord, TextSelectorSlot, TextStream, EncodedText]] = []
    source_alias_counts: dict[tuple[int, int], int] = {}
    for slot in slots:
        if not slot.is_null:
            key = (slot.pointer_bank, slot.target_address)
            source_alias_counts[key] = source_alias_counts.get(key, 0) + 1
    for record in implemented:
        if not 0 <= record.selector < len(slots):
            raise WorkstationError(f"selector ${record.selector:04X} is outside the text tables")
        slot = slots[record.selector]
        stream = _validate_record(original, record, slot)
        validate_visible_line_width(record, slot.presentation)
        lines = record.english
        needed_cells = tuple((len(line) + 1) // 2 for line in lines)
        exact_cells = None
        if (
            len(lines) == len(stream.line_lengths)
            and all(needed <= available for needed, available in zip(needed_cells, stream.line_lengths))
        ):
            exact_cells = stream.line_lengths
        encoded = encode_text_layout(
            "\n".join(record.english),
            max_line_width=slot.presentation.width_cells,
            max_lines=slot.presentation.height_cells,
            line_cells=exact_cells,
            context=f"{record.id} selector ${record.selector:04X}",
        )
        key = (stream.bank, stream.address)
        validated.append((record, slot, stream, encoded))

    plans: list[TranslationPlan] = []
    for record, slot, stream, encoded in validated:
        key = (stream.bank, stream.address)
        force_relocation = source_alias_counts[key] > 1
        allocation = allocator.allocate(
            selector=record.selector,
            original_offset=record.original_offset,
            original_length=record.original_length,
            new_length=len(encoded.data),
            bank=slot.pointer_bank,
            force_relocation=force_relocation,
        )
        if not validate_allocation(allocation, len(original)):
            raise WorkstationError(f"invalid allocation for {record.id}")
        plans.append(TranslationPlan(record, slot, stream, encoded, allocation))

    spans = sorted(
        (plan.allocation.new_offset, plan.allocation.end_offset, plan.record.id)
        for plan in plans
    )
    for left, right in zip(spans, spans[1:]):
        if right[0] < left[1]:
            raise WorkstationError(f"translation allocations overlap: {left[2]} and {right[2]}")
    return plans


def apply_translation(rom: bytearray, plan: TranslationPlan) -> None:
    bounded_write(rom, plan.allocation.new_offset, plan.encoded.data, plan.record.id)
    if plan.needs_pointer_update:
        new_address = 0x8000 + (plan.allocation.new_offset & 0x7FFF)
        write_pointer(
            rom,
            plan.record.selector,
            new_address,
            slots=(plan.slot,),
            expected_target_address=plan.record.original_address,
        )


def build_translation(
    original: bytes,
    records: list[TranslationRecord],
    free_regions: list[FreeSpaceRegion],
) -> BuildResult:
    plans = plan_translations(original, records, free_regions)
    rom = bytearray(original)
    for plan in plans:
        bounded_write(rom, plan.allocation.new_offset, plan.encoded.data, plan.record.id)
        if plan.needs_pointer_update:
            new_address = 0x8000 + (plan.allocation.new_offset & 0x7FFF)
            write_pointer(
                rom,
                plan.record.selector,
                new_address,
                expected_target_address=plan.record.original_address,
            )

    for plan in plans:
        address = 0x8000 + (plan.allocation.new_offset & 0x7FFF)
        decoded = decode_text_stream(
            bytes(rom), bank=plan.allocation.bank, address=address,
            selectors=(plan.record.selector,),
        )
        if decoded.data != plan.encoded.data or decoded.line_lengths != plan.encoded.line_cells:
            raise WorkstationError(f"{plan.record.id} failed the post-write decode round trip")

    write_snes_checksum(rom, 0x7FDE)
    translated = bytes(rom)
    return BuildResult(
        data=translated,
        sha256=sha256(translated),
        changed_offsets=changed_offsets(original, translated),
        metadata={
            "translated": True,
            "translation_count": len(plans),
            "allocations": [
                {
                    "id": plan.record.id,
                    "selector": f"${plan.record.selector:04X}",
                    "strategy": plan.allocation.strategy,
                    "bank": f"${plan.allocation.bank:02X}",
                    "offset": f"${plan.allocation.new_offset:06X}",
                    "length": plan.allocation.new_length,
                }
                for plan in plans
            ],
        },
    )