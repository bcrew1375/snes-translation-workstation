"""Tests for opening fixed labels and X/Y/B choice resources."""

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
from dbz_kakusei_hen.fixed_resource_translation import (  # noqa: E402
    apply_fixed_resource_translation,
    encode_fixed_resource,
    load_fixed_resource_records,
)
from dbz_kakusei_hen.glyphs import decode_latin_cell  # noqa: E402


class FixedResourceManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = load_fixed_resource_records(PROJECT_ROOT / "translation" / "choices.toml")

    def test_fixed_labels_and_button_order_are_explicit(self):
        self.assertEqual(
            [record.record_type for record in self.records],
            ["fixed_label"] * 5 + ["option"] * 14,
        )
        self.assertEqual(
            [record.button for record in self.records],
            ["", "", "", "", "", "X", "Y", "B", "X", "Y", "B", "X", "Y", "X", "Y", "B", "X", "Y", "B"],
        )
        self.assertEqual([record.english for record in self.records], [
            "World Tournament Arena", "Papaya Island", "Preliminaries Venue",
            "DBZ Trivia Quiz", "(Choice)",
            "You're bleeding!", "Are you sick?", "You look sexy.",
            "You haven't changed!", "I grew more than you!", "You look well, Krillin!",
            "You're Chi-Chi!?", "Who are you?",
            "Huh?", "You again...", "King Chappa...",
            "He's an assassin.", "I don't know him either.", "I've seen him somewhere.",
        ])


@unittest.skipUnless((PROJECT_ROOT / "rom" / "original.sfc").is_file(), "original ROM absent")
class OriginalRomFixedResourceTranslationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (PROJECT_ROOT / "rom" / "original.sfc").read_bytes()
        cls.records = load_fixed_resource_records(PROJECT_ROOT / "translation" / "choices.toml")
        cls.translated = apply_fixed_resource_translation(cls.original, cls.original, cls.records)

    def test_sources_and_pointers_are_pinned(self):
        for record in self.records:
            source = self.original[record.original_offset:record.original_offset + record.original_length]
            with self.subTest(record=record.id):
                self.assertEqual(hashlib.sha256(source).hexdigest(), record.source_sha256)
                self.assertEqual(
                    self.original[record.pointer_offset:record.pointer_offset + 2],
                    record.original_address.to_bytes(2, "little"),
                )

    def test_every_record_encodes_and_terminates_at_its_reviewed_destination(self):
        expected_ranges = {
            "tournament_arena_label": (0x047FB4, 0x047FCC),
            "papaya_island_label": (0x047FCC, 0x047FDC),
            "preliminaries_venue_label": (0x047FDC, 0x047FF2),
            "tournament_quiz_header": (0x0C41A8, 0x0C41BE),
            "generic_choice_header": (0x0C41BE, 0x0C41C8),
            "tournament_quiz_02_x": (0x0C7502, 0x0C751C),
            "tournament_quiz_02_y": (0x0C751C, 0x0C7538),
            "tournament_quiz_02_b": (0x0C7538, 0x0C7556),
            "mercenary_tao_quiz_y": (0x0C756A, 0x0C7588),
            "mercenary_tao_quiz_b": (0x0C7588, 0x0C75A6),
        }
        occupied = []
        for record in self.records:
            source = self.original[record.original_offset:record.original_offset + record.original_length]
            encoded = encode_fixed_resource(record, source)
            written = self.translated[record.destination_offset:record.destination_offset + len(encoded)]
            words = tuple(int.from_bytes(written[i:i + 2], "little") for i in range(0, len(written), 2))
            occupied.append((record.destination_offset, record.destination_offset + len(encoded), record.id))
            with self.subTest(record=record.id):
                prefix_bytes = record.prefix_words * 2
                self.assertEqual(written[:prefix_bytes], source[:prefix_bytes])
                self.assertEqual(
                    "".join(decode_latin_cell(word) for word in words[record.prefix_words:-1]).rstrip(),
                    record.english,
                )
                self.assertEqual(words[-1], 0)
                if record.id in expected_ranges:
                    self.assertEqual(
                        (record.destination_offset, record.destination_offset + len(encoded)),
                        expected_ranges[record.id],
                    )
        ordered = sorted(occupied)
        for left, right in zip(ordered, ordered[1:]):
            self.assertLessEqual(left[1], right[0], f"{left[2]} overlaps {right[2]}")

    def test_relocated_records_update_only_their_same_bank_pointers(self):
        for record in self.records:
            expected = record.destination_address.to_bytes(2, "little")
            with self.subTest(record=record.id):
                self.assertEqual(self.translated[record.pointer_offset:record.pointer_offset + 2], expected)

    def test_scenario_choice_command_and_branch_bytes_are_unchanged(self):
        result = build(self.original, None)
        self.assertEqual(result.data[0x088179:0x088193], self.original[0x088179:0x088193])
        self.assertEqual(result.data[0x0881FD:0x088218], self.original[0x0881FD:0x088218])
        self.assertEqual(result.data[0x088718:0x088733], self.original[0x088718:0x088733])
        self.assertEqual(result.metadata["fixed_labels"], {
            "tournament_arena_label": "World Tournament Arena",
            "papaya_island_label": "Papaya Island",
            "preliminaries_venue_label": "Preliminaries Venue",
            "tournament_quiz_header": "DBZ Trivia Quiz",
            "generic_choice_header": "(Choice)",
        })
        self.assertEqual(result.metadata["opening_choices"], {
            "X": "You're bleeding!",
            "Y": "Are you sick?",
            "B": "You look sexy.",
        })
        self.assertEqual(result.metadata["fixed_options"], {
            "tournament_quiz_x": "You're bleeding!",
            "tournament_quiz_y": "Are you sick?",
            "tournament_quiz_b": "You look sexy.",
            "tournament_quiz_02_x": "You haven't changed!",
            "tournament_quiz_02_y": "I grew more than you!",
            "tournament_quiz_02_b": "You look well, Krillin!",
            "chichi_choice_x": "You're Chi-Chi!?",
            "chichi_choice_y": "Who are you?",
            "preliminaries_quiz_x": "Huh?",
            "preliminaries_quiz_y": "You again...",
            "preliminaries_quiz_b": "King Chappa...",
            "mercenary_tao_quiz_x": "He's an assassin.",
            "mercenary_tao_quiz_y": "I don't know him either.",
            "mercenary_tao_quiz_b": "I've seen him somewhere.",
        })


if __name__ == "__main__":
    unittest.main()