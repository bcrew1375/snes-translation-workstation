"""Tests for packed-Latin automatic-opening translation."""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "toolkit"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dbz_kakusei_hen.build import build  # noqa: E402
from dbz_kakusei_hen.glyphs import LATIN_MARKER, decode_glyph_codes  # noqa: E402
from dbz_kakusei_hen.opening_translation import (  # noqa: E402
    OPENING_NARRATIONS,
    OPENING_RECAP,
    OPENING_STREAM_LENGTH,
    OPENING_STREAM_OFFSET,
    OPENING_TEXTS,
    apply_opening_translation,
    encode_opening_stream,
)
from dbz_kakusei_hen.scenario import TEXT_LINE_BREAK, TEXT_TERMINATOR, decode_text_stream  # noqa: E402


class OpeningTranslationTest(unittest.TestCase):
    def test_authored_lines_fit_original_two_character_cells(self):
        for narration in OPENING_TEXTS:
            with self.subTest(selector=f"${narration.selector:04X}"):
                self.assertEqual(len(narration.lines), len(narration.line_cells))
                for line, cells in zip(narration.lines, narration.line_cells):
                    self.assertLessEqual(len(line), cells * 2)

    def test_streams_are_marked_and_retain_original_structures(self):
        for narration in OPENING_TEXTS:
            encoded = encode_opening_stream(narration)
            words = tuple(
                int.from_bytes(encoded[offset:offset + 2], "little")
                for offset in range(0, len(encoded), 2)
            )
            with self.subTest(selector=f"${narration.selector:04X}"):
                self.assertEqual(len(encoded), narration.length)
                self.assertEqual(words.count(TEXT_LINE_BREAK), len(narration.lines) - 1)
                self.assertEqual(words[-1], TEXT_TERMINATOR)
                glyph_words = tuple(word for word in words[:-1] if word != TEXT_LINE_BREAK)
                self.assertEqual(len(glyph_words), sum(narration.line_cells))
                self.assertTrue(all(word & LATIN_MARKER for word in glyph_words))
                expected = "\n".join(
                    line.ljust(cells * 2)
                    for line, cells in zip(narration.lines, narration.line_cells)
                )
                self.assertEqual(decode_glyph_codes(words), expected)

    def test_first_stream_compatibility_aliases_remain_valid(self):
        self.assertEqual(OPENING_STREAM_OFFSET, OPENING_NARRATIONS[0].offset)
        self.assertEqual(OPENING_STREAM_LENGTH, OPENING_NARRATIONS[0].length)
        self.assertEqual(encode_opening_stream(), encode_opening_stream(OPENING_NARRATIONS[0]))


@unittest.skipUnless((PROJECT_ROOT / "rom" / "original.sfc").is_file(), "original ROM absent")
class OriginalRomOpeningTranslationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (PROJECT_ROOT / "rom" / "original.sfc").read_bytes()
        cls.translated = apply_opening_translation(cls.original)

    def test_source_stream_digests_match_supported_original(self):
        for narration in OPENING_TEXTS:
            source = self.original[narration.offset:narration.offset + narration.length]
            with self.subTest(selector=f"${narration.selector:04X}"):
                self.assertEqual(hashlib.sha256(source).hexdigest(), narration.source_sha256)

    def test_translated_streams_decode_with_original_line_structures(self):
        for narration in OPENING_TEXTS:
            stream = decode_text_stream(self.translated, bank=narration.bank, address=narration.address)
            with self.subTest(selector=f"${narration.selector:04X}"):
                self.assertEqual(stream.line_lengths, narration.line_cells)
                self.assertEqual(stream.data, encode_opening_stream(narration))

    def test_project_build_updates_checksum_and_metadata(self):
        result = build(self.original, None)
        complement = int.from_bytes(result.data[0x7FDC:0x7FDE], "little")
        checksum = int.from_bytes(result.data[0x7FDE:0x7FE0], "little")
        self.assertEqual(complement ^ checksum, 0xFFFF)
        zeroed = bytearray(result.data)
        zeroed[0x7FDC:0x7FE0] = bytes(4)
        self.assertEqual(checksum, sum(zeroed) & 0xFFFF)
        self.assertEqual(len(OPENING_RECAP), 22)
        self.assertEqual(result.metadata["opening_selectors"], [f"${r.selector:04X}" for r in OPENING_TEXTS])


if __name__ == "__main__":
    unittest.main()