"""Deterministic English patch for the complete automatic opening sequence.

The original renderer advances by 12 pixels for each 16x16 glyph. To retain
the original stream addresses, line structures, and allocations, each custom
glyph below contains two narrow 5x7 Latin characters separated by one pixel.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from snesworkbench.errors import WorkstationError
from snesworkbench.graphics import encode_tiles
from snesworkbench.patching import bounded_write

from .scenario import TEXT_LINE_BREAK, TEXT_TERMINATOR, glyph_source


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
CHARACTERS_PER_CELL = 2
SPACE_GLYPH_CODE = 0x0272

# This vocabulary documents every pair used by the current English text. The
# physical codes are assigned below from records proven absent from every
# decoded command-$08 stream in the pinned original ROM.
_PAIR_GLYPH_VOCABULARY = {
    " B": 0x0273,
    " a": 0x0274,
    " g": 0x0275,
    " m": 0x0276,
    " s": 0x0277,
    " w": 0x02D1,
    ", ": 0x02D2,
    "..": 0x02D3,
    "Dr": 0x02D4,
    "Lo": 0x02D5,
    "Ga": 0x02D6,
    "Sh": 0x02D7,
    "ag": 0x0414,
    "ai": 0x0415,
    "al": 0x0416,
    "ap": 0x0417,
    "ar": 0x0420,
    "as": 0x0421,
    "d ": 0x0422,
    "e ": 0x0423,
    "en": 0x0424,
    "er": 0x0425,
    "io": 0x0426,
    "ls": 0x0427,
    "go": 0x0430,
    "h.": 0x0431,
    "ic": 0x0432,
    "my": 0x0433,
    "is": 0x0434,
    "it": 0x0435,
    "lo": 0x0436,
    "rb": 0x0437,
    "n ": 0x0441,
    "nd": 0x0442,
    "ng": 0x0443,
    "nt": 0x0444,
    "ny": 0x0445,
    "on": 0x0446,
    "pe": 0x0447,
    "ra": 0x0450,
    "ro": 0x0451,
    "se": 0x0452,
    "st": 0x0453,
    "th": 0x0454,
    "ve": 0x0455,
    " b": 0x0456,
    " c": 0x0457,
    " e": 0x0460,
    " f": 0x0461,
    " t": 0x0462,
    ". ": 0x0463,
    "Go": 0x0464,
    "It": 0x0465,
    "Th": 0x0466,
    "a ": 0x0467,
    "ac": 0x0470,
    "an": 0x0471,
    "ba": 0x0472,
    "ds": 0x0473,
    "ed": 0x0474,
    "eg": 0x0475,
    "es": 0x0476,
    "ev": 0x0477,
    "ey": 0x0480,
    "fo": 0x0481,
    "ge": 0x0482,
    "h ": 0x0483,
    "he": 0x0484,
    "ht": 0x0485,
    "ig": 0x0486,
    "ku": 0x0487,
    "l.": 0x0490,
    "le": 0x0491,
    "ll": 0x0492,
    "ma": 0x0493,
    "mo": 0x0494,
    "no": 0x0495,
    "nu": 0x0496,
    "os": 0x0497,
    "r.": 0x04A0,
    "re": 0x04A1,
    "ri": 0x04A2,
    "s ": 0x04A3,
    "s,": 0x04A4,
    "si": 0x04A5,
    "ss": 0x04A6,
    "ti": 0x04A7,
    "tr": 0x04B0,
    "tt": 0x04B1,
    "ug": 0x04B2,
    "w ": 0x04B3,
    "w.": 0x04B4,
    "y ": 0x04B5,
    " h": 0x04B6,
    "bu": 0x04B7,
    "ce": 0x04C0,
    "co": 0x04C1,
    "do": 0x04C2,
    "na": 0x04C3,
    "iy": 0x04C4,
    "je": 0x04C5,
    "ki": 0x04C6,
    "om": 0x04C7,
    "or": 0x04D0,
    "rt": 0x04D1,
    "sa": 0x04D2,
    "me": 0x04D3,
    "to": 0x04D4,
    "ul": 0x04D5,
    "us": 0x04D6,
    "yu": 0x04D7,
    " d": 0x041C,
    " i": 0x041D,
    " o": 0x041E,
    " y": 0x041F,
    "! ": 0x0428,
    "!!": 0x0429,
    "'s": 0x042A,
    "? ": 0x042B,
    "?!": 0x042C,
    "A-": 0x042D,
    "Al": 0x042E,
    "An": 0x042F,
    "Bu": 0x0438,
    "Ea": 0x0439,
    "Fo": 0x043A,
    "Gi": 0x043B,
    "Gu": 0x043C,
    "H-": 0x043D,
    "Ha": 0x043E,
    "Ho": 0x043F,
    "I ": 0x0448,
    "I'": 0x0449,
    "Je": 0x044A,
    "Ka": 0x044B,
    "Li": 0x044C,
    "Ma": 0x044D,
    "N-": 0x044E,
    "Na": 0x044F,
    "Re": 0x0458,
    "Sa": 0x0459,
    "St": 0x045A,
    "W-": 0x045B,
    "Wh": 0x045C,
    "Yo": 0x045D,
    "a!": 0x045E,
    "a-": 0x045F,
    "aa": 0x0468,
    "at": 0x0469,
    "ay": 0x046A,
    "be": 0x046B,
    "ck": 0x046C,
    "e!": 0x046D,
    "fi": 0x046E,
    "gh": 0x046F,
    "gr": 0x0478,
    "h!": 0x0479,
    "ha": 0x047A,
    "im": 0x047B,
    "ka": 0x047C,
    "ke": 0x047D,
    "l ": 0x047E,
    "ld": 0x047F,
    "m ": 0x0488,
    "n!": 0x0489,
    "n?": 0x048A,
    "o!": 0x048B,
    "oi": 0x048C,
    "ou": 0x048D,
    "po": 0x048E,
    "r ": 0x048F,
    "rc": 0x0498,
    "s.": 0x0499,
    "sh": 0x049A,
    "t ": 0x049B,
    "t?": 0x049C,
    "u ": 0x049D,
    "u!": 0x049E,
    "u'": 0x049F,
    "ur": 0x04A8,
    "w'": 0x04A9,
    "w-": 0x04AA,
    "wh": 0x04AB,
    "wi": 0x04AC,
    "yo": 0x04AD,
}


def _required_pair_glyphs() -> set[str]:
    required = set()
    for narration in OPENING_TEXTS:
        for line, cells in zip(narration.lines, narration.line_cells):
            padded = line.ljust(cells * CHARACTERS_PER_CELL)
            required.update(
                pair
                for index in range(0, len(padded), CHARACTERS_PER_CELL)
                if (pair := padded[index : index + CHARACTERS_PER_CELL]) != "  "
            )
    return required


PAIR_GLYPH_CODES = {
    pair: code
    for pair, code in zip(
        sorted(_required_pair_glyphs()),
        (
            *range(0x0273, 0x0278),
            *range(0x0280, 0x0285),
            0x0287,
            *range(0x0290, 0x0292),
            *range(0x0293, 0x0296),
            0x0297,
            *range(0x02A0, 0x02A2),
            0x02A3,
            *range(0x02A5, 0x02A7),
            *range(0x02B1, 0x02B8),
            *range(0x02C0, 0x02C4),
            *range(0x02D1, 0x02D8),
            *range(0x03C1, 0x03C8),
            *range(0x03D0, 0x03D5),
            *range(0x03E1, 0x03E7),
            *range(0x0402, 0x0405),
            0x0407,
            *range(0x0411, 0x0418),
            *(code for start in range(0x0420, 0x04E0, 0x10) for code in range(start, start + 8)),
            *range(0x04E0, 0x04E7),
        ),
        strict=True,
    )
}

# Concatenating the four 16-byte source blocks for each allocated code in the
# mapping order above produces this digest in the pinned original ROM. This
# permits use of 60 nonblank orphan records while rejecting any unsupported ROM
# revision or unexpected source-data change.
OPENING_GLYPH_SOURCE_SHA256 = "a3fc54b1727c7b175cab3d4656233251e15cb79504dcf922a5d50e3367f41fb5"


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


def opening_pairs(
    narration: OpeningNarration = OPENING_NARRATIONS[0],
) -> tuple[tuple[str, ...], ...]:
    """Return the narration as fixed-width two-character cells."""

    if len(narration.lines) != len(narration.line_cells):
        raise WorkstationError(f"selector ${narration.selector:04X} line metadata is inconsistent")
    rows = []
    for line, cells in zip(narration.lines, narration.line_cells):
        width = cells * CHARACTERS_PER_CELL
        if len(line) > width:
            raise WorkstationError(
                f"selector ${narration.selector:04X} line exceeds {width} narrow characters: {line!r}"
            )
        padded = line.ljust(width)
        rows.append(tuple(padded[index : index + 2] for index in range(0, width, 2)))
    return tuple(rows)


def encode_opening_stream(narration: OpeningNarration = OPENING_NARRATIONS[0]) -> bytes:
    """Encode one English opening stream in the original 16-bit structure."""

    words = []
    rows = opening_pairs(narration)
    for line_number, row in enumerate(rows):
        for pair in row:
            if pair == "  ":
                words.append(SPACE_GLYPH_CODE)
            else:
                try:
                    words.append(PAIR_GLYPH_CODES[pair])
                except KeyError as error:
                    raise WorkstationError(f"opening pair {pair!r} has no glyph allocation") from error
        if line_number != len(rows) - 1:
            words.append(TEXT_LINE_BREAK)
    words.append(TEXT_TERMINATOR)
    encoded = b"".join(word.to_bytes(2, "little") for word in words)
    if len(encoded) != narration.length:
        raise WorkstationError(
            f"selector ${narration.selector:04X} encoded stream is {len(encoded)} bytes; "
            f"expected {narration.length}"
        )
    return encoded


def render_pair(pair: str) -> tuple[tuple[int, ...], ...]:
    """Render two 5x7 characters as one 16x16, palette-index-3 glyph."""

    if len(pair) != 2:
        raise WorkstationError(f"paired glyph must contain exactly two characters: {pair!r}")
    missing = [character for character in pair if character not in FONT_5X7]
    if missing:
        raise WorkstationError(f"unsupported opening-font character {missing[0]!r}")
    bitmap = [[0] * 16 for _ in range(16)]
    for character_index, character in enumerate(pair):
        origin_x = character_index * 6
        for source_y, pattern in enumerate(FONT_5X7[character]):
            for source_x, pixel in enumerate(pattern):
                if pixel == "1":
                    # Double the seven source rows vertically for a 5x14 glyph.
                    bitmap[1 + source_y * 2][origin_x + source_x] = 3
                    bitmap[2 + source_y * 2][origin_x + source_x] = 3
    return tuple(tuple(row) for row in bitmap)


def encode_pair_glyph(pair: str) -> tuple[bytes, bytes, bytes, bytes]:
    """Encode one paired glyph in the renderer's TL/TR/BL/BR block order."""

    bitmap = render_pair(pair)
    tiles = (
        tuple(row[:8] for row in bitmap[:8]),
        tuple(row[8:] for row in bitmap[:8]),
        tuple(row[:8] for row in bitmap[8:]),
        tuple(row[8:] for row in bitmap[8:]),
    )
    encoded = encode_tiles(tiles, bpp=2)
    return tuple(encoded[index : index + 16] for index in range(0, 64, 16))


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

    glyph_source_bytes = b"".join(
        original[offset : offset + 16]
        for code in PAIR_GLYPH_CODES.values()
        for offset in glyph_source(code).block_offsets
    )
    if hashlib.sha256(glyph_source_bytes).hexdigest() != OPENING_GLYPH_SOURCE_SHA256:
        raise WorkstationError("opening glyph source records do not match the supported original")

    patched = bytearray(original)
    for pair, code in PAIR_GLYPH_CODES.items():
        glyph = glyph_source(code)
        for offset, block in zip(glyph.block_offsets, encode_pair_glyph(pair)):
            bounded_write(patched, offset, block, f"opening glyph ${code:04X}")
    for narration in OPENING_TEXTS:
        bounded_write(
            patched,
            narration.offset,
            encode_opening_stream(narration),
            f"opening narration selector ${narration.selector:04X}",
        )
    return bytes(patched)