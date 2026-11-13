"""Tests for the battle-HUD resource codec and tile transform."""

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

from dbz_kakusei_hen.battle_hud import (  # noqa: E402
    compress_resource,
    decompress_resource,
    interleave_2bpp_blocks,
    replace_resource,
)
from dbz_kakusei_hen.build import build  # noqa: E402
from dbz_kakusei_hen.glyphs import decode_latin_cell  # noqa: E402
from dbz_kakusei_hen.hud_translation import (  # noqa: E402
    apply_hud_translation,
    encode_hud_text,
    load_hud_text_records,
)


class BattleHudCodecTest(unittest.TestCase):
    def test_literal_and_overlapping_reference_round_trip(self):
        source = b"ABCABCABCABC" + bytes(range(32)) + b"\0" * 80
        encoded = compress_resource(source)
        decoded = decompress_resource(encoded)
        self.assertEqual(decoded.data, source)
        self.assertEqual(decoded.consumed, len(encoded))
        self.assertEqual(compress_resource(source), encoded)

    def test_initial_reference_zero_fills_like_the_game(self):
        encoded = b"\x05\x00\x00\x2F\x00"
        self.assertEqual(decompress_resource(encoded).data, b"\0" * 5)

    def test_invalid_zero_distance_is_rejected(self):
        with self.assertRaisesRegex(WorkstationError, "zero-distance"):
            decompress_resource(b"\x03\x00\x00\x00\x00")

    def test_post_decompression_interleave(self):
        self.assertEqual(
            interleave_2bpp_blocks(bytes(range(16))),
            bytes((0, 8, 1, 9, 2, 10, 3, 11, 4, 12, 5, 13, 6, 14, 7, 15)),
        )
        with self.assertRaisesRegex(WorkstationError, "16-byte blocks"):
            interleave_2bpp_blocks(b"short")

    def test_replacement_enforces_reviewed_compressed_extent(self):
        original = bytes(64)
        with self.assertRaisesRegex(WorkstationError, "only 3 are available"):
            replace_resource(original, 8, bytes(range(32)), maximum_size=3)


@unittest.skipUnless((PROJECT_ROOT / "rom" / "original.sfc").is_file(), "original ROM absent")
class OriginalRomBattleHudCodecTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = (PROJECT_ROOT / "rom" / "original.sfc").read_bytes()

    def test_confirmed_battle_setup_resources_decode_to_pinned_extents(self):
        expected = {
            0x180000: (0x4000, 0x34DA, "234b8b596e8f53c8f7e0e7dc17d43ba9fcf75809da42470bb65538ddded310d7"),
            0x1834DA: (0x1000, 0x0817, "d2db60a7f8af2d28e796e0ae3ddedf9f086a975e2ec31f64bf2bcf8bcad10c0b"),
            0x1A8000: (0x35A0, 0x1B08, "28af5fd19e731835b5d117ccd4d36244b73f103618ce634b21fe6cb2574fc2cf"),
            0x1003E0: (0x0800, 0x03BD, "5d061991104ab5e8ff9b1cc296b34e4b540f333e52c947cb0737d54300098a0c"),
            0x108000: (0x1400, 0x0B4D, "d407037302c0b321eb841513f86c25d5aef2c9f9b505c982d96444d3050c814c"),
            0x110580: (0x1A00, 0x124A, "82db1a3e6b034c47a66c8e9b7aa5a446815aa438730d429111589ba96d868185"),
        }
        for offset, (length, consumed, digest) in expected.items():
            with self.subTest(offset=f"${offset:06X}"):
                resource = decompress_resource(self.rom, offset)
                self.assertEqual(len(resource.data), length)
                self.assertEqual(resource.consumed, consumed)
                self.assertEqual(hashlib.sha256(resource.data).hexdigest(), digest)

    def test_primary_resources_recompress_to_their_exact_original_sizes(self):
        for offset in (0x180000, 0x1834DA):
            with self.subTest(offset=f"${offset:06X}"):
                resource = decompress_resource(self.rom, offset)
                encoded = compress_resource(resource.data)
                self.assertEqual(len(encoded), resource.consumed)
                self.assertEqual(decompress_resource(encoded).data, resource.data)

    def test_all_observed_resources_recompress_within_small_reviewable_delta(self):
        for offset in (0x1A8000, 0x1003E0, 0x108000, 0x110580):
            with self.subTest(offset=f"${offset:06X}"):
                resource = decompress_resource(self.rom, offset)
                encoded = compress_resource(resource.data)
                self.assertEqual(decompress_resource(encoded).data, resource.data)
                self.assertLessEqual(len(encoded) - resource.consumed, 7)


@unittest.skipUnless((PROJECT_ROOT / "rom" / "original.sfc").is_file(), "original ROM absent")
class OriginalRomBattleHudTranslationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (PROJECT_ROOT / "rom" / "original.sfc").read_bytes()
        cls.records = load_hud_text_records(PROJECT_ROOT / "translation" / "hud.toml")
        cls.translated = apply_hud_translation(cls.original, cls.original, cls.records)

    def test_confirmed_first_hud_records_are_explicit(self):
        self.assertEqual(
            [(record.id, record.english) for record in self.records],
            [
                ("first_hud_fighter_anonymous", "Anonymous"),
                ("first_hud_hp_label", "HP"),
                ("first_hud_power_label", "Power"),
                ("first_hud_dash_punch", "Dash Punch"),
                ("first_hud_dash_punch_alias", "Dash Punch"),
                ("first_hud_homing_ki", "Homing Ki"),
                ("first_hud_charge", "Rush"),
                ("first_hud_open_state", "Open"),
            ],
        )

    def test_sources_are_hash_pinned_and_encoded_in_place(self):
        for record in self.records:
            source = self.original[
                record.original_offset : record.original_offset + record.original_length
            ]
            with self.subTest(record=record.id):
                self.assertEqual(hashlib.sha256(source).hexdigest(), record.source_sha256)
                encoded = encode_hud_text(record)
                self.assertEqual(len(encoded), len(record.patch_offsets) * 2)
                decoded = "".join(
                    decode_latin_cell(int.from_bytes(encoded[index:index + 2], "little"))
                    for index in range(0, len(encoded), 2)
                )
                self.assertEqual(decoded.rstrip(), record.english)
                for index, offset in enumerate(record.patch_offsets):
                    self.assertEqual(
                        self.translated[offset:offset + 2],
                        encoded[index * 2:index * 2 + 2],
                    )

    def test_numeric_calls_terminators_and_geometry_are_unchanged(self):
        unchanged = (
            (0x11861, 0x11888),
            (0x118A7, 0x118D4),
            (0x23F20, 0x23F22),
            (0x24A1E, 0x24A20),
            (0x24BF0, 0x24BF2),
            (0x246F4, 0x246F6),
            (0x24B1E, 0x24B20),
            (0x17703, 0x17705),
        )
        for start, end in unchanged:
            with self.subTest(start=f"${start:06X}"):
                self.assertEqual(self.translated[start:end], self.original[start:end])

    def test_project_build_reports_and_applies_hud_translation(self):
        result = build(self.original, None)
        self.assertEqual(
            result.metadata["battle_hud"],
            {
                "first_hud_fighter_anonymous": "Anonymous",
                "first_hud_hp_label": "HP",
                "first_hud_power_label": "Power",
                "first_hud_dash_punch": "Dash Punch",
                "first_hud_dash_punch_alias": "Dash Punch",
                "first_hud_homing_ki": "Homing Ki",
                "first_hud_charge": "Rush",
                "first_hud_open_state": "Open",
            },
        )
        for record in self.records:
            encoded = encode_hud_text(record)
            for index, offset in enumerate(record.patch_offsets):
                self.assertEqual(result.data[offset:offset + 2], encoded[index * 2:index * 2 + 2])


if __name__ == "__main__":
    unittest.main()