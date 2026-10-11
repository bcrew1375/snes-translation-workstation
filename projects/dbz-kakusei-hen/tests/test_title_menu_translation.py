"""Tests for packed-Latin title-menu translation."""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "toolkit"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from snesworkbench.errors import WorkstationError  # noqa: E402

from dbz_kakusei_hen.build import build  # noqa: E402
from dbz_kakusei_hen.glyphs import LATIN_MARKER, decode_latin_cell  # noqa: E402
from dbz_kakusei_hen.title_menu_translation import (  # noqa: E402
    FIXED_NATIVE_SUFFIX_RECORD,
    apply_title_menu_translation,
    decode_menu_line_cells,
    encode_title_menu,
    load_title_menu_records,
)


class TitleMenuTranslationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = load_title_menu_records(PROJECT_ROOT / "translation" / "menu.tsv")

    def test_all_reachable_opening_menu_records_are_tracked(self):
        fixed_ids = [
            "title_menu_no_save", "title_menu_with_save", "new_game_start_method",
            "options_sound_stereo", "options_sound_mono",
        ]
        self.assertEqual(
            [record.id for record in self.records],
            fixed_ids + [f"options_bgm_{index:02d}" for index in range(20)],
        )
        self.assertEqual(
            [record.english.split("\n") for record in self.records[:5]],
            [
                ["New Game", "Options"],
                ["Continue", "New Game", "Options"],
                ["Start New Game", "Enter Password"],
                ["Sound Stereo"],
                ["Sound Mono"],
            ],
        )

    def test_encoded_lines_are_packed_and_apply_character_offsets(self):
        structures = [(8, 7), (8, 8, 7), (9, 8), (9,), (9,)]
        for record, line_cells in zip(self.records[:5], structures):
            data = encode_title_menu(record, line_cells)
            words = tuple(int.from_bytes(data[i:i + 2], "little") for i in range(0, len(data), 2))
            cursor = 0
            for line, cells, offset in zip(record.english.split("\n"), line_cells, record.character_offsets):
                line_words = words[cursor:cursor + cells]
                decoded = "".join(decode_latin_cell(word) for word in line_words)
                with self.subTest(record=record.id, line=line):
                    self.assertTrue(all(word & LATIN_MARKER for word in line_words))
                    self.assertEqual(decoded, (" " * offset + line).ljust(cells * 2))
                cursor += cells + (record.record_type == "terminated")

    def test_overlong_line_is_rejected(self):
        record = self.records[0]
        changed = record.__class__(**{**record.__dict__, "english": "X" * 12 + "\nOptions"})
        with self.assertRaisesRegex(WorkstationError, "exceeds"):
            encode_title_menu(changed, (8, 7))


@unittest.skipUnless((PROJECT_ROOT / "rom" / "original.sfc").is_file(), "original ROM absent")
class OriginalRomTitleMenuTranslationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (PROJECT_ROOT / "rom" / "original.sfc").read_bytes()
        cls.records = load_title_menu_records(PROJECT_ROOT / "translation" / "menu.tsv")
        cls.translated = apply_title_menu_translation(cls.original, cls.original, cls.records)

    def test_source_locations_lengths_digests_and_structures(self):
        self.assertEqual([record.length for record in self.records], [34, 52, 38] + [18] * 22)
        expected_structures = [(8, 7), (8, 8, 7), (9, 8)] + [(9,)] * 22
        for record, structure in zip(self.records, expected_structures):
            source = self.original[record.offset:record.offset + record.length]
            with self.subTest(record=record.id):
                self.assertEqual(hashlib.sha256(source).hexdigest(), record.source_sha256)
                self.assertEqual(decode_menu_line_cells(source, record.id, record.record_type), structure)

    def test_encoded_streams_retain_original_allocations(self):
        for record in self.records:
            source = self.original[record.offset:record.offset + record.length]
            structure = decode_menu_line_cells(source, record.id, record.record_type)
            encoded = encode_title_menu(record, structure, source)
            with self.subTest(record=record.id):
                self.assertEqual(len(encoded), record.length)
                self.assertEqual(decode_menu_line_cells(encoded, record.id, record.record_type), structure)
                self.assertEqual(self.translated[record.offset:record.offset + record.length], encoded)

    def test_bgm_records_preserve_native_numeral_words(self):
        for record in self.records:
            if record.record_type != FIXED_NATIVE_SUFFIX_RECORD:
                continue
            source = self.original[record.offset:record.offset + record.length]
            translated = self.translated[record.offset:record.offset + record.length]
            with self.subTest(record=record.id):
                self.assertEqual(translated[-4:], source[-4:])
                self.assertTrue(all(
                    int.from_bytes(translated[i:i + 2], "little") & LATIN_MARKER
                    for i in range(0, len(translated) - 4, 2)
                ))

    def test_project_build_reports_menu_lines(self):
        result = build(self.original, None)
        self.assertEqual(
            result.metadata["title_menu_lines"],
            [
                ["New Game", "Options"], ["Continue", "New Game", "Options"],
                ["Start New Game", "Enter Password"], ["Sound Stereo"], ["Sound Mono"],
            ] + [["BGM"]] * 20,
        )


if __name__ == "__main__":
    unittest.main()