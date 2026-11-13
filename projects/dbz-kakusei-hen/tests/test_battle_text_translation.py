"""Tests for the Goku/Chi-Chi battle-script text resources."""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "toolkit"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dbz_kakusei_hen.battle_text_translation import (  # noqa: E402
    apply_battle_text_translation,
    encode_battle_text,
    load_battle_text_records,
    source_line_cells,
)
from dbz_kakusei_hen.glyphs import decode_latin_cell  # noqa: E402
from dbz_kakusei_hen.scenario import TEXT_LINE_BREAK  # noqa: E402


class BattleTextManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = load_battle_text_records(PROJECT_ROOT / "translation" / "battle_text.toml")

    def test_path_resource_order_and_speakers_are_explicit(self):
        self.assertEqual(
            [record.resource_id for record in self.records],
            [
                0x1000,
                0x1001,
                *range(0x1180, 0x1191),
                0x10B6,
                0x10B7,
                0x10B8,
                0x10B9,
                0x1006,
                0x1007,
                0x11AB,
                0x11AC,
                0x11A4,
                0x11A5,
                0x11A6,
                0x11A7,
                0x11A8,
                0x11A9,
                0x10BE,
                0x10BF,
                0x10C0,
                0x10C1,
                0x10C2,
                0x10C4,
                0x10C3,
            ],
        )
        self.assertEqual([record.path for record in self.records[:2]], ["opening"] * 2)
        self.assertEqual([record.speaker for record in self.records[:2]], ["Goku", "Chi-Chi"])
        self.assertEqual([record.path for record in self.records[2:21]], ["chichi_zero"] * 19)
        self.assertEqual([record.path for record in self.records[21:23]], ["goku_zero"] * 2)
        self.assertEqual([record.speaker for record in self.records[21:23]], ["Goku", "Chi-Chi"])
        self.assertEqual([record.path for record in self.records[23:27]], ["junior_opening"] * 4)
        self.assertEqual([record.speaker for record in self.records[23:27]], ["Junior", "Goku", "Junior", "Junior"])
        self.assertEqual([record.path for record in self.records[27:35]], ["junior_win"] * 8)
        self.assertEqual([record.path for record in self.records[35:]], ["junior_loss"] * 5)

    def test_all_authored_lines_obey_the_confirmed_limit(self):
        for record in self.records:
            with self.subTest(record=record.id):
                self.assertTrue(record.english)
                self.assertTrue(all(len(line) <= 21 for line in record.english))

    def test_chichi_bridal_promise_and_goku_question_are_coordinated(self):
        records = {record.resource_id: record for record in self.records}
        self.assertEqual(
            records[0x1187].english,
            ("You said you'd", "make me your bride!!"),
        )
        self.assertEqual(
            records[0x1188].english,
            ("What's a bride!?", "Explain it!!"),
        )

    def test_goku_defeat_exchange_preserves_disbelief_and_warning(self):
        records = {record.resource_id: record for record in self.records}
        self.assertEqual(records[0x10B8].english, ("N-no way...",))
        self.assertEqual(
            records[0x10B9].english,
            ("Don't underestimate", "this woman!!"),
        )


@unittest.skipUnless((PROJECT_ROOT / "rom" / "original.sfc").is_file(), "original ROM absent")
class OriginalRomBattleTextTranslationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (PROJECT_ROOT / "rom" / "original.sfc").read_bytes()
        cls.records = load_battle_text_records(PROJECT_ROOT / "translation" / "battle_text.toml")
        cls.translated = apply_battle_text_translation(cls.original, cls.original, cls.records)

    def test_sources_pointers_and_hashes_are_pinned(self):
        for record in self.records:
            source = self.original[record.original_offset:record.original_offset + record.original_length]
            with self.subTest(record=record.id):
                self.assertEqual(hashlib.sha256(source).hexdigest(), record.source_sha256)
                self.assertEqual(
                    self.original[record.pointer_offset:record.pointer_offset + 2],
                    record.original_address.to_bytes(2, "little"),
                )

    def test_encoding_preserves_native_pagination_and_allocation(self):
        for record in self.records:
            source = self.original[record.original_offset:record.original_offset + record.original_length]
            encoded = encode_battle_text(record, source)
            words = tuple(int.from_bytes(encoded[index:index + 2], "little") for index in range(0, len(encoded), 2))
            decoded_lines = []
            current = []
            for word in words[:-1]:
                if word == TEXT_LINE_BREAK:
                    decoded_lines.append("".join(current).rstrip())
                    current = []
                else:
                    current.append(decode_latin_cell(word))
            decoded_lines.append("".join(current).rstrip())
            with self.subTest(record=record.id):
                self.assertEqual(tuple(decoded_lines), record.english)
                self.assertEqual(len(encoded), record.original_length)
                self.assertEqual(source_line_cells(encoded, context=record.id), source_line_cells(source, context=record.id))
                self.assertEqual(
                    self.translated[record.original_offset:record.original_offset + record.original_length],
                    encoded,
                )


if __name__ == "__main__":
    unittest.main()