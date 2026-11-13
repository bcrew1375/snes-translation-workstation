"""Focused source, pagination, allocation, and final-ROM tests for root $0018."""

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
from dbz_kakusei_hen.glyphs import decode_glyph_codes  # noqa: E402
from dbz_kakusei_hen.scenario import decode_text_slots, decode_text_stream  # noqa: E402
from dbz_kakusei_hen.translation_build import (  # noqa: E402
    load_reviewed_free_regions,
    load_translation_manifests,
    plan_translations,
)


@unittest.skipUnless((PROJECT_ROOT / "rom" / "original.sfc").is_file(), "original ROM absent")
class JuniorKamiConfrontationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (PROJECT_ROOT / "rom" / "original.sfc").read_bytes()
        cls.records = load_translation_manifests(
            PROJECT_ROOT / "translation" / "patches"
        )
        cls.scene_records = [record for record in cls.records if record.id.startswith("junior_kami_")]
        cls.consecutive_records = [
            record for record in cls.scene_records if record.id != "junior_kami_goku_reaction"
        ]
        cls.plans = plan_translations(
            cls.original,
            cls.records,
            load_reviewed_free_regions(PROJECT_ROOT / "translation" / "ranges"),
        )
        cls.scene_plans = [plan for plan in cls.plans if plan.record.id.startswith("junior_kami_")]
        cls.built = build(cls.original, None).data

    def test_selectors_source_hashes_and_native_blank_lines_are_pinned(self):
        self.assertEqual(
            [record.selector for record in self.consecutive_records],
            list(range(0x030A, 0x0329)),
        )
        reaction = next(
            record for record in self.scene_records if record.id == "junior_kami_goku_reaction"
        )
        self.assertEqual(reaction.selector, 0x002A)
        for plan in self.scene_plans:
            source = self.original[
                plan.record.original_offset:plan.record.original_offset + plan.record.original_length
            ]
            with self.subTest(record=plan.record.id):
                self.assertEqual(hashlib.sha256(source).hexdigest(), plan.record.source_sha256)
                self.assertEqual(
                    tuple(bool(line) for line in plan.record.english),
                    tuple(bool(length) for length in plan.source_stream.line_lengths),
                )

    def test_root_0018_interleaved_reaction_and_recognition_timing_are_pinned(self):
        by_id = {record.id: record for record in self.scene_records}
        self.assertEqual(by_id["junior_kami_goku_reaction"].english, ("What!?",))
        self.assertNotIn("Kami", "\n".join(by_id["junior_kami_06"].english))
        self.assertIn("Kami", "\n".join(by_id["junior_kami_10"].english))

    def test_evil_containment_terminology_fits_visible_lines(self):
        by_id = {record.id: record for record in self.scene_records}
        self.assertEqual(by_id["junior_kami_22"].english, ("Evil Containment!!",))
        self.assertEqual(by_id["junior_kami_23"].english, ("Evil Containment!!",))
        self.assertEqual(by_id["junior_kami_24"].english, ("Containment Reversal!",))
        self.assertTrue(all("Mafuba" not in "\n".join(record.english) for record in self.scene_records))

    def test_allocations_stay_in_bank_99_and_do_not_overlap(self):
        spans = []
        for plan in self.scene_plans:
            with self.subTest(record=plan.record.id):
                self.assertEqual(plan.allocation.bank, 0x99)
                self.assertEqual(plan.allocation.new_offset & 1, 0)
                self.assertLessEqual(plan.allocation.end_offset, 0x0D0000)
            spans.append((plan.allocation.new_offset, plan.allocation.end_offset, plan.record.id))
        ordered = sorted(spans)
        for left, right in zip(ordered, ordered[1:]):
            self.assertLessEqual(left[1], right[0], f"{left[2]} overlaps {right[2]}")

    def test_fragmented_bank_99_space_is_packed_largest_first(self):
        self.assertEqual(
            [plan.record.id for plan in self.plans],
            [record.id for record in self.records if record.status == "implemented"],
        )
        plan = next(plan for plan in self.scene_plans if plan.record.selector == 0x0311)
        self.assertEqual(plan.record.id, "junior_kami_07")
        self.assertEqual(plan.allocation.strategy, "in-bank")
        self.assertEqual(plan.allocation.region_name, "free_text_bank_99_tail")
        self.assertEqual(plan.allocation.new_offset, 0x0CFAAE)
        self.assertEqual(plan.allocation.new_length, 98)

    def test_final_rom_decodes_every_authored_line_at_its_selected_pointer(self):
        slots = decode_text_slots(self.built)
        by_selector = {plan.record.selector: plan for plan in self.scene_plans}
        for selector in [0x002A, *range(0x030A, 0x0329)]:
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