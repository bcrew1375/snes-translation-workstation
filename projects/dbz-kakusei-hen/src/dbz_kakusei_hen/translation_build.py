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
    "selector": int,
    "reference_address": str,
    "reference_offset": int,
    "pointer_format": str,
    "original_address": str,
    "original_offset": int,
    "original_length": int,
    "source_sha256": str,
    "english": list,
    "status": str,
    "notes": str,
}
PATCH_OPTIONAL_FIELDS = {
    "max_line_length": int,
    "alias_selectors": list,
    "preserve_source_line_layout": bool,
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
    """One self-contained translated command-$08 text record."""

    id: str
    selector: int
    original_bank: int
    original_address: int
    original_offset: int
    original_length: int
    source_sha256: str
    english: tuple[str, ...]
    max_line_length: int | None
    alias_selectors: tuple[int, ...]
    status: str
    notes: str
    reference_offset: int
    pointer_format: str
    preserve_source_line_layout: bool = False


@dataclass(frozen=True)
class TranslationPlan:
    record: TranslationRecord
    slot: TextSelectorSlot
    alias_slots: tuple[TextSelectorSlot, ...]
    source_stream: TextStream
    encoded: EncodedText
    allocation: Allocation

    @property
    def needs_pointer_update(self) -> bool:
        return self.allocation.strategy != "in-place" or bool(self.alias_slots)


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


def source_dialogue_box_count(stream: TextStream, *, lines_per_box: int = 4) -> int:
    """Return the source stream's four-line dialogue-box count."""

    if lines_per_box < 1:
        raise ValueError("lines per dialogue box must be positive")
    return (len(stream.line_lengths) + lines_per_box - 1) // lines_per_box


def validate_dialogue_box_count(
    record: TranslationRecord, stream: TextStream, *, lines_per_box: int = 4
) -> None:
    """Preserve source box count without creating invisible input prompts."""

    source_boxes = source_dialogue_box_count(stream, lines_per_box=lines_per_box)
    english_boxes = (len(record.english) + lines_per_box - 1) // lines_per_box
    if english_boxes != source_boxes:
        raise WorkstationError(
            f"{record.id} selector ${record.selector:04X} uses {english_boxes} English "
            f"dialogue boxes; source uses {source_boxes}"
        )
    for box_index in range(source_boxes):
        start = box_index * lines_per_box
        source_lines = stream.line_lengths[start:start + lines_per_box]
        english_lines = record.english[start:start + lines_per_box]
        if any(source_lines) and not any(line.strip() for line in english_lines):
            raise WorkstationError(
                f"{record.id} selector ${record.selector:04X} English dialogue box "
                f"{box_index + 1} is blank but the source box contains visible text"
            )

    if record.preserve_source_line_layout:
        source_layout = tuple(bool(length) for length in stream.line_lengths)
        english_layout = tuple(bool(line.strip()) for line in record.english)
        if english_layout != source_layout:
            raise WorkstationError(
                f"{record.id} selector ${record.selector:04X} must preserve source "
                f"line layout {source_layout}; English uses {english_layout}"
            )


def load_translation_manifests(patches_path: str | Path) -> list[TranslationRecord]:
    """Load self-contained command-$08 translation manifests."""

    patches = read_manifest_collection(
        patches_path, PATCH_FIELDS, optional_fields=PATCH_OPTIONAL_FIELDS
    )
    records = []
    seen: set[str] = set()
    for patch in patches:
        identifier = patch["id"]
        if identifier in seen:
            raise WorkstationError(f"duplicate patch id {identifier!r}")
        seen.add(identifier)
        selector = _hex(patch["selector"], f"{identifier} selector")
        reference_bank, reference_address = parse_cpu_address(
            patch["reference_address"].removeprefix("$")
        )
        reference_offset = _hex(
            patch["reference_offset"], f"{identifier} reference offset"
        )
        if cpu_to_offset(reference_bank, reference_address, "lorom") != reference_offset:
            raise WorkstationError(
                f"reference address and offset disagree for {identifier!r}"
            )
        bank, address = parse_cpu_address(patch["original_address"].removeprefix("$"))
        offset = _hex(patch["original_offset"], f"{identifier} original offset")
        try:
            length = manifest_int(patch["original_length"], f"{identifier} original length")
        except WorkstationError as error:
            raise WorkstationError(f"invalid original length for {identifier!r}") from error
        english = patch["english"]
        if not english:
            raise WorkstationError(f"patch {identifier!r} has an empty English line array")
        if any(not isinstance(line, str) for line in english):
            raise WorkstationError(f"patch {identifier!r} has a non-string English line")
        if not any(line.strip() for line in english):
            raise WorkstationError(f"patch {identifier!r} has no nonblank English lines")
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
        raw_aliases = patch.get("alias_selectors", [])
        alias_selectors = tuple(
            _hex(value, f"{identifier} alias selector") for value in raw_aliases
        )
        if len(set(alias_selectors)) != len(alias_selectors):
            raise WorkstationError(f"patch {identifier!r} repeats an alias selector")
        if selector in alias_selectors:
            raise WorkstationError(f"patch {identifier!r} aliases its primary selector")
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
                alias_selectors=alias_selectors,
                status=patch["status"],
                notes=patch["notes"],
                reference_offset=reference_offset,
                pointer_format=patch["pointer_format"],
                preserve_source_line_layout=patch.get("preserve_source_line_layout", False),
            )
        )
    return records


def load_translations_from_tsv(tsv_path: str | Path) -> list[TranslationRecord]:
    """Reject the old unsafe single-manifest API with actionable guidance."""

    raise WorkstationError(
        f"{tsv_path} is obsolete; load the self-contained TOML patch collection"
    )


def load_reviewed_free_regions(ranges_path: str | Path) -> list[FreeSpaceRegion]:
    """Load only ranges explicitly named and reviewed as text free space.

    Existing translated-stream and glyph-storage ranges are intentionally not
    allocation pools. A future allocation range must use a ``free_text_`` name,
    ``confirmed`` confidence, and half-open conversion of its inclusive manifest end.
    """

    rows = read_manifest_collection(ranges_path, RANGE_FIELDS)
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
    implemented = [record for record in records if record.status == "implemented"]
    claimed_selectors = [
        selector
        for record in implemented
        for selector in (record.selector, *record.alias_selectors)
    ]
    if len(set(claimed_selectors)) != len(claimed_selectors):
        raise WorkstationError("implemented translation records repeat a selector or alias")

    validated: list[
        tuple[
            TranslationRecord,
            TextSelectorSlot,
            tuple[TextSelectorSlot, ...],
            TextStream,
            EncodedText,
        ]
    ] = []
    source_selectors: dict[tuple[int, int], set[int]] = {}
    for slot in slots:
        if not slot.is_null:
            key = (slot.pointer_bank, slot.target_address)
            source_selectors.setdefault(key, set()).add(slot.selector)
    for record in implemented:
        if not 0 <= record.selector < len(slots):
            raise WorkstationError(f"selector ${record.selector:04X} is outside the text tables")
        slot = slots[record.selector]
        stream = _validate_record(original, record, slot)
        alias_slots = []
        for alias_selector in record.alias_selectors:
            if not 0 <= alias_selector < len(slots):
                raise WorkstationError(
                    f"alias selector ${alias_selector:04X} for {record.id} is outside the text tables"
                )
            alias_slot = slots[alias_selector]
            if alias_slot.is_null:
                raise WorkstationError(
                    f"alias selector ${alias_selector:04X} for {record.id} is null"
                )
            alias_stream = decode_text_stream(
                original,
                bank=alias_slot.pointer_bank,
                address=alias_slot.target_address,
                selectors=(alias_selector,),
            )
            if alias_stream.data != stream.data:
                raise WorkstationError(
                    f"alias selector ${alias_selector:04X} for {record.id} does not contain "
                    f"the same source stream as ${record.selector:04X}"
                )
            alias_slots.append(alias_slot)
        validate_visible_line_width(record, slot.presentation)
        validate_dialogue_box_count(record, stream)
        encoded = encode_text_layout(
            "\n".join(record.english),
            max_line_width=slot.presentation.width_cells,
            max_lines=source_dialogue_box_count(stream) * 4,
            context=f"{record.id} selector ${record.selector:04X}",
        )
        validated.append((record, slot, tuple(alias_slots), stream, encoded))

    allocation_regions = list(free_regions)
    force_relocations: dict[int, bool] = {}
    for record, slot, alias_slots, stream, encoded in validated:
        key = (stream.bank, stream.address)
        claimed = {record.selector, *(alias.selector for alias in alias_slots)}
        force_relocation = not source_selectors[key] <= claimed
        force_relocations[record.selector] = force_relocation
        if not force_relocation:
            if len(encoded.data) < record.original_length:
                allocation_regions.append(
                    FreeSpaceRegion(
                        bank=slot.pointer_bank,
                        rom_start=record.original_offset + len(encoded.data),
                        rom_end=record.original_offset + record.original_length,
                        alignment=2,
                        name=f"compact suffix of {record.id}",
                    )
                )
            elif len(encoded.data) > record.original_length:
                allocation_regions.append(
                    FreeSpaceRegion(
                        bank=slot.pointer_bank,
                        rom_start=record.original_offset,
                        rom_end=record.original_offset + record.original_length,
                        alignment=2,
                        name=f"vacated source of {record.id}",
                        priority=1,
                    )
                )

    allocator = StreamAllocator(allocation_regions)
    indexed_validated = list(enumerate(validated))

    def allocation_order(item):
        index, (record, _slot, _alias_slots, _stream, encoded) = item
        needs_relocation = (
            force_relocations[record.selector]
            or len(encoded.data) > record.original_length
        )
        return (not needs_relocation, -len(encoded.data) if needs_relocation else 0, index)

    allocations: dict[int, Allocation] = {}
    for index, (record, slot, _alias_slots, _stream, encoded) in sorted(
        indexed_validated, key=allocation_order
    ):
        allocation = allocator.allocate(
            selector=record.selector,
            original_offset=record.original_offset,
            original_length=record.original_length,
            new_length=len(encoded.data),
            bank=slot.pointer_bank,
            force_relocation=force_relocations[record.selector],
        )
        if not validate_allocation(allocation, len(original)):
            raise WorkstationError(f"invalid allocation for {record.id}")
        allocations[index] = allocation

    plans = [
        TranslationPlan(record, slot, alias_slots, stream, encoded, allocations[index])
        for index, (record, slot, alias_slots, stream, encoded) in indexed_validated
    ]

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
        for slot in (plan.slot, *plan.alias_slots):
            write_pointer(
                rom,
                slot.selector,
                new_address,
                slots=(slot,),
                expected_target_address=slot.target_address,
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
            for slot in (plan.slot, *plan.alias_slots):
                write_pointer(
                    rom,
                    slot.selector,
                    new_address,
                    slots=(slot,),
                    expected_target_address=slot.target_address,
                )

    for plan in plans:
        address = 0x8000 + (plan.allocation.new_offset & 0x7FFF)
        decoded = decode_text_stream(
            bytes(rom), bank=plan.allocation.bank, address=address,
            selectors=(plan.record.selector,),
        )
        if decoded.data != plan.encoded.data or decoded.line_lengths != plan.encoded.line_cells:
            raise WorkstationError(f"{plan.record.id} failed the post-write decode round trip")
        for alias_slot in plan.alias_slots:
            alias_target = decode_text_slots(bytes(rom))[alias_slot.selector]
            if alias_target.target_offset != plan.allocation.new_offset:
                raise WorkstationError(
                    f"{plan.record.id} alias selector ${alias_slot.selector:04X} "
                    "does not resolve to the translated allocation"
                )

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