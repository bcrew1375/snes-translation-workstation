"""Validated translation of pointer-selected fixed text resources."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from snesworkbench.errors import WorkstationError
from snesworkbench.manifests import manifest_int, read_manifest
from snesworkbench.patching import bounded_write
from snesworkbench.rom import parse_cpu_address

from .glyphs import encode_latin_line
from .scenario import TEXT_TERMINATOR


FIXED_RESOURCE_FIELDS = {
    "id": str,
    "record_type": str,
    "button": str,
    "pointer_address": str,
    "pointer_offset": int,
    "original_address": str,
    "original_offset": int,
    "original_length": int,
    "source_sha256": str,
    "destination_address": str,
    "destination_offset": int,
    "prefix_words": int,
    "english": str,
    "status": str,
    "notes": str,
}


@dataclass(frozen=True)
class FixedResourceRecord:
    id: str
    record_type: str
    button: str
    pointer_bank: int
    pointer_address: int
    pointer_offset: int
    original_bank: int
    original_address: int
    original_offset: int
    original_length: int
    source_sha256: str
    destination_bank: int
    destination_address: int
    destination_offset: int
    prefix_words: int
    english: str
    status: str
    notes: str


def _hex(value: object, field: str) -> int:
    return manifest_int(value, field, hexadecimal=True)


def load_fixed_resource_records(path: str | Path) -> list[FixedResourceRecord]:
    rows = read_manifest(path, FIXED_RESOURCE_FIELDS)
    records = []
    seen: set[str] = set()
    for row in rows:
        identifier = row["id"]
        if identifier in seen:
            raise WorkstationError(f"duplicate fixed-resource record {identifier!r}")
        seen.add(identifier)
        pointer_bank, pointer_address = parse_cpu_address(row["pointer_address"].removeprefix("$"))
        original_bank, original_address = parse_cpu_address(row["original_address"].removeprefix("$"))
        destination_bank, destination_address = parse_cpu_address(
            row["destination_address"].removeprefix("$")
        )
        try:
            original_length = manifest_int(
                row["original_length"], f"{identifier} original length"
            )
            prefix_words = manifest_int(row["prefix_words"], f"{identifier} prefix words")
        except WorkstationError as error:
            raise WorkstationError(f"invalid numeric field for {identifier!r}") from error
        records.append(
            FixedResourceRecord(
                id=identifier,
                record_type=row["record_type"],
                button=row["button"],
                pointer_bank=pointer_bank,
                pointer_address=pointer_address,
                pointer_offset=_hex(row["pointer_offset"], f"{identifier} pointer offset"),
                original_bank=original_bank,
                original_address=original_address,
                original_offset=_hex(row["original_offset"], f"{identifier} original offset"),
                original_length=original_length,
                source_sha256=row["source_sha256"],
                destination_bank=destination_bank,
                destination_address=destination_address,
                destination_offset=_hex(row["destination_offset"], f"{identifier} destination offset"),
                prefix_words=prefix_words,
                english=row["english"],
                status=row["status"],
                notes=row["notes"],
            )
        )
    return records


def encode_fixed_resource(record: FixedResourceRecord, source: bytes) -> bytes:
    if record.original_length % 2:
        raise WorkstationError(f"{record.id} source length is not word-aligned")
    if record.prefix_words < 0 or record.prefix_words * 2 >= len(source):
        raise WorkstationError(f"{record.id} has an invalid preserved prefix")
    source_cells = record.original_length // 2 - record.prefix_words - 1
    needed_cells = (len(record.english) + 1) // 2
    cells = source_cells if needed_cells <= source_cells else needed_cells
    prefix = source[:record.prefix_words * 2]
    words = encode_latin_line(record.english, cells, context=record.id) + (TEXT_TERMINATOR,)
    return prefix + b"".join(word.to_bytes(2, "little") for word in words)


def apply_fixed_resource_translation(
    original: bytes, translated: bytes, records: list[FixedResourceRecord]
) -> bytes:
    patched = bytearray(translated)
    destinations: list[tuple[int, int, str]] = []
    for record in records:
        if record.status != "implemented":
            continue
        source = original[record.original_offset:record.original_offset + record.original_length]
        if len(source) != record.original_length:
            raise WorkstationError(f"{record.id} source range exceeds the ROM")
        if hashlib.sha256(source).hexdigest() != record.source_sha256:
            raise WorkstationError(f"{record.id} source SHA-256 does not match the supported ROM")
        for bank, address, offset, label in (
            (record.pointer_bank, record.pointer_address, record.pointer_offset, "pointer"),
            (record.original_bank, record.original_address, record.original_offset, "source"),
            (record.destination_bank, record.destination_address, record.destination_offset, "destination"),
        ):
            expected = (bank & 0x7F) * 0x8000 + (address & 0x7FFF)
            if expected != offset:
                raise WorkstationError(f"{record.id} {label} CPU address and ROM offset disagree")
        if record.pointer_bank != record.destination_bank:
            raise WorkstationError(f"{record.id} destination is not in the pointer's bank")
        expected_pointer = record.original_address.to_bytes(2, "little")
        if original[record.pointer_offset:record.pointer_offset + 2] != expected_pointer:
            raise WorkstationError(f"{record.id} pointer does not target its pinned source")
        encoded = encode_fixed_resource(record, source)
        destinations.append((record.destination_offset, record.destination_offset + len(encoded), record.id))
        bounded_write(patched, record.destination_offset, encoded, record.id)
        if record.destination_address != record.original_address:
            bounded_write(
                patched,
                record.pointer_offset,
                record.destination_address.to_bytes(2, "little"),
                f"{record.id} pointer",
            )
    ordered = sorted(destinations)
    for left, right in zip(ordered, ordered[1:]):
        if right[0] < left[1]:
            raise WorkstationError(f"fixed-resource destinations overlap: {left[2]} and {right[2]}")
    return bytes(patched)