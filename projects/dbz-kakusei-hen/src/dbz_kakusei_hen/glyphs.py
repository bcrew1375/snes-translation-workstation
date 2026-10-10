"""Strict paired-glyph text encoding for Kakusei Hen."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from snesworkbench.errors import WorkstationError

from .opening_translation import PAIR_GLYPH_CODES, SPACE_GLYPH_CODE
from .scenario import TEXT_LINE_BREAK, TEXT_TERMINATOR


CHARACTERS_PER_CELL = 2
EXTENDED_VOCABULARY: dict[str, int] = dict(PAIR_GLYPH_CODES)


@dataclass(frozen=True)
class EncodedText:
    words: tuple[int, ...]
    line_cells: tuple[int, ...]

    @property
    def data(self) -> bytes:
        return b"".join(word.to_bytes(2, "little") for word in self.words)


def _split_lines(text: str) -> tuple[str, ...]:
    if "\r" in text:
        raise WorkstationError("translation text must use LF line endings")
    lines = tuple(text.split("\n"))
    if any(line == "" for line in lines):
        raise WorkstationError("translation text contains an empty line")
    return lines


def encode_text_layout(
    text: str,
    *,
    max_line_width: int,
    max_lines: int | None = None,
    line_cells: Sequence[int] | None = None,
    vocabulary: Mapping[str, int] = EXTENDED_VOCABULARY,
    context: str = "translation",
) -> EncodedText:
    """Encode explicit lines, reporting unsupported pairs and exact positions."""

    if max_line_width < 1:
        raise WorkstationError("maximum line width must be positive")
    lines = _split_lines(text)
    if max_lines is not None and len(lines) > max_lines:
        raise WorkstationError(
            f"{context} has {len(lines)} lines; presentation permits {max_lines}"
        )
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
                f"{context} line {line_index + 1} uses {cells} cells; presentation permits "
                f"{max_line_width}"
            )
        padded = line.ljust(cells * CHARACTERS_PER_CELL)
        for cell_index in range(cells):
            pair = padded[cell_index * 2 : cell_index * 2 + 2]
            if pair == "  ":
                words.append(SPACE_GLYPH_CODE)
                continue
            try:
                words.append(vocabulary[pair])
            except KeyError as error:
                unsupported = [character for character in pair if character != " "]
                detail = (
                    f"unsupported character {unsupported[0]!r}"
                    if any(not any(character in known for known in vocabulary) for character in unsupported)
                    else f"unsupported pair {pair!r}"
                )
                raise WorkstationError(
                    f"{context} line {line_index + 1}, cell {cell_index + 1}: {detail}"
                ) from error
        encoded_widths.append(cells)
        if line_index != len(lines) - 1:
            words.append(TEXT_LINE_BREAK)
    words.append(TEXT_TERMINATOR)
    return EncodedText(tuple(words), tuple(encoded_widths))


def encode_text(text: str, max_line_width: int = 14) -> list[int]:
    """Compatibility API returning encoded words with strict validation."""

    return list(encode_text_layout(text, max_line_width=max_line_width).words)


def decode_glyph_codes(
    codes: Sequence[int], vocabulary: Mapping[str, int] = EXTENDED_VOCABULARY
) -> str:
    reverse = {code: pair for pair, code in vocabulary.items()}
    reverse[SPACE_GLYPH_CODE] = "  "
    reverse[TEXT_LINE_BREAK] = "\n"
    reverse[TEXT_TERMINATOR] = ""
    unknown = [code for code in codes if code not in reverse]
    if unknown:
        raise WorkstationError(f"unknown paired-glyph code ${unknown[0]:04X}")
    return "".join(reverse[code] for code in codes)