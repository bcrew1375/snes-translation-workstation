"""Focused source, allocation, and final-ROM tests for Shenron's wish menu."""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "toolkit"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dbz_kakusei_hen.glyphs import decode_glyph_codes  # noqa: E402
from dbz_kakusei_hen.scenario import decode_text_slots, decode_text_stream  # noqa: E402
from dbz_kakusei_hen.translation_build import (  # noqa: E402
    build_translation,
    load_translation_manifests,
    plan_translations,
)


@unittest.skipUnless((PROJECT_ROOT / "rom" / "original.sfc").is_file(), "original ROM absent")
class ShenronWishesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (PROJECT_ROOT / "rom" / "original.sfc").read_bytes()
        cls.records = load_translation_manifests(
            PROJECT_ROOT / "translation" / "patches"
        )
        cls.scene_records = [record for record in cls.records if record.id.startswith("shenron_")]
        cls.plans = plan_translations(
            cls.original,
            cls.scene_records,
            [],
        )
        cls.scene_plans = [plan for plan in cls.plans if plan.record.id.startswith("shenron_")]
        cls.built = build_translation(cls.original, cls.scene_records, []).data

    def test_selectors_hashes_and_portrait_are_pinned(self):
        self.assertEqual([record.selector for record in self.scene_records], list(range(0x0806, 0x080B)))
        slots = decode_text_slots(self.original)
        for plan in self.scene_plans:
            source = self.original[
                plan.record.original_offset:plan.record.original_offset + plan.record.original_length
            ]
            presentation = slots[plan.record.selector].presentation
            with self.subTest(selector=f"${plan.record.selector:04X}"):
                self.assertEqual(hashlib.sha256(source).hexdigest(), plan.record.source_sha256)
                self.assertEqual(presentation.portrait_resource, 0x67)
                self.assertEqual(presentation.portrait_variant, 0x00)

    def test_every_stream_fits_in_place_and_preserves_source_line_layout(self):
        for plan in self.scene_plans:
            with self.subTest(record=plan.record.id):
                self.assertEqual(plan.allocation.strategy, "in-place")
                self.assertLessEqual(len(plan.encoded.data), plan.record.original_length)
                self.assertEqual(
                    tuple(bool(line) for line in plan.record.english),
                    tuple(bool(length) for length in plan.source_stream.line_lengths),
                )

    def test_final_rom_decodes_authored_lines_at_selectors_0806_through_080a(self):
        slots = decode_text_slots(self.built)
        by_selector = {plan.record.selector: plan for plan in self.scene_plans}
        for selector in range(0x0806, 0x080B):
            plan = by_selector[selector]
            slot = slots[selector]
            stream = decode_text_stream(
                self.built,
                bank=slot.pointer_bank,
                address=slot.target_address,
                selectors=(selector,),
            )
            words = tuple(
                int.from_bytes(stream.data[offset:offset + 2], "little")
                for offset in range(0, len(stream.data), 2)
            )
            decoded = decode_glyph_codes(words).split("\n")
            with self.subTest(selector=f"${selector:04X}"):
                self.assertEqual([line.rstrip() for line in decoded], list(plan.record.english))


if __name__ == "__main__":
    unittest.main()