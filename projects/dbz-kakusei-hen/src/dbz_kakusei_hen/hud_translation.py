"""Validated in-place translation of the first battle HUD text sources."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from snesworkbench.errors import WorkstationError
from snesworkbench.manifests import manifest_int, read_manifest_collection
from snesworkbench.patching import bounded_write

from .glyphs import encode_latin_line


HUD_FIELDS = {
    "id": str,
    "original_offset": int,
    "original_length": int,
    "source_sha256": str,
    "patch_offsets": list,
    "english": str,
    "status": str,
    "notes": str,
}


@dataclass(frozen=True)
class HudTextRecord:
    id: str
    original_offset: int
    original_length: int
    source_sha256: str
    patch_offsets: tuple[int, ...]
    english: str
    status: str
    notes: str


def load_hud_text_records(path: str | Path) -> list[HudTextRecord]:
    records = []
    seen: set[str] = set()
    for row in read_manifest_collection(path, HUD_FIELDS):
        identifier = row["id"]
        if identifier in seen:
            raise WorkstationError(f"duplicate HUD text record {identifier!r}")
        seen.add(identifier)
        patch_offsets = tuple(
            manifest_int(value, f"{identifier} patch offset", hexadecimal=True)
            for value in row["patch_offsets"]
        )
        if not patch_offsets or len(set(patch_offsets)) != len(patch_offsets):
            raise WorkstationError(f"{identifier} must declare unique patch offsets")
        records.append(
            HudTextRecord(
                id=identifier,
                original_offset=manifest_int(
                    row["original_offset"], f"{identifier} original offset", hexadecimal=True
                ),
                original_length=manifest_int(
                    row["original_length"], f"{identifier} original length"
                ),
                source_sha256=row["source_sha256"],
                patch_offsets=patch_offsets,
                english=row["english"],
                status=row["status"],
                notes=row["notes"],
            )
        )
    return records


def encode_hud_text(record: HudTextRecord) -> bytes:
    words = encode_latin_line(record.english, len(record.patch_offsets), context=record.id)
    return b"".join(word.to_bytes(2, "little") for word in words)


def apply_hud_translation(
    original: bytes, translated: bytes, records: list[HudTextRecord]
) -> bytes:
    patched = bytearray(translated)
    occupied: set[int] = set()
    for record in records:
        if record.status != "implemented":
            continue
        source = original[
            record.original_offset : record.original_offset + record.original_length
        ]
        if len(source) != record.original_length:
            raise WorkstationError(f"{record.id} source range exceeds the ROM")
        if hashlib.sha256(source).hexdigest() != record.source_sha256:
            raise WorkstationError(f"{record.id} source SHA-256 does not match the supported ROM")
        encoded = encode_hud_text(record)
        for index, offset in enumerate(record.patch_offsets):
            if offset < record.original_offset or offset + 2 > record.original_offset + record.original_length:
                raise WorkstationError(f"{record.id} patch offset lies outside its pinned source")
            if offset in occupied:
                raise WorkstationError(f"HUD text patch offset ${offset:06X} is reused")
            occupied.add(offset)
            bounded_write(patched, offset, encoded[index * 2 : index * 2 + 2], record.id)
    return bytes(patched)