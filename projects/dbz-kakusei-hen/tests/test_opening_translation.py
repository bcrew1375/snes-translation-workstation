"""Tests for the fixed-size complete English automatic-opening patch."""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "toolkit"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dbz_kakusei_hen.opening_translation import (  # noqa: E402
    OPENING_NARRATIONS,
    OPENING_RECAP,
    OPENING_TEXTS,
    OPENING_GLYPH_SOURCE_SHA256,
    OPENING_STREAM_LENGTH,
    OPENING_STREAM_OFFSET,
    PAIR_GLYPH_CODES,
    SPACE_GLYPH_CODE,
    apply_opening_translation,
    encode_opening_stream,
    encode_pair_glyph,
    opening_pairs,
    render_pair,
)
from dbz_kakusei_hen.build import build  # noqa: E402
from dbz_kakusei_hen.scenario import (  # noqa: E402
    TEXT_LINE_BREAK,
    TEXT_TERMINATOR,
    decode_glyph,
    decode_text_slots,
    decode_text_stream,
    decode_unique_text_streams,
    glyph_source,
)


class OpeningTranslationTest(unittest.TestCase):
    def test_authored_lines_fit_original_paired_cell_widths(self):
        required_pairs = set()
        for narration in OPENING_TEXTS:
            with self.subTest(selector=f"${narration.selector:04X}"):
                rows = opening_pairs(narration)
                self.assertEqual(len(rows), len(narration.lines))
                self.assertEqual(tuple(map(len, rows)), narration.line_cells)
                for line, cells in zip(narration.lines, narration.line_cells):
                    self.assertLessEqual(len(line), cells * 2)
                required_pairs.update(pair for row in rows for pair in row if pair != "  ")
        self.assertEqual(required_pairs, set(PAIR_GLYPH_CODES))

    def test_streams_retain_original_structures_and_sizes(self):
        for narration in OPENING_TEXTS:
            with self.subTest(selector=f"${narration.selector:04X}"):
                encoded = encode_opening_stream(narration)
                self.assertEqual(len(encoded), narration.length)
                words = tuple(
                    int.from_bytes(encoded[offset : offset + 2], "little")
                    for offset in range(0, len(encoded), 2)
                )
                self.assertEqual(words.count(TEXT_LINE_BREAK), len(narration.lines) - 1)
                self.assertEqual(words[-1], TEXT_TERMINATOR)
                self.assertEqual(
                    len([word for word in words[:-1] if word != TEXT_LINE_BREAK]),
                    sum(narration.line_cells),
                )
                if any(cells * 2 - len(line) >= 2 for line, cells in zip(narration.lines, narration.line_cells)):
                    self.assertIn(SPACE_GLYPH_CODE, words)

    def test_first_stream_compatibility_aliases_remain_valid(self):
        self.assertEqual(OPENING_STREAM_OFFSET, OPENING_NARRATIONS[0].offset)
        self.assertEqual(OPENING_STREAM_LENGTH, OPENING_NARRATIONS[0].length)
        self.assertEqual(encode_opening_stream(), encode_opening_stream(OPENING_NARRATIONS[0]))

    def test_pair_bitmaps_use_game_palette_index_and_fit_twelve_pixels(self):
        for pair in PAIR_GLYPH_CODES:
            with self.subTest(pair=pair):
                bitmap = render_pair(pair)
                self.assertEqual((len(bitmap), len(bitmap[0])), (16, 16))
                self.assertLessEqual({value for row in bitmap for value in row}, {0, 3})
                self.assertFalse(any(row[12:] for row in bitmap if any(row[12:])))

    def test_allocated_glyph_blocks_are_mutually_disjoint(self):
        blocks = []
        for code in PAIR_GLYPH_CODES.values():
            blocks.extend(glyph_source(code).block_offsets)
        self.assertEqual(len(blocks), len(set(blocks)))

    def test_pair_encoding_round_trips_through_game_decoder(self):
        for pair, code in PAIR_GLYPH_CODES.items():
            with self.subTest(pair=pair, code=f"${code:04X}"):
                source = glyph_source(code)
                size = max(source.block_offsets) + 16
                fixture = bytearray(size)
                for offset, block in zip(source.block_offsets, encode_pair_glyph(pair)):
                    fixture[offset : offset + 16] = block
                self.assertEqual(decode_glyph(bytes(fixture), code), render_pair(pair))


@unittest.skipUnless((PROJECT_ROOT / "rom" / "original.sfc").is_file(), "original ROM absent")
class OriginalRomOpeningTranslationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (PROJECT_ROOT / "rom" / "original.sfc").read_bytes()
        cls.translated = apply_opening_translation(cls.original)

    def test_source_stream_digests_match_supported_original(self):
        for narration in OPENING_TEXTS:
            with self.subTest(selector=f"${narration.selector:04X}"):
                source = self.original[narration.offset : narration.offset + narration.length]
                self.assertEqual(hashlib.sha256(source).hexdigest(), narration.source_sha256)

    def test_allocated_records_are_disjoint_and_unused_in_supported_original(self):
        slots = decode_text_slots(self.original)
        used_codes = {
            code
            for stream in decode_unique_text_streams(self.original, slots)
            for code in stream.glyph_codes
        }
        self.assertFalse(set(PAIR_GLYPH_CODES.values()) & used_codes)
        blocks = [
            offset
            for code in PAIR_GLYPH_CODES.values()
            for offset in glyph_source(code).block_offsets
        ]
        self.assertEqual(len(blocks), len(set(blocks)))
        source = b"".join(self.original[offset : offset + 16] for offset in blocks)
        self.assertEqual(hashlib.sha256(source).hexdigest(), OPENING_GLYPH_SOURCE_SHA256)

    def test_translated_streams_decode_with_original_line_structures(self):
        for narration in OPENING_TEXTS:
            with self.subTest(selector=f"${narration.selector:04X}"):
                stream = decode_text_stream(
                    self.translated,
                    bank=narration.bank,
                    address=narration.address,
                )
                self.assertEqual(stream.line_lengths, narration.line_cells)
                self.assertEqual(stream.data, encode_opening_stream(narration))

    def test_each_translated_glyph_matches_generated_bitmap(self):
        for pair, code in PAIR_GLYPH_CODES.items():
            with self.subTest(pair=pair):
                self.assertEqual(decode_glyph(self.translated, code), render_pair(pair))

    def test_patch_does_not_change_rom_size(self):
        self.assertEqual(len(self.translated), len(self.original))
        for narration in OPENING_TEXTS:
            with self.subTest(selector=f"${narration.selector:04X}"):
                region = slice(narration.offset, narration.offset + narration.length)
                self.assertNotEqual(self.translated[region], self.original[region])

    def test_project_build_updates_checksum_and_complement(self):
        result = build(self.original, None)
        complement = int.from_bytes(result.data[0x7FDC:0x7FDE], "little")
        checksum = int.from_bytes(result.data[0x7FDE:0x7FE0], "little")
        self.assertEqual(complement ^ checksum, 0xFFFF)
        zeroed = bytearray(result.data)
        zeroed[0x7FDC:0x7FE0] = bytes(4)
        self.assertEqual(checksum, sum(zeroed) & 0xFFFF)
        self.assertEqual(len(OPENING_RECAP), 22)
        self.assertEqual(
            result.metadata["opening_selectors"],
            [f"${record.selector:04X}" for record in OPENING_TEXTS],
        )


if __name__ == "__main__":
    unittest.main()