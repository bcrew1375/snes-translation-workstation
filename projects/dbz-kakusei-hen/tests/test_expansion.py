"""Focused safety tests for text expansion and relocation infrastructure."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "toolkit"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from snesworkbench.errors import WorkstationError  # noqa: E402
from snesworkbench.rom import cpu_to_offset  # noqa: E402

from dbz_kakusei_hen.allocator import (  # noqa: E402
    FreeSpaceRegion,
    StreamAllocator,
    allocate_streams,
)
from dbz_kakusei_hen.glyphs import encode_latin_cell, encode_text_layout  # noqa: E402
from dbz_kakusei_hen.opening_translation import (  # noqa: E402
    OPENING_TEXTS,
    apply_opening_translation,
    encode_opening_stream,
)
from dbz_kakusei_hen.pointer_update import write_pointer  # noqa: E402
from dbz_kakusei_hen.scenario import (  # noqa: E402
    TextPresentation,
    TextSelectorSlot,
    TextStream,
    decode_text_stream,
)
from dbz_kakusei_hen.translation_build import (  # noqa: E402
    TranslationRecord,
    build_translation,
    load_reviewed_free_regions,
    load_translation_manifests,
    map_unverified_candidate_gaps,
    plan_translations,
    source_dialogue_box_count,
    validate_dialogue_box_count,
    validate_visible_line_width,
    validate_reviewed_free_regions,
    visible_line_character_limit,
)


class GlyphEncodingTest(unittest.TestCase):
    def test_unsupported_character_is_not_silently_replaced(self):
        with self.assertRaisesRegex(WorkstationError, r"unsupported Latin character '@'"):
            encode_text_layout("@ ", max_line_width=1)

    def test_width_and_height_are_enforced(self):
        with self.assertRaisesRegex(WorkstationError, "presentation permits 1"):
            encode_text_layout("ItIt", max_line_width=1)
        with self.assertRaisesRegex(WorkstationError, "has 2 lines"):
            encode_text_layout("It\nIt", max_line_width=1, max_lines=1)

    def test_odd_line_is_padded_to_one_complete_cell(self):
        encoded = encode_text_layout("I", max_line_width=1)
        self.assertEqual(encoded.words, (encode_latin_cell("I"), 0))
        self.assertEqual(encoded.line_cells, (1,))

    def test_empty_lines_encode_as_page_padding(self):
        encoded = encode_text_layout("One\n\nTwo", max_line_width=16)
        self.assertEqual(encoded.line_cells, (2, 0, 2))
        self.assertEqual(encoded.words.count(0x000A), 2)

    def test_next_box_uses_line_breaks_without_blank_glyph_cells(self):
        encoded = encode_text_layout("One\n\n\n\nTwo", max_line_width=16)
        self.assertEqual(encoded.line_cells, (2, 0, 0, 0, 2))
        self.assertEqual(
            encoded.words,
            (
                encode_latin_cell("O", "n"),
                encode_latin_cell("e"),
                0x000A,
                0x000A,
                0x000A,
                0x000A,
                encode_latin_cell("T", "w"),
                encode_latin_cell("o"),
                0x0000,
            ),
        )


class DialoguePaginationTest(unittest.TestCase):
    def test_source_box_count_uses_four_lines_per_box(self):
        stream = decode_text_stream(
            bytes.fromhex("00010a000a000a000a000101000000"),
            bank=0x80,
            address=0x8000,
        )
        self.assertEqual(stream.line_lengths, (1, 0, 0, 0, 1))
        self.assertEqual(source_dialogue_box_count(stream), 2)


    def test_english_must_preserve_source_box_count(self):
        stream = decode_text_stream(
            bytes.fromhex("00010a000a000a000a000101000000"),
            bank=0x80,
            address=0x8000,
        )
        record = TranslationRecord(
            id="pagination_test",
            selector=0x0200,
            original_bank=0x80,
            original_address=0x8000,
            original_offset=0,
            original_length=len(stream.data),
            source_sha256=hashlib.sha256(stream.data).hexdigest(),
            english=("Only one box",),
            max_line_length=None,
            alias_selectors=(),
            status="implemented",
            notes="synthetic pagination test",
            reference_offset=0,
            pointer_format="synthetic",
        )
        with self.assertRaisesRegex(WorkstationError, "source uses 2"):
            validate_dialogue_box_count(record, stream)

    def test_nonblank_source_box_cannot_become_an_invisible_prompt(self):
        stream = decode_text_stream(
            bytes.fromhex("00010a000a000a000a000101000000"),
            bank=0x80,
            address=0x8000,
        )
        record = TranslationRecord(
            id="blank_box_test",
            selector=0x0200,
            original_bank=0x80,
            original_address=0x8000,
            original_offset=0,
            original_length=len(stream.data),
            source_sha256=hashlib.sha256(stream.data).hexdigest(),
            english=("Visible", "", "", "", "", "", "", ""),
            max_line_length=None,
            alias_selectors=(),
            status="implemented",
            notes="synthetic invisible-prompt regression test",
            reference_offset=0,
            pointer_format="synthetic",
        )
        with self.assertRaisesRegex(WorkstationError, "dialogue box 2 is blank"):
            validate_dialogue_box_count(record, stream)

    def test_opt_in_source_line_layout_must_preserve_visible_and_blank_lines(self):
        stream = TextStream(
            bank=0x80,
            address=0x8000,
            offset=0,
            end_offset=2,
            data=b"\x00\x00",
            words=(),
            line_lengths=(1, 0, 1, 0, 1),
        )
        record = TranslationRecord(
            id="exact_layout_test",
            selector=0x0200,
            original_bank=0x80,
            original_address=0x8000,
            original_offset=0,
            original_length=len(stream.data),
            source_sha256=hashlib.sha256(stream.data).hexdigest(),
            english=("One", "Moved", "", "", "Two"),
            max_line_length=None,
            alias_selectors=(),
            status="implemented",
            notes="synthetic exact-layout regression test",
            reference_offset=0,
            pointer_format="synthetic",
            preserve_source_line_layout=True,
        )
        with self.assertRaisesRegex(WorkstationError, "must preserve source line layout"):
            validate_dialogue_box_count(record, stream)

    def test_compact_encoding_does_not_preserve_unused_source_cells(self):
        encoded = encode_text_layout("Short\nNext", max_line_width=16)
        self.assertEqual(encoded.line_cells, (3, 2))
        self.assertEqual(len(encoded.data), 14)


class AllocatorTest(unittest.TestCase):
    BANK = 0x99
    BANK_START = cpu_to_offset(BANK, 0x8000, "lorom")

    def test_relocation_requires_the_full_stream_length(self):
        allocator = StreamAllocator(
            [FreeSpaceRegion(self.BANK, self.BANK_START + 0x100, self.BANK_START + 0x10A)]
        )
        with self.assertRaisesRegex(WorkstationError, "full 12-byte stream"):
            allocator.allocate(
                selector=1,
                original_offset=self.BANK_START,
                original_length=8,
                new_length=12,
                bank=self.BANK,
            )

    def test_multiple_allocations_consume_regions_without_overlap(self):
        allocations = allocate_streams(
            [
                {
                    "selector": 1,
                    "original_offset": self.BANK_START,
                    "original_length": 2,
                    "new_length": 8,
                    "original_bank": self.BANK,
                },
                {
                    "selector": 2,
                    "original_offset": self.BANK_START + 2,
                    "original_length": 2,
                    "new_length": 8,
                    "original_bank": self.BANK,
                },
            ],
            [FreeSpaceRegion(self.BANK, self.BANK_START + 0x101, self.BANK_START + 0x120)],
        )
        self.assertEqual([item.new_offset for item in allocations], [self.BANK_START + 0x102, self.BANK_START + 0x10A])
        self.assertLessEqual(allocations[0].end_offset, allocations[1].new_offset)

    def test_lower_priority_region_is_used_only_as_a_fallback(self):
        preferred = FreeSpaceRegion(
            self.BANK,
            self.BANK_START + 0x200,
            self.BANK_START + 0x210,
            name="preferred",
        )
        fallback = FreeSpaceRegion(
            self.BANK,
            self.BANK_START + 0x100,
            self.BANK_START + 0x120,
            name="fallback",
            priority=1,
        )
        allocator = StreamAllocator([fallback, preferred])

        first = allocator.allocate(
            selector=1,
            original_offset=self.BANK_START,
            original_length=2,
            new_length=16,
            bank=self.BANK,
        )
        second = allocator.allocate(
            selector=2,
            original_offset=self.BANK_START + 2,
            original_length=2,
            new_length=16,
            bank=self.BANK,
        )

        self.assertEqual((first.new_offset, first.region_name), (preferred.rom_start, "preferred"))
        self.assertEqual((second.new_offset, second.region_name), (fallback.rom_start, "fallback"))

    def test_cross_bank_space_is_not_used(self):
        other = 0x9A
        allocator = StreamAllocator(
            [FreeSpaceRegion(other, cpu_to_offset(other, 0x9000, "lorom"), cpu_to_offset(other, 0x9020, "lorom"))]
        )
        with self.assertRaisesRegex(WorkstationError, r"bank \$99"):
            allocator.allocate(
                selector=1,
                original_offset=self.BANK_START,
                original_length=2,
                new_length=8,
                bank=self.BANK,
            )

    def test_region_crossing_a_bank_boundary_is_rejected(self):
        with self.assertRaisesRegex(WorkstationError, "not wholly inside"):
            FreeSpaceRegion(self.BANK, self.BANK_START + 0x7FF0, self.BANK_START + 0x8010)


class PointerUpdateTest(unittest.TestCase):
    def test_explicit_authoritative_slot_is_updated_and_validated(self):
        rom = bytearray(0x10000)
        slot = TextSelectorSlot(
            selector=0x1234,
            pointer_bank=0x01,
            pointer_address=0x8000,
            pointer_offset=0,
            target_address=0x8100,
            target_offset=0x0100,
            presentation=TextPresentation("default", None, None, None, 16, 8),
        )
        rom[:2] = (0x8100).to_bytes(2, "little")
        entry = write_pointer(
            rom, 0x1234, 0x8200, slots=(slot,), expected_target_address=0x8100
        )
        self.assertEqual(entry.target_address, 0x8200)
        self.assertEqual(rom[:2], b"\x00\x82")
        with self.assertRaisesRegex(WorkstationError, "changed from expected"):
            write_pointer(
                rom, 0x1234, 0x8300, slots=(slot,), expected_target_address=0x8000
            )


class ManifestTest(unittest.TestCase):
    @staticmethod
    def translation_record(
        english: str, max_line_length: int | None
    ) -> TranslationRecord:
        return TranslationRecord(
            id="width_test",
            selector=0x0200,
            original_bank=0x99,
            original_address=0x8000,
            original_offset=0,
            original_length=2,
            source_sha256="0" * 64,
            english=tuple(english.split("\n")),
            max_line_length=max_line_length,
            alias_selectors=(),
            status="implemented",
            notes="",
            reference_offset=0,
            pointer_format="16-bit same-bank LoROM pointer",
        )

    def test_confirmed_visible_line_limits(self):
        wide = TextPresentation("wide_marker", b"\xFF\xFF", 0x8000, 0, 21, 8)
        portrait = TextPresentation("context_pair", b"\x01\x00", 0x8002, 2, 16, 8)
        default = TextPresentation("default", None, None, None, 16, 8)
        self.assertEqual(visible_line_character_limit(wide), 28)
        self.assertEqual(visible_line_character_limit(portrait), 21)
        self.assertIsNone(visible_line_character_limit(default))
        validate_visible_line_width(self.translation_record("W" * 28, 28), wide)
        validate_visible_line_width(self.translation_record("P" * 21, 21), portrait)
        validate_visible_line_width(self.translation_record("default", None), default)
        with self.assertRaisesRegex(
            WorkstationError,
            r"width_test selector \$0200 line 1 has 29 characters; wide_marker permits 28",
        ):
            validate_visible_line_width(self.translation_record("W" * 29, 28), wide)
        with self.assertRaisesRegex(
            WorkstationError,
            r"width_test selector \$0200 line 2 has 22 characters; context_pair permits 21",
        ):
            validate_visible_line_width(
                self.translation_record("ok\n" + "P" * 22, 21), portrait
            )
        with self.assertRaisesRegex(WorkstationError, "must declare max_line_length = 28"):
            validate_visible_line_width(self.translation_record("wide", None), wide)
        with self.assertRaisesRegex(WorkstationError, "wide_marker requires 28"):
            validate_visible_line_width(self.translation_record("wide", 21), wide)
        with self.assertRaisesRegex(WorkstationError, "must omit max_line_length"):
            validate_visible_line_width(self.translation_record("default", 28), default)

    def test_manifests_join_by_id_and_preserve_real_banks(self):
        records = load_translation_manifests(
            PROJECT_ROOT / "translation" / "patches"
        )
        self.assertEqual(len(records), 369)
        self.assertEqual(records[0].selector, 0x07E1)
        self.assertEqual({record.original_bank for record in records}, {0x98, 0x99, 0x9B, 0x9C})
        self.assertEqual(len(records[0].english), 4)
        self.assertEqual(records[0].max_line_length, 28)
        self.assertIn("Long ago", records[0].english[0])

    def test_reused_announcer_begin_lines_are_claimed(self):
        records = load_translation_manifests(
            PROJECT_ROOT / "translation" / "patches"
        )
        reused = {
            record.selector: record
            for record in records
            if record.id in {"semifinal_match_begin_reuse", "first_match_begin_reuse"}
        }
        self.assertEqual(set(reused), {0x0369, 0x0950})
        self.assertEqual(reused[0x0369].original_offset, 0x0CDD38)
        self.assertEqual(reused[0x0950].original_offset, 0x0E6FFE)
        self.assertEqual(
            reused[0x0369].english,
            ("All right!!", "Semifinal match!", "", "", "Please begin!!"),
        )
        self.assertEqual(reused[0x0950].english, ("First match!", "Please begin!!"))

    def test_recognized_route_to_first_hud_is_complete_and_deterministic(self):
        original_path = PROJECT_ROOT / "rom" / "original.sfc"
        if not original_path.is_file():
            self.skipTest("original ROM absent")
        original = original_path.read_bytes()
        records = load_translation_manifests(
            PROJECT_ROOT / "translation" / "patches"
        )
        checkpoint = [
            record
            for record in records
            if record.id.startswith(("krillin_match_end_", "yamcha_shen_", "semifinals_"))
        ]
        self.assertEqual(len(checkpoint), 51)
        self.assertEqual(
            [record.selector for record in checkpoint],
            list(range(0x02D6, 0x0309)),
        )
        self.assertEqual(
            checkpoint[15].alias_selectors,
            (0x0309,),
        )

        regions = load_reviewed_free_regions(PROJECT_ROOT / "translation" / "ranges")
        plans = plan_translations(original, records, regions)
        checkpoint_plans = {
            plan.record.id: plan
            for plan in plans
            if plan.record in checkpoint
        }
        relocated = {
            identifier: (plan.allocation.new_offset, plan.allocation.new_length)
            for identifier, plan in checkpoint_plans.items()
            if plan.allocation.strategy == "in-bank"
        }
        self.assertEqual(
            relocated,
            {
                "krillin_match_end_08": (0x0CFF24, 50),
                "krillin_match_end_10": (0x0CFD98, 70),
                "yamcha_shen_00": (0x0CFC20, 80),
                "yamcha_shen_01": (0x0CFA42, 108),
                "yamcha_shen_04": (0x0CFF56, 48),
                "yamcha_shen_08": (0x0CFDDE, 70),
                "yamcha_shen_15": (0x0C8F14, 38),
                "yamcha_shen_25": (0x0C8D2A, 14),
            },
        )
        self.assertEqual(checkpoint_plans["yamcha_shen_02"].allocation.strategy, "in-place")

        first = build_translation(original, records, regions)
        second = build_translation(original, records, regions)
        self.assertEqual(first.data, second.data)
        from dbz_kakusei_hen.scenario import decode_text_slots

        slots = decode_text_slots(first.data)
        self.assertEqual(slots[0x02E5].target_offset, 0x0CBBA4)
        self.assertEqual(slots[0x0309].target_offset, 0x0CBBA4)
        self.assertLessEqual(checkpoint_plans["yamcha_shen_31"].allocation.end_offset, 0x0D0000)

    def test_goku_tien_battle_opening_is_complete_and_in_place(self):
        original_path = PROJECT_ROOT / "rom" / "original.sfc"
        if not original_path.is_file():
            self.skipTest("original ROM absent")
        original = original_path.read_bytes()
        records = load_translation_manifests(
            PROJECT_ROOT / "translation" / "patches"
        )
        checkpoint = [record for record in records if record.id.startswith("goku_tien_")]
        self.assertEqual(len(checkpoint), 10)
        self.assertEqual(
            [record.selector for record in checkpoint],
            list(range(0x0332, 0x033B)) + [0x0F24],
        )

        regions = load_reviewed_free_regions(PROJECT_ROOT / "translation" / "ranges")
        plans = plan_translations(original, records, regions)
        checkpoint_plans = [plan for plan in plans if plan.record in checkpoint]
        self.assertEqual(len(checkpoint_plans), 10)
        self.assertTrue(
            all(plan.allocation.strategy == "in-place" for plan in checkpoint_plans)
        )
        for plan in checkpoint_plans:
            self.assertEqual(plan.allocation.new_offset, plan.record.original_offset)
            self.assertLessEqual(plan.allocation.new_length, plan.record.original_length)

    def test_duplicate_patch_ids_across_files_are_rejected(self):
        patch = f'''schema_version = 1

[[record]]
id = "duplicate"
selector = 0
reference_address = "98:8000"
reference_offset = 0xC0000
pointer_format = "16-bit same-bank LoROM pointer"
original_address = "98:8100"
original_offset = 0xC0100
original_length = 2
source_sha256 = "{'0' * 64}"
english = ["It"]
max_line_length = 21
status = "implemented"
notes = ""
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            patches = root / "patches"
            patches.mkdir()
            (patches / "01_first.toml").write_text(patch, encoding="utf-8")
            (patches / "02_second.toml").write_text(patch, encoding="utf-8")
            with self.assertRaisesRegex(WorkstationError, "duplicate patch id 'duplicate'"):
                load_translation_manifests(patches)

    def test_manifest_loader_allows_padding_but_rejects_all_blank_lines(self):
        patch = f'''schema_version = 1

[[record]]
id = "padding"
selector = 0
reference_address = "98:8000"
reference_offset = 0xC0000
pointer_format = "16-bit same-bank LoROM pointer"
original_address = "98:8100"
original_offset = 0xC0100
original_length = 2
source_sha256 = "{'0' * 64}"
english = ["", "It", ""]
max_line_length = 21
status = "implemented"
notes = ""
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            patches = root / "patches.toml"
            patches.write_text(patch, encoding="utf-8")

            records = load_translation_manifests(patches)
            self.assertEqual(records[0].english, ("", "It", ""))

            patches.write_text(
                patch.replace('english = ["", "It", ""]', 'english = ["", "   "]'),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(WorkstationError, "no nonblank English lines"):
                load_translation_manifests(patches)

    def test_reference_address_offset_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            patches = root / "patches.toml"
            patches.write_text(f'''schema_version = 1

[[record]]
id = "x"
selector = 0
reference_address = "98:8000"
reference_offset = 0xC0002
pointer_format = "16-bit same-bank LoROM pointer"
original_address = "98:8100"
original_offset = 0xC0100
original_length = 2
source_sha256 = "{'0' * 64}"
english = ["It"]
max_line_length = 21
status = "implemented"
notes = ""
''', encoding="utf-8")
            with self.assertRaisesRegex(WorkstationError, "reference address and offset disagree"):
                load_translation_manifests(patches)


@unittest.skipUnless((PROJECT_ROOT / "rom" / "original.sfc").is_file(), "original ROM absent")
class OriginalRomExpansionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (PROJECT_ROOT / "rom" / "original.sfc").read_bytes()
        cls.records = load_translation_manifests(
            PROJECT_ROOT / "translation" / "patches"
        )

    def test_existing_records_plan_in_place_with_compact_opening_bytes(self):
        plans = plan_translations(self.original, self.records[:len(OPENING_TEXTS)], [])
        self.assertEqual(len(plans), len(OPENING_TEXTS))
        self.assertTrue(all(plan.allocation.strategy == "in-place" for plan in plans))
        for plan, opening in zip(plans, OPENING_TEXTS):
            with self.subTest(id=plan.record.id):
                self.assertEqual(plan.record.selector, opening.selector)
                self.assertLessEqual(len(plan.encoded.data), len(encode_opening_stream(opening)))
                self.assertEqual(plan.encoded.line_cells, tuple((len(line) + 1) // 2 for line in opening.lines))

    def test_tournament_lines_fit_confirmed_visible_presentations(self):
        from dbz_kakusei_hen.scenario import decode_text_slots

        slots = decode_text_slots(self.original)
        tournament = [
            record for record in self.records
            if record.id.startswith("tournament_opening_")
        ]
        self.assertEqual(len(tournament), 27)
        for record in tournament:
            presentation = slots[record.selector].presentation
            limit = visible_line_character_limit(presentation)
            with self.subTest(id=record.id, kind=presentation.kind):
                self.assertIsNotNone(limit)
                self.assertEqual(record.max_line_length, limit)
                stream = decode_text_stream(
                    self.original,
                    bank=slots[record.selector].pointer_bank,
                    address=slots[record.selector].target_address,
                    selectors=(record.selector,),
                )
                self.assertEqual(
                    (len(record.english) + 3) // 4,
                    source_dialogue_box_count(stream),
                )
                self.assertTrue(all(len(line) <= limit for line in record.english))
                validate_visible_line_width(record, presentation)

    def test_every_visible_source_box_has_visible_english(self):
        from dbz_kakusei_hen.scenario import decode_text_slots

        slots = decode_text_slots(self.original)
        for record in self.records:
            slot = slots[record.selector]
            stream = decode_text_stream(
                self.original,
                bank=slot.pointer_bank,
                address=slot.target_address,
                selectors=(record.selector,),
            )
            with self.subTest(id=record.id, selector=f"${record.selector:04X}"):
                validate_dialogue_box_count(record, stream)

        bride = next(record for record in self.records if record.id == "chichi_x_10")
        self.assertEqual(
            tuple(bride.english[index:index + 4] for index in range(0, len(bride.english), 4)),
            (
                ("Ah!! I remember now!!", "", "", ""),
                ("I sure did say I'd", "", "", ""),
                ("come get a bride!!",),
            ),
        )

    def test_default_presentations_omit_unconfirmed_line_limit(self):
        from dbz_kakusei_hen.scenario import decode_text_slots

        slots = decode_text_slots(self.original)
        defaults = [record for record in self.records if slots[record.selector].presentation.kind == "default"]
        self.assertEqual(
            [record.id for record in defaults],
            [
                "opening_recap_01", "opening_recap_04", "opening_recap_15",
                "opening_recap_19", "post_quiz_krillin_exclamation",
                "yamcha_startled_laugh", "goku_affirmative_reply",
                "goku_chichi_unknown_name_reaction",
                "goku_chichi_unknown_agreement",
                "junior_kami_goku_reaction",
                "junior_win_cont_0011", "junior_win_cont_0002",
            ],
        )
        self.assertTrue(all(record.max_line_length is None for record in defaults))

    def test_tournament_relocation_count_and_span_are_stable(self):
        regions = load_reviewed_free_regions(PROJECT_ROOT / "translation" / "ranges")
        tournament = [
            record for record in self.records
            if record.id.startswith("tournament_opening_")
        ]
        plans = plan_translations(self.original, tournament, regions)
        relocated = [plan for plan in plans if plan.needs_pointer_update]
        self.assertEqual(len(relocated), 10)
        self.assertEqual(
            min(plan.allocation.new_offset for plan in relocated),
            0x0C8C38,
        )
        self.assertEqual(
            max(plan.allocation.end_offset for plan in relocated) - 1,
            0x0CFA3D,
        )

    def test_quiz_responses_relocate_deterministically(self):
        responses = [
            record for record in self.records
            if record.id.startswith("tournament_quiz_") and "response" in record.id
        ]
        self.assertEqual(
            [(record.id, record.selector) for record in responses],
            [
                ("tournament_quiz_response_b", 0x021C),
                ("tournament_quiz_response_xy", 0x021B),
                ("tournament_quiz_02_response", 0x0222),
            ],
        )
        regions = load_reviewed_free_regions(PROJECT_ROOT / "translation" / "ranges")
        tournament_and_responses = [
            record for record in self.records
            if record.id.startswith("tournament_opening_")
            or (record.id.startswith("tournament_quiz_") and "response" in record.id)
        ]
        plans = [
            plan for plan in plan_translations(self.original, tournament_and_responses, regions)
            if plan.record.id.startswith("tournament_quiz_") and "response" in plan.record.id
        ]
        self.assertEqual(
            [(plan.record.id, plan.allocation.strategy, plan.allocation.new_offset) for plan in plans],
            [
                ("tournament_quiz_response_b", "in-bank", 0x0CF9E0),
                ("tournament_quiz_response_xy", "in-bank", 0x0CFA5C),
                ("tournament_quiz_02_response", "in-place", 0x0C917E),
            ],
        )
        result = build_translation(self.original, tournament_and_responses, regions)
        for plan in plans:
            with self.subTest(id=plan.record.id):
                expected_pointer = 0x8000 + (plan.allocation.new_offset & 0x7FFF)
                self.assertEqual(
                    int.from_bytes(
                        result.data[plan.record.reference_offset:plan.record.reference_offset + 2],
                        "little",
                    ),
                    expected_pointer,
                )
                self.assertEqual(
                    result.data[plan.allocation.new_offset:plan.allocation.end_offset],
                    plan.encoded.data,
                )

    def test_second_quiz_leadins_are_complete_and_allocate_deterministically(self):
        leadins = [
            record for record in self.records
            if record.id.startswith("tournament_quiz_02_leadin_")
        ]
        self.assertEqual(
            [(record.id, record.selector) for record in leadins],
            [
                ("tournament_quiz_02_leadin_01", 0x021D),
                ("tournament_quiz_02_leadin_02", 0x021E),
                ("tournament_quiz_02_leadin_03", 0x021F),
                ("tournament_quiz_02_leadin_04", 0x0220),
                ("tournament_quiz_02_leadin_05", 0x0221),
            ],
        )
        regions = load_reviewed_free_regions(PROJECT_ROOT / "translation" / "ranges")
        checkpoint = [
            record for record in self.records
            if record.id.startswith("tournament_opening_")
            or record.id.startswith("tournament_quiz_")
        ]
        plans = {
            plan.record.id: plan
            for plan in plan_translations(self.original, checkpoint, regions)
            if plan.record.id.startswith("tournament_quiz_02_leadin_")
        }
        self.assertEqual(
            [
                (record.id, plans[record.id].allocation.strategy)
                for record in leadins
            ],
            [
                ("tournament_quiz_02_leadin_01", "in-place"),
                ("tournament_quiz_02_leadin_02", "in-place"),
                ("tournament_quiz_02_leadin_03", "in-bank"),
                ("tournament_quiz_02_leadin_04", "in-place"),
                ("tournament_quiz_02_leadin_05", "in-place"),
            ],
        )
        self.assertEqual(plans["tournament_quiz_02_leadin_03"].allocation.new_offset, 0x0CF9E0)

    def test_pre_chichi_route_is_complete_and_allocates_deterministically(self):
        checkpoint = [
            record for record in self.records
            if record.id.startswith(("post_quiz_", "pre_chichi_"))
            or record.id in {f"preliminaries_{index:02d}" for index in range(8)}
        ]
        self.assertEqual(
            [(record.id, record.selector) for record in checkpoint],
            [
                ("post_quiz_00", 0x0223),
                ("post_quiz_krillin_exclamation", 0x001B),
                ("post_quiz_01", 0x0225),
                ("post_quiz_02", 0x0226),
                ("post_quiz_03", 0x0227),
                ("post_quiz_04", 0x0228),
                ("post_quiz_05", 0x0229),
                ("preliminaries_00", 0x022A),
                ("preliminaries_01", 0x022B),
                ("preliminaries_02", 0x022C),
                ("preliminaries_03", 0x022D),
                ("preliminaries_04", 0x022E),
                ("preliminaries_05", 0x022F),
                ("preliminaries_06", 0x0230),
                ("preliminaries_07", 0x0231),
                ("pre_chichi_00", 0x0232),
                ("pre_chichi_01", 0x0233),
                ("pre_chichi_02", 0x0234),
                ("pre_chichi_03", 0x0235),
                ("pre_chichi_04", 0x0236),
                ("pre_chichi_05", 0x0237),
                ("pre_chichi_06", 0x0238),
                ("pre_chichi_07", 0x0239),
                ("pre_chichi_08", 0x023A),
                ("pre_chichi_09", 0x023B),
                ("pre_chichi_10", 0x023C),
                ("pre_chichi_11", 0x023D),
            ],
        )
        regions = load_reviewed_free_regions(PROJECT_ROOT / "translation" / "ranges")
        plans = {
            plan.record.id: plan
            for plan in plan_translations(self.original, self.records, regions)
            if plan.record.id in {record.id for record in checkpoint}
        }
        self.assertEqual(
            [
                (record.id, plans[record.id].allocation.strategy, plans[record.id].allocation.new_offset)
                for record in checkpoint
            ],
            [
                ("post_quiz_00", "in-place", 0x0C919C),
                ("post_quiz_krillin_exclamation", "in-place", 0x0C88D2),
                ("post_quiz_01", "in-bank", 0x0CFCBE),
                ("post_quiz_02", "in-bank", 0x0C998A),
                ("post_quiz_03", "in-place", 0x0C9238),
                ("post_quiz_04", "in-place", 0x0C9248),
                ("post_quiz_05", "in-place", 0x0C9294),
                ("preliminaries_00", "in-bank", 0x0CFFB4),
                ("preliminaries_01", "in-place", 0x0C92DA),
                ("preliminaries_02", "in-bank", 0x0CB5A0),
                ("preliminaries_03", "in-place", 0x0C931E),
                ("preliminaries_04", "in-place", 0x0C93B0),
                ("preliminaries_05", "in-place", 0x0C93BE),
                ("preliminaries_06", "in-bank", 0x0C9526),
                ("preliminaries_07", "in-place", 0x0C93EC),
                ("pre_chichi_00", "in-place", 0x0C93FE),
                ("pre_chichi_01", "in-place", 0x0C940C),
                ("pre_chichi_02", "in-bank", 0x0CB60C),
                ("pre_chichi_03", "in-place", 0x0C943E),
                ("pre_chichi_04", "in-place", 0x0C946A),
                ("pre_chichi_05", "in-bank", 0x0C975E),
                ("pre_chichi_06", "in-place", 0x0C94D0),
                ("pre_chichi_07", "in-place", 0x0C94E2),
                ("pre_chichi_08", "in-bank", 0x0CB87A),
                ("pre_chichi_09", "in-place", 0x0C9562),
                ("pre_chichi_10", "in-place", 0x0C957E),
                ("pre_chichi_11", "in-place", 0x0C95A8),
            ],
        )
        self.assertNotIn(0x0224, {record.selector for record in checkpoint})
        self.assertEqual(
            self.original[0x0C8448:0x0C844A],
            self.original[0x0C844A:0x0C844C],
        )

    def test_chichi_branches_and_next_quiz_allocate_deterministically(self):
        checkpoint = [
            record for record in self.records
            if record.id.startswith(("chichi_y_", "chichi_x_", "preliminaries_quiz_"))
        ]
        self.assertEqual(
            [(record.id, record.selector) for record in checkpoint],
            [(f"chichi_y_{index:02d}", 0x023E + index) for index in range(6)]
            + [(f"chichi_x_{index:02d}", 0x0244 + index) for index in range(16)]
            + [(f"preliminaries_quiz_{index:02d}", 0x0260 + index) for index in range(4)]
            + [(f"preliminaries_quiz_response_{index:02d}", 0x0264 + index) for index in range(3)],
        )
        regions = load_reviewed_free_regions(PROJECT_ROOT / "translation" / "ranges")
        plans = {
            plan.record.id: plan
            for plan in plan_translations(self.original, self.records, regions)
            if plan.record.id in {record.id for record in checkpoint}
        }
        expected_relocations = {
            "chichi_y_02": 0x0C9A04,
            "chichi_x_03": 0x0C9024,
            "chichi_x_04": 0x0C8C38,
            "chichi_x_06": 0x0C96E2,
            "chichi_x_12": 0x0CB1F8,
            "chichi_x_14": 0x0CC168,
            "preliminaries_quiz_02": 0x0CFC70,
            "preliminaries_quiz_response_00": 0x0CF9D2,
            "preliminaries_quiz_response_02": 0x0CFE68,
        }
        self.assertEqual(
            {
                record.id: plans[record.id].allocation.new_offset
                for record in checkpoint
                if plans[record.id].allocation.strategy == "in-bank"
            },
            expected_relocations,
        )
        self.assertEqual(
            [record.id for record in checkpoint if plans[record.id].allocation.strategy == "in-place"],
            [record.id for record in checkpoint if record.id not in expected_relocations],
        )

    def test_first_preliminary_match_allocates_deterministically(self):
        checkpoint = [
            record for record in self.records
            if record.id.startswith("first_preliminary_match")
        ]
        self.assertEqual(
            [(record.id, record.selector) for record in checkpoint],
            [(f"first_preliminary_match_{index:02d}", 0x0267 + index) for index in range(16)]
            + [(f"first_preliminary_match_response_{index:02d}", 0x0277 + index) for index in range(5)],
        )
        regions = load_reviewed_free_regions(PROJECT_ROOT / "translation" / "ranges")
        plans = {
            plan.record.id: plan
            for plan in plan_translations(self.original, self.records, regions)
            if plan.record.id in {record.id for record in checkpoint}
        }
        expected_relocations = {
            "first_preliminary_match_00": 0x0C92AE,
            "first_preliminary_match_02": 0x0CA746,
            "first_preliminary_match_03": 0x0CB326,
            "first_preliminary_match_04": 0x0C9A3E,
            "first_preliminary_match_13": 0x0C8F96,
            "first_preliminary_match_15": 0x0CBD12,
        }
        self.assertEqual(
            {
                record.id: plans[record.id].allocation.new_offset
                for record in checkpoint
                if plans[record.id].allocation.strategy == "in-bank"
            },
            expected_relocations,
        )
        self.assertEqual(
            [record.id for record in checkpoint if plans[record.id].allocation.strategy == "in-place"],
            [record.id for record in checkpoint if record.id not in expected_relocations],
        )

    def test_second_preliminary_leadin_allocates_deterministically(self):
        checkpoint = [
            record for record in self.records
            if record.id.startswith("second_preliminary_leadin_")
        ]
        self.assertEqual(
            [(record.id, record.selector) for record in checkpoint],
            [(f"second_preliminary_leadin_{index:02d}", 0x027C + index) for index in range(5)],
        )
        regions = load_reviewed_free_regions(PROJECT_ROOT / "translation" / "ranges")
        plans = {
            plan.record.id: plan
            for plan in plan_translations(self.original, self.records, regions)
            if plan.record.id in {record.id for record in checkpoint}
        }
        self.assertEqual(
            {
                record.id: (plans[record.id].allocation.strategy, plans[record.id].allocation.new_offset)
                for record in checkpoint
            },
            {
                "second_preliminary_leadin_00": ("in-place", 0x0CA2A4),
                "second_preliminary_leadin_01": ("in-bank", 0x0C8F68),
                "second_preliminary_leadin_02": ("in-bank", 0x0CFBC8),
                "second_preliminary_leadin_03": ("in-place", 0x0CA336),
                "second_preliminary_leadin_04": ("in-place", 0x0CA3BA),
            },
        )
        self.assertEqual(
            [plans[record.id].encoded.line_cells for record in checkpoint],
            [(3, 8), (7, 8, 5), (9, 0, 0, 0, 11, 8, 9),
             (10, 9, 0, 0, 7, 8, 0, 0, 10, 5), (3, 4, 5, 8)],
        )

    def test_finals_transition_allocates_runtime_confirmed_disjoint_selectors_deterministically(self):
        checkpoint = [
            record for record in self.records
            if record.id.startswith("finals_transition")
        ]
        expected_selectors = list(range(0x0281, 0x0294)) + [0x0F25] + list(range(0x0294, 0x029A))
        self.assertEqual([record.selector for record in checkpoint], expected_selectors)
        regions = load_reviewed_free_regions(PROJECT_ROOT / "translation" / "ranges")
        plans = {
            plan.record.id: plan
            for plan in plan_translations(self.original, self.records, regions)
            if plan.record.id in {record.id for record in checkpoint}
        }
        expected_relocations = {
            "finals_transition_02": ("in-bank", 0x0C9386),
            "finals_transition_03": ("in-bank", 0x0C9914),
        }
        self.assertEqual(
            {
                record.id: (plans[record.id].allocation.strategy, plans[record.id].allocation.new_offset)
                for record in checkpoint
            },
            {
                record.id: expected_relocations.get(
                    record.id, ("in-place", record.original_offset)
                )
                for record in checkpoint
            },
        )

    def test_finals_quiz_tien_tao_and_chichi_routes_allocate_in_place(self):
        checkpoint = [
            record for record in self.records
            if record.id.startswith(("finals_quiz_result", "tien_tao", "goku_chichi"))
        ]
        expected_selectors = (
            list(range(0x029A, 0x02CC))
            + [0x001D]
            + list(range(0x02CC, 0x02D5))
            + [0x001F, 0x02D5]
            + list(range(0x0F1F, 0x0F23))
        )
        self.assertEqual([record.selector for record in checkpoint], expected_selectors)
        regions = load_reviewed_free_regions(PROJECT_ROOT / "translation" / "ranges")
        plans = {
            plan.record.id: plan
            for plan in plan_translations(self.original, self.records, regions)
            if plan.record.id in {record.id for record in checkpoint}
        }
        self.assertEqual(len(plans), 66)
        self.assertEqual(
            {
                record.id: (plans[record.id].allocation.strategy, plans[record.id].allocation.new_offset)
                for record in checkpoint
                if plans[record.id].allocation.strategy != "in-place"
            },
            {
                "tien_tao_00": ("in-bank", 0x0C9E06),
                "tien_tao_26": ("in-bank", 0x0CFE24),
                "tien_tao_34": ("in-bank", 0x0CFB10),
                "tien_tao_38": ("in-bank", 0x0CFD0A),
                "tien_tao_39": ("in-bank", 0x0CF8EE),
                "goku_chichi_recognized_02": ("in-bank", 0x0C9C42),
                "goku_chichi_unknown_name_reaction": ("in-bank", 0x0C9830),
                "goku_chichi_unknown_01": ("in-bank", 0x0CFD52),
            },
        )
        self.assertTrue(
            all(
                plans[record.id].allocation.new_offset == record.original_offset
                for record in checkpoint
                if record.id not in {
                    "tien_tao_00", "tien_tao_26", "tien_tao_34", "tien_tao_38",
                    "tien_tao_39", "goku_chichi_recognized_02",
                    "goku_chichi_unknown_name_reaction",
                    "goku_chichi_unknown_01"
                }
            )
        )
        self.assertEqual(
            plans["tien_tao_unrecognized_00"].encoded.line_cells,
            (10, 8, 0, 0, 9, 8, 0, 0, 10, 9, 10),
        )
        self.assertEqual(
            plans["tien_tao_unrecognized_01"].encoded.line_cells,
            (8, 9, 7, 6, 5, 6),
        )

        reply = next(record for record in self.records if record.id == "goku_affirmative_reply")
        self.assertEqual(reply.selector, 0x001C)
        reply_plan = next(
            plan for plan in plan_translations(self.original, self.records, regions)
            if plan.record.id == reply.id
        )
        self.assertEqual(
            (reply_plan.allocation.strategy, reply_plan.allocation.new_offset),
            ("in-place", 0x0C88DA),
        )

    def test_candidate_gaps_exclude_all_confirmed_text_structures(self):
        from dbz_kakusei_hen.scenario import (
            TEXT_PRESENTATION_ADDRESS,
            TEXT_PRESENTATION_BANK,
            TEXT_PRESENTATION_FIRST_SELECTOR,
            TEXT_SELECTOR_LAST,
            TEXT_TABLE_RANGES,
            decode_text_slots,
            decode_unique_text_streams,
        )

        gaps = map_unverified_candidate_gaps(self.original)
        slots = decode_text_slots(self.original)
        reserved = [
            (stream.offset, stream.end_offset)
            for stream in decode_unique_text_streams(self.original, slots)
        ]
        for table in TEXT_TABLE_RANGES:
            start = cpu_to_offset(table.bank, table.address, "lorom")
            reserved.append((start, start + table.count * 2))
        start = cpu_to_offset(TEXT_PRESENTATION_BANK, TEXT_PRESENTATION_ADDRESS, "lorom")
        reserved.append(
            (
                start,
                start + (TEXT_SELECTOR_LAST - TEXT_PRESENTATION_FIRST_SELECTOR + 1) * 2,
            )
        )
        for gap in gaps:
            self.assertFalse(
                any(gap.rom_start < end and start < gap.rom_end for start, end in reserved)
            )

    def test_reviewed_free_region_cannot_overlap_a_text_stream(self):
        record = self.records[0]
        region = FreeSpaceRegion(
            record.original_bank,
            record.original_offset,
            record.original_offset + record.original_length,
            name="free_text_bad_fixture",
        )
        with self.assertRaisesRegex(WorkstationError, "overlaps text stream"):
            validate_reviewed_free_regions(self.original, [region])

    def test_source_hash_mismatch_is_rejected_before_planning(self):
        record = self.records[0]
        changed = TranslationRecord(
            **{**record.__dict__, "source_sha256": hashlib.sha256(b"wrong").hexdigest()}
        )
        with self.assertRaisesRegex(WorkstationError, "source SHA-256"):
            plan_translations(self.original, [changed], [])

    def test_declared_aliases_share_one_relocated_write_and_pointer(self):
        regions = load_reviewed_free_regions(PROJECT_ROOT / "translation" / "ranges")
        primary = TranslationRecord(
            id="recognized_route_begin",
            selector=0x02E5,
            original_bank=0x99,
            original_address=0xBBA4,
            original_offset=0x0CBBA4,
            original_length=30,
            source_sha256="d06a298ab583ab45d3cf43c8f444fbbcc48aa3797813667579394a94c0f6b7ef",
            english=("Now, let us begin!!",),
            max_line_length=21,
            alias_selectors=(0x0309,),
            status="implemented",
            notes="test fixture for the byte-identical recognized-route content alias",
            reference_offset=0x0C85CA,
            pointer_format="16-bit same-bank LoROM pointer",
        )
        plans = plan_translations(self.original, [primary], regions)
        self.assertEqual(len(plans), 1)
        self.assertEqual([slot.selector for slot in plans[0].alias_slots], [0x0309])
        self.assertEqual(plans[0].allocation.strategy, "in-place")
        result = build_translation(self.original, [primary], regions)
        from dbz_kakusei_hen.scenario import decode_text_slots

        slots = decode_text_slots(result.data)
        self.assertEqual(slots[0x02E5].target_offset, slots[0x0309].target_offset)
        self.assertEqual(slots[0x02E5].target_offset, plans[0].allocation.new_offset)

    def test_compact_suffixes_are_provenanced_and_do_not_overlap_allocations(self):
        regions = load_reviewed_free_regions(PROJECT_ROOT / "translation" / "ranges")
        plans = plan_translations(self.original, self.records, regions)
        suffix_allocations = [
            plan
            for plan in plans
            if plan.allocation.region_name
            and plan.allocation.region_name.startswith("compact suffix of ")
        ]
        self.assertTrue(suffix_allocations)
        spans = sorted(
            (plan.allocation.new_offset, plan.allocation.end_offset)
            for plan in plans
        )
        self.assertTrue(all(right[0] >= left[1] for left, right in zip(spans, spans[1:])))
        for plan in suffix_allocations:
            with self.subTest(id=plan.record.id, region=plan.allocation.region_name):
                self.assertEqual(plan.allocation.bank, plan.slot.pointer_bank)
                self.assertEqual(plan.allocation.new_offset % 2, 0)

        vacated_allocations = [
            plan
            for plan in plans
            if plan.allocation.region_name
            and plan.allocation.region_name.startswith("vacated source of ")
        ]
        self.assertEqual(
            [
                (
                    plan.record.id,
                    plan.allocation.new_offset,
                    plan.allocation.region_name,
                )
                for plan in vacated_allocations
            ],
            [
                (
                    "chichi_x_03",
                    0x0C9024,
                    "vacated source of tournament_opening_25",
                ),
                (
                    "first_preliminary_match_00",
                    0x0C92AE,
                    "vacated source of preliminaries_00",
                ),
                (
                    "first_preliminary_match_04",
                    0x0C9A3E,
                    "vacated source of chichi_x_14",
                ),
                (
                    "first_preliminary_match_13",
                    0x0C8F96,
                    "vacated source of tournament_opening_22",
                ),
                (
                    "second_preliminary_leadin_01",
                    0x0C8F68,
                    "vacated source of tournament_opening_22",
                ),
                (
                    "goku_chichi_recognized_02",
                    0x0C9C42,
                    "vacated source of preliminaries_quiz_02",
                ),
                (
                    "yamcha_shen_15",
                    0x0C8F14,
                    "vacated source of tournament_opening_20",
                ),
                (
                    "junior_win_cont_03a7",
                    0x0C953C,
                    "vacated source of pre_chichi_08",
                ),
                (
                    "junior_win_cont_03aa",
                    0x0C9C64,
                    "vacated source of preliminaries_quiz_02",
                ),
            ],
        )

    def test_unclaimed_source_alias_forces_relocation(self):
        regions = load_reviewed_free_regions(PROJECT_ROOT / "translation" / "ranges")
        source = next(record for record in self.records if record.id == "post_quiz_01")
        primary = TranslationRecord(
            **{
                **source.__dict__,
                "english": ("Hi", "", "", "", "Bye"),
                "notes": "test fixture with an intentionally unclaimed shared-pointer alias",
            }
        )
        plan = plan_translations(self.original, [primary], regions)[0]
        self.assertLess(len(plan.encoded.data), primary.original_length)
        self.assertEqual(plan.allocation.strategy, "in-bank")
        self.assertNotEqual(plan.allocation.new_offset, primary.original_offset)
        self.assertFalse(
            plan.allocation.region_name
            and plan.allocation.region_name.startswith("vacated source of ")
        )

    def test_alias_must_contain_the_same_source_stream(self):
        regions = load_reviewed_free_regions(PROJECT_ROOT / "translation" / "ranges")
        primary = self.records[0]
        aliased = TranslationRecord(
            **{**primary.__dict__, "alias_selectors": (primary.selector + 1,)}
        )
        with self.assertRaisesRegex(WorkstationError, "does not contain the same source stream"):
            plan_translations(self.original, [aliased], regions)

    def test_generic_builder_compacts_the_established_opening_records_deterministically(self):
        first = build_translation(self.original, self.records[:len(OPENING_TEXTS)], [])
        second = build_translation(self.original, self.records[:len(OPENING_TEXTS)], [])
        self.assertEqual(first.data, second.data)
        self.assertNotEqual(first.data, apply_opening_translation(self.original))
        self.assertEqual(first.metadata["translation_count"], len(OPENING_TEXTS))

    def test_one_stream_relocation_round_trips_in_a_copied_rom(self):
        record = self.records[0]
        slot_offset = cpu_to_offset(record.original_bank, record.original_address, "lorom")
        destination = slot_offset + 0x1000
        region = FreeSpaceRegion(
            record.original_bank,
            destination,
            destination + record.original_length,
            name="test-only copied-ROM destination",
        )
        # Force relocation by presenting the source as aliased in a synthetic
        # record set is covered by allocator tests; here we directly validate
        # the same-bank stream and pointer mechanics against a copied ROM.
        copied = bytearray(self.original)
        data = encode_opening_stream(OPENING_TEXTS[0])
        copied[destination : destination + len(data)] = data
        new_address = 0x8000 + (destination & 0x7FFF)
        from dbz_kakusei_hen.scenario import decode_text_slots
        slots = decode_text_slots(self.original)
        write_pointer(
            copied,
            record.selector,
            new_address,
            slots=(slots[record.selector],),
            expected_target_address=record.original_address,
        )
        decoded = decode_text_stream(
            bytes(copied), bank=record.original_bank, address=new_address
        )
        self.assertEqual(decoded.data, data)
        self.assertEqual(self.original[slot_offset : slot_offset + len(data)], self.original[record.original_offset : record.original_offset + len(data)])
        self.assertEqual(region.bank, record.original_bank)


if __name__ == "__main__":
    unittest.main()