"""Deterministic English patch for the complete automatic opening sequence."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from snesworkbench.errors import WorkstationError
from snesworkbench.patching import bounded_write

from .glyphs import CHARACTERS_PER_CELL, encode_latin_line
from .scenario import TEXT_LINE_BREAK, TEXT_TERMINATOR


@dataclass(frozen=True)
class OpeningNarration:
    """One fixed-allocation command-$08 opening narration stream."""

    selector: int
    bank: int
    address: int
    offset: int
    length: int
    source_sha256: str
    lines: tuple[str, ...]
    line_cells: tuple[int, ...]


OPENING_NARRATIONS = (
    OpeningNarration(
        selector=0x07E1,
        bank=0x9C,
        address=0x9358,
        offset=0x0E1358,
        length=120,
        source_sha256="1fc79be8e4185536a5e87ab8aaab3aa04ed7806a6fec92f2b876316f3f72ff38",
        lines=(
            "Long ago, it was said that",
            "when all seven Dragon Balls",
            "were gathered, Shenron would",
            "appear and grant any wish...",
        ),
        line_cells=(14, 14, 14, 14),
    ),
    OpeningNarration(
        selector=0x07E2,
        bank=0x9C,
        address=0x93D0,
        offset=0x0E13D0,
        length=116,
        source_sha256="ee3c88a822fde30fe192b24309935df94948bced8df1241775ab2d0b20f92b10",
        lines=(
            "Because of the Dragon Balls,",
            "young Goku met many friends",
            "and fought many enemies,",
            "growing ever stronger...",
        ),
        line_cells=(14, 14, 13, 13),
    ),
    OpeningNarration(
        selector=0x07E3,
        bank=0x9C,
        address=0x9444,
        offset=0x0E1444,
        length=72,
        source_sha256="ca0554babf3af2d796e4790cb9ab3bdacaf3841503e253f9289b05c16a4a73fe",
        lines=(
            "It all began with",
            "a single Dragon Ball...",
            "And...",
        ),
        line_cells=(14, 14, 5),
    ),
    OpeningNarration(
        selector=0x07E4,
        bank=0x9C,
        address=0x948C,
        offset=0x0E148C,
        length=26,
        source_sha256="2bde7cbd0979fce47aa7f639e0534718471b40364e1fca6bc86e51f4bb568ab1",
        lines=("It continues even now...",),
        line_cells=(12,),
    ),
)

# Runtime tracing of scenario root $0170 confirms that these records follow the
# four narration panels before the title screen returns. Each translation keeps
# the original stream's exact line and cell allocation.
OPENING_RECAP = (
    OpeningNarration(0x0026, 0x99, 0x8964, 0x0C8964, 14, "99085eb2e3e5fcd9831f5e84346018e7060096445739d52a99f5d8b3015c85ed", ("A-a-aah...!",), (6,)),
    OpeningNarration(0x07E5, 0x9C, 0x94A6, 0x0E14A6, 40, "18e1c4d87bb87a27aa9040d097c953a31c0a7f6ffd63e8f3ccca3b7dbaaa287b", ("H-he's huge!!", "Like a mountain!!"), (8, 10)),
    OpeningNarration(0x07E6, 0x9C, 0x94CE, 0x0E14CE, 14, "d25c4239bd11b03a5b351d792fbeaed0be0c050addd49aed65b42e8e70bb2d97", ("N-no way...",), (6,)),
    OpeningNarration(0x002E, 0x99, 0x89D0, 0x0C89D0, 22, "5007192465a5e08e86bc396f0f26822d4dc5b488adbd2db13aae77acaa823c07", ("Ha ha ha ha!!",), (10,)),
    OpeningNarration(0x07E7, 0x9C, 0x94DC, 0x0E14DC, 44, "863e6d469fd43838aecef044faca379feb4279e393388ae06e6d9e1748b87b90", ("W-w-what", "the heck is", "that monster?!"), (4, 6, 9)),
    OpeningNarration(0x076B, 0x9B, 0xE9D8, 0x0DE9D8, 66, "8a18b11add16504e23a17fb8e3354b9a518db91c7646904e309d6e11a744026f", ("Ha ha ha!", "How's that,", "Kakarot?!", "You're done too!"), (5, 9, 7, 8)),
    OpeningNarration(0x07E8, 0x9C, 0x9508, 0x0E1508, 34, "7c785658fdbab811601ce7dd90300374fc9a1c48d22c2e46e2faa717b6bafeb8", ("What the", "hell's going on?!!"), (5, 10)),
    OpeningNarration(0x07E9, 0x9C, 0x952A, 0x0E152A, 12, "51b8c810422dd33295a123fef3caf1971e52019ce4252168af07933b155bd411", ("Recoome!!",), (5,)),
    OpeningNarration(0x07EA, 0x9C, 0x9536, 0x0E1536, 10, "1d4a74ffb0718fe1e4966c44264c82321d5fb351c5ee775b39da4057f8fc0ead", ("Burter!!",), (4,)),
    OpeningNarration(0x07EB, 0x9C, 0x9540, 0x0E1540, 10, "c04c981134d43fad6a29d57cd28822e575adc0900180f76a2ee0f5209bb13f98", ("Jeice!!",), (4,)),
    OpeningNarration(0x07EC, 0x9C, 0x954A, 0x0E154A, 10, "46451d0aa03bdd0e6adb99531fdc268a98d824ac12b20a86c2074c1bac108d5a", ("Guldo!!",), (4,)),
    OpeningNarration(0x07ED, 0x9C, 0x9554, 0x0E1554, 12, "71462c03b3d1ec290a880c53745adb8c401ba2fe949fc5a5bc27950e721b4b51", ("Ginyu!!",), (5,)),
    OpeningNarration(0x07EE, 0x9C, 0x9560, 0x0E1560, 16, "74f8014fc0e39d4aec15ecd9f8b4179213deadbc914c7a5478e77a4cc11b647a", ("All together!",), (7,)),
    OpeningNarration(0x07EF, 0x9C, 0x9570, 0x0E1570, 20, "b5603e209395b706e1cc4c1b367121b38217290a1e6a50bb312d19981f86e425", ("Ginyu Force!!!!",), (9,)),
    OpeningNarration(0x0000, 0x99, 0x87C0, 0x0C87C0, 10, "8264ff205bb897c0ff9cceef06f5288a145727941ce95ec02cab83b91b4ec3e2", ("........",), (4,)),
    OpeningNarration(0x0800, 0x9C, 0x996E, 0x0E196E, 46, "4f7afbc0633053802db031272a8f289f7a7400dd420f3976e5beedb9c3d1f167", ("What's with", "those fighting", "poses...?"), (7, 7, 6)),
    OpeningNarration(0x0801, 0x9C, 0x999C, 0x0E199C, 62, "e628a4703df65033932a724a9cf55a6ec4a24e01c5297d0e1ed949dbc7d5fb15", ("State your wish.", "I shall grant you", "any three wishes."), (9, 10, 9)),
    OpeningNarration(0x0802, 0x9C, 0x99DA, 0x0E19DA, 34, "b2f84f3ba9368d86801bfbc147398d03ba26dcc8d46c1fefc4bfbd303fb461af", ("Make me", "immortal!!"), (5, 10)),
    OpeningNarration(0x0003, 0x99, 0x87EA, 0x0C87EA, 12, "40d0dc835cec8bd33b14b233247dee90e67bae8fdfa3e7b3ee468b25d92337d8", ("..........",), (5,)),
    OpeningNarration(0x0803, 0x9C, 0x99FC, 0x0E19FC, 34, "20da39b2a6e98c99cdf5b8a13106c7343be46aa22916dcedd7712ad21434a904", ("I'm a Saiyan from", "Earth!"), (9, 6)),
    OpeningNarration(0x0804, 0x9C, 0x9A1E, 0x0E1A1E, 78, "faef76a7848bab342fb78df5c0838541f41524934186205232701b9131026c0c", ("For the Saiyans", "you killed...", "And for the", "Namekians here..."), (8, 9, 9, 9)),
    OpeningNarration(0x0805, 0x9C, 0x9A6C, 0x0E1A6C, 24, "13f37b31b4dde600a60b17f983f15ef38910baedf125feda5091b3f967bd69b2", ("I'll", "beat you!!"), (4, 6)),
)

OPENING_TEXTS = OPENING_NARRATIONS + OPENING_RECAP

# Compatibility aliases for the first implemented narration record.
OPENING_STREAM_OFFSET = OPENING_NARRATIONS[0].offset
OPENING_STREAM_LENGTH = OPENING_NARRATIONS[0].length
OPENING_SOURCE_SHA256 = OPENING_NARRATIONS[0].source_sha256
OPENING_LINES = OPENING_NARRATIONS[0].lines
CELLS_PER_LINE = OPENING_NARRATIONS[0].line_cells[0]
FONT_5X7 = {
    " ": ("00000",) * 7,
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "'": ("00100", "00100", "00000", "00000", "00000", "00000", "00000"),
    ",": ("00000", "00000", "00000", "00000", "00000", "00110", "00100"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00110", "00110"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "a": ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    "b": ("10000", "10000", "10110", "11001", "10001", "10001", "11110"),
    "c": ("00000", "00000", "01111", "10000", "10000", "10000", "01111"),
    "d": ("00001", "00001", "01101", "10011", "10001", "10011", "01101"),
    "e": ("00000", "00000", "01110", "10001", "11111", "10000", "01111"),
    "f": ("00111", "01000", "11110", "01000", "01000", "01000", "01000"),
    "g": ("00000", "01111", "10001", "01111", "00001", "10001", "01110"),
    "h": ("10000", "10000", "10110", "11001", "10001", "10001", "10001"),
    "i": ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    "j": ("00010", "00000", "00110", "00010", "00010", "10010", "01100"),
    "k": ("10000", "10001", "10010", "11100", "10010", "10001", "10001"),
    "l": ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    "m": ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    "n": ("00000", "00000", "10110", "11001", "10001", "10001", "10001"),
    "o": ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    "p": ("00000", "00000", "11110", "10001", "11110", "10000", "10000"),
    "r": ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    "s": ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    "t": ("00100", "00100", "11111", "00100", "00100", "00100", "00011"),
    "u": ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    "v": ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    "w": ("00000", "00000", "10001", "10001", "10101", "10101", "01010"),
    "y": ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
}


def encode_opening_stream(narration: OpeningNarration = OPENING_NARRATIONS[0]) -> bytes:
    """Encode one English opening stream in the original 16-bit structure."""

    words = []
    for line_number, (line, cells) in enumerate(zip(narration.lines, narration.line_cells)):
        words.extend(
            encode_latin_line(
                line, cells, context=f"opening selector ${narration.selector:04X} line {line_number + 1}"
            )
        )
        if line_number != len(narration.lines) - 1:
            words.append(TEXT_LINE_BREAK)
    words.append(TEXT_TERMINATOR)
    encoded = b"".join(word.to_bytes(2, "little") for word in words)
    if len(encoded) != narration.length:
        raise WorkstationError(
            f"selector ${narration.selector:04X} encoded stream is {len(encoded)} bytes; "
            f"expected {narration.length}"
        )
    return encoded


def apply_opening_translation(original: bytes) -> bytes:
    """Validate and patch the supported original ROM without relocation."""

    for narration in OPENING_TEXTS:
        source = original[narration.offset : narration.offset + narration.length]
        if (
            len(source) != narration.length
            or hashlib.sha256(source).hexdigest() != narration.source_sha256
        ):
            raise WorkstationError(
                f"selector ${narration.selector:04X} source stream does not match the supported original"
            )

    patched = bytearray(original)
    for narration in OPENING_TEXTS:
        bounded_write(
            patched,
            narration.offset,
            encode_opening_stream(narration),
            f"opening narration selector ${narration.selector:04X}",
        )
    return bytes(patched)