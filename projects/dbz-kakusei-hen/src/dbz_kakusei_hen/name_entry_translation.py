"""Validated character-oriented translation of the five-name editor."""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from snesworkbench.errors import WorkstationError
from snesworkbench.graphics import encode_tiles
from snesworkbench.manifests import read_tsv, require_columns
from snesworkbench.patching import bounded_write, changed_offsets
from snesworkbench.rom import parse_cpu_address

from .glyphs import (
    BASIC_LATIN_CHARACTERS,
    EXTENDED_LATIN_CHARACTERS,
    LATIN_CHARACTERS,
    LATIN_CHARACTER_IDS,
    LATIN_ID_CHARACTERS,
    decode_latin_cell,
    encode_latin_cell,
    encode_latin_line,
)
from .opening_translation import FONT_5X7
from .scenario import TEXT_LINE_BREAK, TEXT_TERMINATOR, glyph_source


NAME_ENTRY_COLUMNS = {
    "id", "original_address", "original_offset", "original_length",
    "source_sha256", "record_type", "english", "status", "notes",
}

PICKER_PAGE_1_OFFSET = 0x0223E0
PICKER_PAGE_2_OFFSET = 0x0224D0
PICKER_PAGE_LENGTH = 0xF0
SELECTION_MAP_1_OFFSET = 0x008D56
SELECTION_MAP_2_OFFSET = 0x008E00
SELECTION_MAP_LENGTH = 85 * 2
DEFAULT_NAMES_OFFSET = 0x022048
DEFAULT_NAMES_LENGTH = 50
DEFAULT_NAME_COUNT = 5
NAME_FIELD_WORDS = 5
NAME_FIELD_CHARACTERS = NAME_FIELD_WORDS * 2
NAME_RENDERER_ASM = Path(__file__).resolve().parents[2] / "asm" / "dual_format_text.asm"

# Filled after assembling the reviewed replacement. End offsets are exclusive.
NAME_RENDER_PATCH_RANGES = (
    (0x001B2C, 0x001B30),
    (0x006BCF, 0x006DB3),
    (0x008685, 0x00868B),
    (0x008AD7, 0x008ADB),
    (0x008BDD, 0x008BE2),
    (0x008C38, 0x008C3D),
    (0x00FE00, 0x00FFA1),
)
NAME_RENDER_PATCH_SOURCE_SHA256 = "f67683861445edbe4eeb805b462d08b4f2b2f060d43267827a105b5a8a26c823"

PICKER_STREAM_ENTRY_INDICES = (
    1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17,
    20, 21, 22, 23, 24, 26, 27, 28, 29, 30, 32, 33, 34, 35, 36,
    39, 40, 41, 42, 43, 45, 46, 47, 48, 49, 51, 52, 53, 54, 55,
    58, 59, 60, 61, 62, 64, 65, 66, 67, 68, 70, 71, 72, 73, 74,
    77, 78, 79, 80, 81, 83, 84, 85, 86, 87, 89, 90, 91, 92, 93,
    96, 97, 98, 99, 100, 102, 103, 104, 105, 106,
)
ACTION_GLYPH_INDICES = (108, 109, 110, 111)

SINGLE_CHARACTERS = LATIN_CHARACTERS
PAGE_1_CHARACTERS = BASIC_LATIN_CHARACTERS + (" ",) * (85 - len(BASIC_LATIN_CHARACTERS))
PAGE_2_CHARACTERS = EXTENDED_LATIN_CHARACTERS + (" ",) * (85 - len(EXTENDED_LATIN_CHARACTERS))

# One ordinary 16x16 renderer record per character. The packed stream stores
# IDs 1..119; this table is mirrored in dual_format_text.asm.
_LATIN_GLYPH_CODES = (
    0x0301, 0x0302, 0x0303, 0x0304, 0x0305, 0x0306, 0x0307, 0x0308,
    0x0311, 0x0312, 0x0313, 0x0314, 0x0315, 0x0316, 0x0317, 0x0318,
    0x0321, 0x0322, 0x0323, 0x0324, 0x0325, 0x0326, 0x0327, 0x0328,
    0x0331, 0x0332, 0x0333, 0x0334, 0x0335, 0x0336, 0x0337, 0x0338,
    0x0341, 0x0342, 0x0343, 0x0344, 0x0345, 0x0346, 0x0347, 0x0348,
    0x0351, 0x0352, 0x0353, 0x0354, 0x0355, 0x0356, 0x0357, 0x0358,
    0x0361, 0x0362, 0x0363, 0x0364, 0x0365, 0x0366, 0x0367, 0x0368,
    0x0371, 0x0372, 0x0373, 0x0374, 0x0375, 0x0376, 0x0377, 0x0378,
    0x0381, 0x0382, 0x0383, 0x0384, 0x0385,
    0x0273, 0x0274, 0x0275, 0x0276, 0x0277,
    0x02D1, 0x02D2, 0x02D3, 0x02D4, 0x02D5, 0x02D6, 0x02D7,
    0x0414, 0x0415, 0x0416, 0x0417,
    0x0420, 0x0421, 0x0422, 0x0423, 0x0424, 0x0425, 0x0426, 0x0427,
    0x0430, 0x0431, 0x0432, 0x0433, 0x0434, 0x0435, 0x0436, 0x0437,
    0x0440, 0x0441, 0x0442, 0x0443, 0x0444, 0x0445, 0x0446, 0x0447,
    0x0450, 0x0451, 0x0452, 0x0453, 0x0454, 0x0455, 0x0456, 0x0457,
    0x0460, 0x0461,
)
LATIN_GLYPH_CODES = dict(zip(SINGLE_CHARACTERS, _LATIN_GLYPH_CODES, strict=True))
LATIN_ID_GLYPH_CODES = {
    LATIN_CHARACTER_IDS[character]: code for character, code in LATIN_GLYPH_CODES.items()
}
LATIN_GLYPH_SOURCE_SHA256 = "e1d8c8639378d43d685db4b476a9b48d35bfa541451b1031efc975613f03469f"

EXTRA_FONT_5X7 = {
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    ":": ("00000", "00110", "00110", "00000", "00110", "00110", "00000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "q": ("00000", "00000", "01101", "10011", "01111", "00001", "00001"),
    "x": ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    "z": ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    "'": ("00100", "00100", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00110", "00110"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    ",": ("00000", "00000", "00000", "00000", "00110", "00110", "00100"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "/": ("00001", "00010", "00100", "00100", "01000", "10000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "\"": ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
}


def _accented(pattern: tuple[str, ...], mark: str) -> tuple[str, ...]:
    """Place an accent above a compact six-row capital or five-row lowercase."""

    if len(pattern) == 6:
        return (mark, *pattern)
    return (mark, "00000", *pattern[2:])


COMPACT_CAPITALS = {
    "A": ("01110", "10001", "11111", "10001", "10001", "10001"),
    "C": ("01110", "10001", "10000", "10000", "10001", "01110"),
    "E": ("11111", "10000", "11110", "10000", "10000", "11111"),
    "I": ("11111", "00100", "00100", "00100", "00100", "11111"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "01110"),
    "U": ("10001", "10001", "10001", "10001", "10001", "01110"),
}
ACCENT_MARKS = {
    "acute": "00010", "grave": "01000", "diaeresis": "01010",
    "macron": "01110", "tilde": "01101",
}
ACCENTED_FONT_5X7 = {
    **{character: _accented(COMPACT_CAPITALS[base], ACCENT_MARKS[accent]) for character, base, accent in (
        ("Á", "A", "acute"), ("É", "E", "acute"), ("Í", "I", "acute"),
        ("Ó", "O", "acute"), ("Ú", "U", "acute"), ("À", "A", "grave"),
        ("È", "E", "grave"), ("Ì", "I", "grave"), ("Ò", "O", "grave"),
        ("Ù", "U", "grave"), ("Ä", "A", "diaeresis"), ("Ë", "E", "diaeresis"),
        ("Ï", "I", "diaeresis"), ("Ö", "O", "diaeresis"), ("Ü", "U", "diaeresis"),
        ("Ñ", "N", "tilde"), ("Ā", "A", "macron"), ("Ē", "E", "macron"),
        ("Ī", "I", "macron"), ("Ō", "O", "macron"), ("Ū", "U", "macron"),
    )},
    "Ç": (*COMPACT_CAPITALS["C"][:5], "00100", "01000"),
    **{character: _accented(FONT_5X7[base], ACCENT_MARKS[accent]) for character, base, accent in (
        ("á", "a", "acute"), ("é", "e", "acute"), ("í", "i", "acute"),
        ("ó", "o", "acute"), ("ú", "u", "acute"), ("à", "a", "grave"),
        ("è", "e", "grave"), ("ì", "i", "grave"), ("ò", "o", "grave"),
        ("ù", "u", "grave"), ("ä", "a", "diaeresis"), ("ë", "e", "diaeresis"),
        ("ï", "i", "diaeresis"), ("ö", "o", "diaeresis"), ("ü", "u", "diaeresis"),
        ("ñ", "n", "tilde"), ("ā", "a", "macron"), ("ē", "e", "macron"),
        ("ī", "i", "macron"), ("ō", "o", "macron"), ("ū", "u", "macron"),
    )},
    "ç": ("00000", "01111", "10000", "10000", "01111", "00100", "01000"),
}
NAME_FONT_5X7 = {**FONT_5X7, **EXTRA_FONT_5X7, **ACCENTED_FONT_5X7}


@dataclass(frozen=True)
class NameEntryRecord:
    id: str
    bank: int
    address: int
    offset: int
    length: int
    source_sha256: str
    record_type: str
    english: str
    status: str
    notes: str


def _hex(value: str, field: str) -> int:
    try:
        return int(value.removeprefix("$"), 16)
    except ValueError as error:
        raise WorkstationError(f"invalid {field}: {value!r}") from error


def load_name_entry_records(path: str | Path) -> list[NameEntryRecord]:
    rows = read_tsv(path)
    require_columns(path, rows, NAME_ENTRY_COLUMNS)
    records: list[NameEntryRecord] = []
    seen: set[str] = set()
    for row in rows:
        identifier = row["id"]
        if identifier in seen:
            raise WorkstationError(f"duplicate name-entry record {identifier!r}")
        seen.add(identifier)
        bank, address = parse_cpu_address(row["original_address"].removeprefix("$"))
        records.append(NameEntryRecord(
            id=identifier,
            bank=bank,
            address=address,
            offset=_hex(row["original_offset"], f"{identifier} original offset"),
            length=int(row["original_length"], 0),
            source_sha256=row["source_sha256"],
            record_type=row["record_type"],
            english=row["english"].replace("\\n", "\n"),
            status=row["status"],
            notes=row["notes"],
        ))
    return records


def render_latin_character(character: str) -> tuple[tuple[int, ...], ...]:
    if len(character) != 1 or character not in NAME_FONT_5X7:
        raise WorkstationError(f"unsupported name-font character {character!r}")
    bitmap = [[0] * 16 for _ in range(16)]
    for source_y, pattern in enumerate(NAME_FONT_5X7[character]):
        for source_x, pixel in enumerate(pattern):
            if pixel == "1":
                bitmap[1 + source_y * 2][source_x] = 3
                bitmap[2 + source_y * 2][source_x] = 3
    return tuple(tuple(row) for row in bitmap)


def encode_latin_glyph(character: str) -> tuple[bytes, bytes, bytes, bytes]:
    bitmap = render_latin_character(character)
    tiles = (
        tuple(row[:8] for row in bitmap[:8]), tuple(row[8:] for row in bitmap[:8]),
        tuple(row[:8] for row in bitmap[8:]), tuple(row[8:] for row in bitmap[8:]),
    )
    encoded = encode_tiles(tiles, bpp=2)
    return tuple(encoded[index:index + 16] for index in range(0, 64, 16))


def picker_word(character: str) -> int:
    if character == " ":
        return encode_latin_cell()
    return encode_latin_cell(character)


def encode_name_words(text: str, max_cells: int = NAME_FIELD_WORDS) -> tuple[int, ...]:
    if len(text) > max_cells * 2:
        raise WorkstationError(f"cannot encode {text!r} in {max_cells * 2} name characters")
    return encode_latin_line(text, max_cells, context="name")


def encode_default_name_words(text: str) -> tuple[int, ...]:
    """Encode a localized default in the ordinary packed-Latin format."""

    return encode_name_words(text)


def decode_name_words(words: Sequence[int]) -> str:
    return "".join(decode_latin_cell(word) for word in words).rstrip()


def prepare_name_field_for_edit(words: Sequence[int]) -> tuple[int, ...]:
    """Convert only a legacy field before a packed-character overwrite."""

    if len(words) != NAME_FIELD_WORDS:
        raise WorkstationError(f"name field has {len(words)} words; expected {NAME_FIELD_WORDS}")
    if not words[0] & 0x8000:
        return (0x8000,) * NAME_FIELD_WORDS
    return tuple(words)


def overwrite_name_character(words: Sequence[int], position: int, character: str) -> tuple[int, ...]:
    """Model one A-button insertion into a ten-character name field."""

    if not 0 <= position < NAME_FIELD_CHARACTERS:
        raise WorkstationError(f"name position {position} is outside one name field")
    normalized = list(prepare_name_field_for_edit(words))
    character_id = LATIN_CHARACTER_IDS.get(character)
    if character_id is None:
        raise WorkstationError(f"unsupported Latin character {character!r} in name")
    word_index, odd = divmod(position, 2)
    if odd:
        normalized[word_index] = (normalized[word_index] & 0x807F) | (character_id << 7)
    else:
        normalized[word_index] = (normalized[word_index] & 0xBF80) | character_id
    return tuple(normalized)


def backspace_name_fields(
    cursor: int, fields: Sequence[Sequence[int]]
) -> tuple[int, tuple[tuple[int, ...], ...]]:
    """Model B-button cursor navigation without changing stored name data."""

    if not 0 <= cursor < DEFAULT_NAME_COUNT * NAME_FIELD_CHARACTERS:
        raise WorkstationError(f"name cursor {cursor} is outside the five name fields")
    if len(fields) != DEFAULT_NAME_COUNT:
        raise WorkstationError(f"name editor has {len(fields)} fields; expected {DEFAULT_NAME_COUNT}")
    normalized = tuple(tuple(field) for field in fields)
    if any(len(field) != NAME_FIELD_WORDS for field in normalized):
        raise WorkstationError(f"every name field must contain {NAME_FIELD_WORDS} words")
    return max(cursor - 1, 0), normalized


def name_cursor_x(cursor: int, *, origin: int = 0xB0) -> int:
    return origin + (cursor % NAME_FIELD_CHARACTERS) * 6


def _source_line_cells(data: bytes, context: str) -> tuple[int, ...]:
    if len(data) % 2:
        raise WorkstationError(f"{context} has an odd source length")
    widths = [0]
    for offset in range(0, len(data), 2):
        word = int.from_bytes(data[offset:offset + 2], "little")
        if word == TEXT_TERMINATOR:
            if offset != len(data) - 2:
                raise WorkstationError(f"{context} has data after its terminator")
            return tuple(widths)
        if word == TEXT_LINE_BREAK:
            widths.append(0)
        else:
            widths[-1] += 1
    raise WorkstationError(f"{context} has no terminator")


def _encode_fixed_lines(text: str, line_cells: Sequence[int]) -> bytes:
    lines = text.split("\n")
    if len(lines) != len(line_cells):
        raise WorkstationError("name-entry fixed text line count does not match its source")
    words: list[int] = []
    for line_index, (line, cells) in enumerate(zip(lines, line_cells)):
        words.extend(encode_latin_line(line, cells, context=f"name UI line {line_index + 1}"))
        if line_index != len(lines) - 1:
            words.append(TEXT_LINE_BREAK)
    words.append(TEXT_TERMINATOR)
    return b"".join(word.to_bytes(2, "little") for word in words)


def _patch_picker_page(source: bytes, characters: Sequence[str]) -> bytes:
    if len(source) != PICKER_PAGE_LENGTH or len(characters) != 85:
        raise WorkstationError("name picker page structure is inconsistent")
    words = [int.from_bytes(source[index:index + 2], "little") for index in range(0, len(source), 2)]
    for stream_index, character in zip(PICKER_STREAM_ENTRY_INDICES, characters, strict=True):
        words[stream_index] = picker_word(character)
    # Preserve the action area geometry with packed single-character labels.
    words[ACTION_GLYPH_INDICES[0]] = encode_latin_cell("D", "O")
    words[ACTION_GLYPH_INDICES[1]] = encode_latin_cell("N", "E")
    words[ACTION_GLYPH_INDICES[2]] = encode_latin_cell()
    words[ACTION_GLYPH_INDICES[3]] = encode_latin_cell()
    return b"".join(word.to_bytes(2, "little") for word in words)


def _record_by_id(records: Sequence[NameEntryRecord], identifier: str) -> NameEntryRecord:
    try:
        return next(record for record in records if record.id == identifier)
    except StopIteration as error:
        raise WorkstationError(f"missing name-entry record {identifier!r}") from error


def _apply_runtime_patch(original: bytes, translated: bytes) -> bytes:
    source = b"".join(original[start:end] for start, end in NAME_RENDER_PATCH_RANGES)
    if hashlib.sha256(source).hexdigest() != NAME_RENDER_PATCH_SOURCE_SHA256:
        raise WorkstationError("dual-format runtime patch ranges do not match the supported original")
    with tempfile.TemporaryDirectory(prefix="dbz-dual-format-") as directory:
        rom_path = Path(directory) / "translated.sfc"
        rom_path.write_bytes(translated)
        result = subprocess.run(
            ["asar", "--no-title-check", "--fix-checksum=off", str(NAME_RENDERER_ASM), str(rom_path)],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            diagnostic = (result.stdout + result.stderr).strip()[:1000]
            raise WorkstationError(f"dual-format runtime assembly failed: {diagnostic}")
        patched = rom_path.read_bytes()
    if len(patched) != len(translated):
        raise WorkstationError("dual-format runtime patch changed the ROM size")
    allowed = {offset for start, end in NAME_RENDER_PATCH_RANGES for offset in range(start, end)}
    outside = changed_offsets(translated, patched) - allowed
    if outside:
        raise WorkstationError(f"runtime patch changed unexpected byte at ROM ${min(outside):06X}")
    return patched


def apply_name_entry_translation(
    original: bytes, translated: bytes, records: Sequence[NameEntryRecord]
) -> bytes:
    implemented = [record for record in records if record.status == "implemented"]
    for record in implemented:
        source = original[record.offset:record.offset + record.length]
        if len(source) != record.length or hashlib.sha256(source).hexdigest() != record.source_sha256:
            raise WorkstationError(f"{record.id} source does not match the supported original")
        expected_offset = (record.bank & 0x7F) * 0x8000 + (record.address & 0x7FFF)
        if expected_offset != record.offset:
            raise WorkstationError(f"{record.id} CPU address and ROM offset disagree")

    glyph_source_bytes = b"".join(
        original[offset:offset + 16]
        for code in LATIN_GLYPH_CODES.values()
        for offset in glyph_source(code).block_offsets
    )
    if hashlib.sha256(glyph_source_bytes).hexdigest() != LATIN_GLYPH_SOURCE_SHA256:
        raise WorkstationError("Latin glyph source records do not match the supported original")

    patched = bytearray(translated)
    for character, code in LATIN_GLYPH_CODES.items():
        for offset, block in zip(glyph_source(code).block_offsets, encode_latin_glyph(character), strict=True):
            bounded_write(patched, offset, block, f"Latin glyph ${code:04X}")

    for identifier, characters in (("picker_page_1", PAGE_1_CHARACTERS), ("picker_page_2", PAGE_2_CHARACTERS)):
        record = _record_by_id(records, identifier)
        bounded_write(patched, record.offset, _patch_picker_page(original[record.offset:record.offset + record.length], characters), identifier)
    for identifier, characters in (("selection_map_1", PAGE_1_CHARACTERS), ("selection_map_2", PAGE_2_CHARACTERS)):
        record = _record_by_id(records, identifier)
        encoded = b"".join(picker_word(character).to_bytes(2, "little") for character in characters)
        bounded_write(patched, record.offset, encoded, identifier)

    for record in implemented:
        if record.record_type == "fixed_text":
            bounded_write(
                patched, record.offset,
                _encode_fixed_lines(record.english, _source_line_cells(original[record.offset:record.offset + record.length], record.id)),
                record.id,
            )

    defaults = _record_by_id(records, "default_names")
    names = defaults.english.split("\n")
    if len(names) != DEFAULT_NAME_COUNT:
        raise WorkstationError(f"default_names defines {len(names)} names; expected {DEFAULT_NAME_COUNT}")
    encoded_defaults = b"".join(
        word.to_bytes(2, "little") for name in names for word in encode_default_name_words(name)
    )
    bounded_write(patched, defaults.offset, encoded_defaults, defaults.id)
    return _apply_runtime_patch(original, bytes(patched))