"""Validated fixed-allocation translation of the opening menu family."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from snesworkbench.errors import WorkstationError
from snesworkbench.manifests import manifest_int, manifest_int_list, read_manifest
from snesworkbench.patching import bounded_write
from snesworkbench.rom import parse_cpu_address

from .glyphs import encode_latin_line
from .scenario import TEXT_LINE_BREAK, TEXT_TERMINATOR


MENU_FIELDS = {
    "id": str,
    "original_address": str,
    "original_offset": int,
    "original_length": int,
    "source_sha256": str,
    "record_type": str,
    "character_offsets": list,
    "english": str,
    "status": str,
    "notes": str,
}
TERMINATED_RECORD = "terminated"
FIXED_RECORD = "fixed"
FIXED_NATIVE_SUFFIX_RECORD = "fixed_native_suffix"


@dataclass(frozen=True)
class TitleMenuRecord:
    id: str
    bank: int
    address: int
    offset: int
    length: int
    source_sha256: str
    record_type: str
    character_offsets: tuple[int, ...]
    english: str
    status: str
    notes: str


def _hex(value: object, field: str) -> int:
    return manifest_int(value, field, hexadecimal=True)


def load_title_menu_records(path: str | Path) -> list[TitleMenuRecord]:
    rows = read_manifest(path, MENU_FIELDS)
    records: list[TitleMenuRecord] = []
    seen: set[str] = set()
    for row in rows:
        identifier = row["id"]
        if identifier in seen:
            raise WorkstationError(f"duplicate title-menu record {identifier!r}")
        seen.add(identifier)
        bank, address = parse_cpu_address(row["original_address"].removeprefix("$"))
        try:
            length = manifest_int(row["original_length"], f"{identifier} original length")
        except WorkstationError as error:
            raise WorkstationError(f"invalid original length for {identifier!r}") from error
        record_type = row["record_type"]
        if record_type not in {TERMINATED_RECORD, FIXED_RECORD, FIXED_NATIVE_SUFFIX_RECORD}:
            raise WorkstationError(f"invalid record type for {identifier!r}: {record_type!r}")
        try:
            character_offsets = manifest_int_list(
                row["character_offsets"], f"{identifier} character offsets"
            )
        except WorkstationError as error:
            raise WorkstationError(f"invalid character offsets for {identifier!r}") from error
        if not character_offsets or any(offset < 0 for offset in character_offsets):
            raise WorkstationError(f"invalid character offsets for {identifier!r}")
        records.append(
            TitleMenuRecord(
                id=identifier,
                bank=bank,
                address=address,
                offset=_hex(row["original_offset"], f"{identifier} original offset"),
                length=length,
                source_sha256=row["source_sha256"],
                record_type=record_type,
                character_offsets=character_offsets,
                english=row["english"].replace("\\n", "\n"),
                status=row["status"],
                notes=row["notes"],
            )
        )
    return records


def decode_menu_line_cells(
    data: bytes, context: str, record_type: str = TERMINATED_RECORD
) -> tuple[int, ...]:
    if len(data) % 2:
        raise WorkstationError(f"{context} has an odd byte length")
    words = tuple(
        int.from_bytes(data[offset : offset + 2], "little")
        for offset in range(0, len(data), 2)
    )
    if not words:
        raise WorkstationError(f"{context} is empty")
    if record_type in {FIXED_RECORD, FIXED_NATIVE_SUFFIX_RECORD}:
        if any(word < 0x0100 for word in words):
            raise WorkstationError(f"{context} fixed record contains a control word")
        return (len(words),)
    if record_type != TERMINATED_RECORD:
        raise WorkstationError(f"{context} has unknown record type {record_type!r}")
    if words[-1] != TEXT_TERMINATOR:
        raise WorkstationError(f"{context} lacks its final terminator")
    widths: list[int] = []
    width = 0
    for word in words[:-1]:
        if word == TEXT_LINE_BREAK:
            if width == 0:
                raise WorkstationError(f"{context} contains an empty line")
            widths.append(width)
            width = 0
        elif word < 0x0100:
            raise WorkstationError(f"{context} contains unknown control word ${word:04X}")
        else:
            width += 1
    if width == 0:
        raise WorkstationError(f"{context} ends with an empty line")
    widths.append(width)
    return tuple(widths)


def encode_title_menu(
    record: TitleMenuRecord, line_cells: tuple[int, ...], source: bytes | None = None
) -> bytes:
    lines = tuple(record.english.split("\n"))
    if (
        len(lines) != len(line_cells)
        or len(lines) != len(record.character_offsets)
        or any(not line for line in lines)
    ):
        raise WorkstationError(
            f"{record.id} has {len(lines)} English lines; source has {len(line_cells)}"
        )
    words: list[int] = []
    for line_index, (line, cells, character_offset) in enumerate(
        zip(lines, line_cells, record.character_offsets)
    ):
        if character_offset + len(line) > cells * 2:
            raise WorkstationError(
                f"{record.id} line {line_index + 1} exceeds its {cells}-cell allocation"
            )
        padded = " " * character_offset + line
        words.extend(
            encode_latin_line(
                padded, cells, context=f"{record.id} line {line_index + 1}"
            )
        )
        if record.record_type == TERMINATED_RECORD and line_index != len(lines) - 1:
            words.append(TEXT_LINE_BREAK)
    if record.record_type == TERMINATED_RECORD:
        words.append(TEXT_TERMINATOR)
    if record.record_type == FIXED_NATIVE_SUFFIX_RECORD:
        if source is None or len(source) < 4:
            raise WorkstationError(f"{record.id} requires a two-word native suffix")
        words[-2:] = (
            int.from_bytes(source[-4:-2], "little"),
            int.from_bytes(source[-2:], "little"),
        )
    encoded = b"".join(word.to_bytes(2, "little") for word in words)
    if len(encoded) != record.length:
        raise WorkstationError(
            f"{record.id} encoded length is {len(encoded)}; expected {record.length}"
        )
    return encoded


def apply_title_menu_translation(
    original: bytes, translated: bytes, records: list[TitleMenuRecord]
) -> bytes:
    """Validate the pinned menu streams and replace them without relocation."""

    patched = bytearray(translated)
    implemented = [record for record in records if record.status == "implemented"]
    for record in implemented:
        source = original[record.offset : record.offset + record.length]
        if len(source) != record.length:
            raise WorkstationError(f"{record.id} source range exceeds the ROM")
        if hashlib.sha256(source).hexdigest() != record.source_sha256:
            raise WorkstationError(f"{record.id} source SHA-256 does not match the supported ROM")
        expected_offset = (record.bank & 0x7F) * 0x8000 + (record.address & 0x7FFF)
        if expected_offset != record.offset:
            raise WorkstationError(f"{record.id} CPU address and ROM offset disagree")
        line_cells = decode_menu_line_cells(source, record.id, record.record_type)
        encoded = encode_title_menu(record, line_cells, source)
        bounded_write(patched, record.offset, encoded, record.id)
        if decode_menu_line_cells(encoded, record.id, record.record_type) != line_cells:
            raise WorkstationError(f"{record.id} failed the post-write structure check")
    return bytes(patched)