"""Packed Latin text encoding for Kakusei Hen's dual-format compositor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from snesworkbench.errors import WorkstationError

from .scenario import TEXT_LINE_BREAK, TEXT_TERMINATOR


CHARACTERS_PER_CELL = 2
LATIN_MARKER = 0x8000
LATIN_ID_MASK = 0x007F
LATIN_SECOND_SHIFT = 7
BASIC_LATIN_CHARACTERS = tuple(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'-.!,?:"
)
EXTENDED_LATIN_CHARACTERS = tuple(
    "ÁÉÍÓÚÀÈÌÒÙÄËÏÖÜÑÇáéíóúàèìòùäëïöüñçĀĒĪŌŪāēīōū&/()+\""
)
LATIN_CHARACTERS = BASIC_LATIN_CHARACTERS + EXTENDED_LATIN_CHARACTERS
LATIN_CHARACTER_IDS = {
    character: index for index, character in enumerate(LATIN_CHARACTERS, start=1)
}
LATIN_ID_CHARACTERS = {identifier: character for character, identifier in LATIN_CHARACTER_IDS.items()}


@dataclass(frozen=True)
class EncodedText:
    words: tuple[int, ...]
    line_cells: tuple[int, ...]

    @property
    def data(self) -> bytes:
        return b"".join(word.to_bytes(2, "little") for word in self.words)


def encode_latin_cell(first: str = " ", second: str = " ") -> int:
    """Pack two independent Latin characters into one marked 16-bit word."""

    identifiers = []
    for character in (first, second):
        if character == " ":
            identifiers.append(0)
            continue
        try:
            identifiers.append(LATIN_CHARACTER_IDS[character])
        except KeyError as error:
            raise WorkstationError(f"unsupported Latin character {character!r}") from error
    return LATIN_MARKER | identifiers[0] | (identifiers[1] << LATIN_SECOND_SHIFT)


def decode_latin_cell(word: int) -> str:
    if not word & LATIN_MARKER:
        raise WorkstationError(f"word ${word:04X} is not packed Latin data")
    first = word & LATIN_ID_MASK
    second = (word >> LATIN_SECOND_SHIFT) & LATIN_ID_MASK
    try:
        return "".join(
            " " if identifier == 0 else LATIN_ID_CHARACTERS[identifier]
            for identifier in (first, second)
        )
    except KeyError as error:
        raise WorkstationError(f"unknown packed Latin character id {error.args[0]}") from error


def encode_latin_line(line: str, cells: int, *, context: str) -> tuple[int, ...]:
    width = cells * CHARACTERS_PER_CELL
    if len(line) > width:
        raise WorkstationError(f"{context} exceeds its {width}-character allocation")
    padded = line.ljust(width)
    return tuple(
        encode_latin_cell(padded[index], padded[index + 1])
        for index in range(0, width, CHARACTERS_PER_CELL)
    )


def _split_lines(text: str) -> tuple[str, ...]:
    if "\r" in text:
        raise WorkstationError("translation text must use LF line endings")
    return tuple(text.split("\n"))


def encode_text_layout(
    text: str,
    *,
    max_line_width: int,
    max_lines: int | None = None,
    line_cells: Sequence[int] | None = None,
    context: str = "translation",
) -> EncodedText:
    """Encode explicit lines as marked, two-character Latin words."""

    if max_line_width < 1:
        raise WorkstationError("maximum line width must be positive")
    lines = _split_lines(text)
    if max_lines is not None and len(lines) > max_lines:
        raise WorkstationError(f"{context} has {len(lines)} lines; presentation permits {max_lines}")
    if line_cells is not None and len(line_cells) != len(lines):
        raise WorkstationError(
            f"{context} has {len(lines)} lines but {len(line_cells)} line-cell allocations"
        )

    words: list[int] = []
    encoded_widths: list[int] = []
    for line_index, line in enumerate(lines):
        needed = (len(line) + 1) // CHARACTERS_PER_CELL
        cells = needed if line_cells is None else line_cells[line_index]
        if cells < needed:
            raise WorkstationError(
                f"{context} line {line_index + 1} needs {needed} cells; allocation is {cells}"
            )
        if cells > max_line_width:
            raise WorkstationError(
                f"{context} line {line_index + 1} uses {cells} cells; presentation permits {max_line_width}"
            )
        words.extend(encode_latin_line(line, cells, context=f"{context} line {line_index + 1}"))
        encoded_widths.append(cells)
        if line_index != len(lines) - 1:
            words.append(TEXT_LINE_BREAK)
    words.append(TEXT_TERMINATOR)
    return EncodedText(tuple(words), tuple(encoded_widths))


def encode_text(text: str, max_line_width: int = 14) -> list[int]:
    return list(encode_text_layout(text, max_line_width=max_line_width).words)


def decode_glyph_codes(codes: Sequence[int]) -> str:
    decoded: list[str] = []
    for code in codes:
        if code == TEXT_LINE_BREAK:
            decoded.append("\n")
        elif code == TEXT_TERMINATOR:
            continue
        else:
            decoded.append(decode_latin_cell(code))
    return "".join(decoded)