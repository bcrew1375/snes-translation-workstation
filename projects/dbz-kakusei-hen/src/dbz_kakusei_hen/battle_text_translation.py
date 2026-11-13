"""Validated in-place translation of battle-script text resources."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from snesworkbench.errors import WorkstationError
from snesworkbench.manifests import manifest_int, read_manifest_collection
from snesworkbench.patching import bounded_write
from snesworkbench.rom import parse_cpu_address

from .glyphs import encode_latin_line
from .scenario import TEXT_LINE_BREAK, TEXT_TERMINATOR


BATTLE_TEXT_FIELDS = {
    "id": str,
    "path": str,
    "speaker": str,
    "resource_id": int,
    "pointer_address": str,
    "pointer_offset": int,
    "original_address": str,
    "original_offset": int,
    "original_length": int,
    "source_sha256": str,
    "english": list,
    "max_line_length": int,
    "status": str,
    "notes": str,
}


@dataclass(frozen=True)
class BattleTextRecord:
    id: str
    path: str
    speaker: str
    resource_id: int
    pointer_bank: int
    pointer_address: int
    pointer_offset: int
    original_bank: int
    original_address: int
    original_offset: int
    original_length: int
    source_sha256: str
    english: tuple[str, ...]
    max_line_length: int
    status: str
    notes: str


def _hex(value: object, field: str) -> int:
    return manifest_int(value, field, hexadecimal=True)


def load_battle_text_records(path: str | Path) -> list[BattleTextRecord]:
    rows = read_manifest_collection(path, BATTLE_TEXT_FIELDS)
    records = []
    seen_ids: set[str] = set()
    seen_resources: set[int] = set()
    for row in rows:
        identifier = row["id"]
        if identifier in seen_ids:
            raise WorkstationError(f"duplicate battle-text record {identifier!r}")
        seen_ids.add(identifier)
        resource_id = _hex(row["resource_id"], f"{identifier} resource id")
        if resource_id in seen_resources:
            raise WorkstationError(f"duplicate battle-text resource ${resource_id:04X}")
        seen_resources.add(resource_id)
        pointer_bank, pointer_address = parse_cpu_address(row["pointer_address"])
        original_bank, original_address = parse_cpu_address(row["original_address"])
        english = tuple(row["english"])
        if not english or any(not isinstance(line, str) for line in english):
            raise WorkstationError(f"{identifier} must contain explicit English lines")
        max_line_length = manifest_int(row["max_line_length"], f"{identifier} line limit")
        if max_line_length != 21:
            raise WorkstationError(f"{identifier} must use the confirmed 21-character limit")
        for line_number, line in enumerate(english, start=1):
            if "\n" in line or "\r" in line:
                raise WorkstationError(f"{identifier} line {line_number} contains a line break")
            if len(line) > max_line_length:
                raise WorkstationError(
                    f"{identifier} line {line_number} has {len(line)} characters; "
                    f"limit is {max_line_length}"
                )
        records.append(
            BattleTextRecord(
                id=identifier,
                path=row["path"],
                speaker=row["speaker"],
                resource_id=resource_id,
                pointer_bank=pointer_bank,
                pointer_address=pointer_address,
                pointer_offset=_hex(row["pointer_offset"], f"{identifier} pointer offset"),
                original_bank=original_bank,
                original_address=original_address,
                original_offset=_hex(row["original_offset"], f"{identifier} original offset"),
                original_length=manifest_int(row["original_length"], f"{identifier} source length"),
                source_sha256=row["source_sha256"],
                english=english,
                max_line_length=max_line_length,
                status=row["status"],
                notes=row["notes"],
            )
        )
    return records


def source_line_cells(source: bytes, *, context: str) -> tuple[int, ...]:
    if len(source) < 2 or len(source) % 2:
        raise WorkstationError(f"{context} source is not a terminated word stream")
    words = tuple(int.from_bytes(source[index:index + 2], "little") for index in range(0, len(source), 2))
    if words[-1] != TEXT_TERMINATOR or TEXT_TERMINATOR in words[:-1]:
        raise WorkstationError(f"{context} source terminator is not at the pinned end")
    lengths = [0]
    for word in words[:-1]:
        if word == TEXT_LINE_BREAK:
            lengths.append(0)
        elif word < 0x0100:
            raise WorkstationError(f"{context} contains unknown control word ${word:04X}")
        else:
            lengths[-1] += 1
    return tuple(lengths)


def encode_battle_text(record: BattleTextRecord, source: bytes) -> bytes:
    line_cells = source_line_cells(source, context=record.id)
    if len(record.english) != len(line_cells):
        raise WorkstationError(
            f"{record.id} has {len(record.english)} English lines; source has {len(line_cells)}"
        )
    words: list[int] = []
    for line_number, (line, cells) in enumerate(zip(record.english, line_cells, strict=True), start=1):
        words.extend(encode_latin_line(line, cells, context=f"{record.id} line {line_number}"))
        if line_number != len(line_cells):
            words.append(TEXT_LINE_BREAK)
    words.append(TEXT_TERMINATOR)
    encoded = b"".join(word.to_bytes(2, "little") for word in words)
    if len(encoded) != record.original_length:
        raise WorkstationError(f"{record.id} encoded length changed unexpectedly")
    return encoded


def apply_battle_text_translation(
    original: bytes, translated: bytes, records: list[BattleTextRecord]
) -> bytes:
    patched = bytearray(translated)
    for record in records:
        if record.status != "implemented":
            continue
        source = original[record.original_offset:record.original_offset + record.original_length]
        if len(source) != record.original_length:
            raise WorkstationError(f"{record.id} source range exceeds the ROM")
        if hashlib.sha256(source).hexdigest() != record.source_sha256:
            raise WorkstationError(f"{record.id} source SHA-256 does not match the supported ROM")
        expected_pointer_offset = (record.pointer_bank & 0x7F) * 0x8000 + (record.pointer_address & 0x7FFF)
        expected_source_offset = (record.original_bank & 0x7F) * 0x8000 + (record.original_address & 0x7FFF)
        if expected_pointer_offset != record.pointer_offset:
            raise WorkstationError(f"{record.id} pointer CPU address and ROM offset disagree")
        if expected_source_offset != record.original_offset:
            raise WorkstationError(f"{record.id} source CPU address and ROM offset disagree")
        expected_pointer_address = 0x8000 + (record.resource_id - 0x1000) * 2
        if (record.pointer_bank, record.pointer_address) != (0xB4, expected_pointer_address):
            raise WorkstationError(f"{record.id} pointer does not match resource ${record.resource_id:04X}")
        if record.original_bank != 0xB4:
            raise WorkstationError(f"{record.id} source is not in battle-text bank $B4")
        if original[record.pointer_offset:record.pointer_offset + 2] != record.original_address.to_bytes(2, "little"):
            raise WorkstationError(f"{record.id} pointer does not target its pinned source")
        bounded_write(patched, record.original_offset, encode_battle_text(record, source), record.id)
    return bytes(patched)