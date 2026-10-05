"""Configurable translated-text encoding and allocation primitives."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import WorkstationError
from .manifests import read_tsv, require_columns


class TextEncodeError(WorkstationError):
    """Raised for unsupported translated text or invalid allocation data."""


@dataclass(frozen=True)
class AllocationRange:
    start: int
    end: int


@dataclass(frozen=True)
class TextEncoding:
    characters: dict[str, int]
    controls: tuple[tuple[str, bytes], ...]
    terminator: bytes
    max_line_units: int
    line_control: str | None = None


def load_character_encoding(path: str | Path, *, maximum_value: int = 0xFF) -> dict[str, int]:
    rows = read_tsv(path)
    require_columns(path, rows, {"character", "stream_byte"})
    result: dict[str, int] = {}
    for row in rows:
        character = row["character"]
        value = int(row["stream_byte"], 0)
        if character in result:
            raise TextEncodeError(f"duplicate encoding for {character!r}")
        if not 0 <= value <= maximum_value:
            raise TextEncodeError(
                f"translated byte must be in $00-${maximum_value:02X}, got ${value:02X}"
            )
        result[character] = value
    return result


def encode_text(text: str, encoding: TextEncoding) -> bytes:
    output = bytearray()
    line_units = 0
    cursor = 0
    controls = sorted(encoding.controls, key=lambda item: len(item[0]), reverse=True)
    while cursor < len(text):
        matched = False
        for token, data in controls:
            if text.startswith(token, cursor):
                output.extend(data)
                if token == encoding.line_control:
                    line_units = 0
                cursor += len(token)
                matched = True
                break
        if matched:
            continue
        character = text[cursor]
        if character not in encoding.characters:
            raise TextEncodeError(
                f"unsupported translated character {character!r} at index {cursor}"
            )
        line_units += 1
        if line_units > encoding.max_line_units:
            raise TextEncodeError(
                f"translated line exceeds {encoding.max_line_units} units near index {cursor}"
            )
        output.append(encoding.characters[character])
        cursor += 1
    output.extend(encoding.terminator)
    return bytes(output)


def validate_allocation_ranges(
    ranges: list[AllocationRange], *, minimum: int = 0, maximum: int = 0xFFFFFFFF
) -> None:
    if not ranges:
        raise TextEncodeError("at least one allocation range is required")
    for region in ranges:
        if not minimum <= region.start <= region.end <= maximum:
            raise TextEncodeError(
                f"invalid allocation range ${region.start:X}-${region.end:X}"
            )
    for previous, current in zip(ranges, ranges[1:]):
        if current.start <= previous.end:
            raise TextEncodeError("allocation ranges overlap or are not ascending")


def allocate_streams(
    encoded: list[tuple[str, bytes]],
    ranges: list[AllocationRange],
    *,
    minimum: int = 0,
    maximum: int = 0xFFFFFFFF,
) -> dict[str, int]:
    validate_allocation_ranges(ranges, minimum=minimum, maximum=maximum)
    addresses: dict[str, int] = {}
    range_index = 0
    cursor = ranges[0].start
    for string_id, data in encoded:
        if not data:
            raise TextEncodeError(f"translated stream {string_id} is empty")
        if string_id in addresses:
            raise TextEncodeError(f"duplicate translated stream ID {string_id}")
        while cursor + len(data) - 1 > ranges[range_index].end:
            range_index += 1
            if range_index >= len(ranges):
                raise TextEncodeError(f"translated streams do not fit; failed at {string_id}")
            cursor = ranges[range_index].start
        addresses[string_id] = cursor
        cursor += len(data)
    return addresses