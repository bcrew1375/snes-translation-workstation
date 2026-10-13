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
    decode_text_stream,
)
from dbz_kakusei_hen.translation_build import (  # noqa: E402
    TranslationRecord,
    build_translation,
    load_reviewed_free_regions,
    load_translation_manifests,
    map_unverified_candidate_gaps,
    plan_translations,
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
            PROJECT_ROOT / "translation" / "patches",
            PROJECT_ROOT / "translation" / "references.toml",
        )
        self.assertEqual(len(records), 53)
        self.assertEqual(records[0].selector, 0x07E1)
        self.assertEqual({record.original_bank for record in records}, {0x99, 0x9B, 0x9C})
        self.assertEqual(len(records[0].english), 4)
        self.assertEqual(records[0].max_line_length, 28)
        self.assertIn("Long ago", records[0].english[0])

    def test_duplicate_patch_ids_across_files_are_rejected(self):
        patch = f'''schema_version = 1

[[record]]
id = "duplicate"
original_address = "99:8100"
original_offset = 0xC0100
original_length = 2
source_sha256 = "{'0' * 64}"
english = ["It"]
max_line_length = 21
status = "implemented"
notes = ""
'''
        reference = '''schema_version = 1

[[record]]
id = "duplicate"
reference_type = "command_08_selector"
reference_address = "99:8000"
reference_offset = 0xC0000
message_index = 0
pointer_format = "16-bit same-bank LoROM pointer"
target_address = "99:8100"
target_offset = 0xC0100
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            patches = root / "patches"
            patches.mkdir()
            (patches / "01_first.toml").write_text(patch, encoding="utf-8")
            (patches / "02_second.toml").write_text(patch, encoding="utf-8")
            references = root / "references.toml"
            references.write_text(reference, encoding="utf-8")

            with self.assertRaisesRegex(WorkstationError, "duplicate patch id 'duplicate'"):
                load_translation_manifests(patches, references)

    def test_manifest_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            patches = root / "patches.toml"
            references = root / "references.toml"
            patches.write_text(f'''schema_version = 1

[[record]]
id = "x"
original_address = "99:8100"
original_offset = 0xC0100
original_length = 2
source_sha256 = "{'0' * 64}"
english = ["It"]
max_line_length = 21
status = "implemented"
notes = ""
''', encoding="utf-8")
            references.write_text('''schema_version = 1

[[record]]
id = "y"
reference_type = "command_08_selector"
reference_address = "99:8000"
reference_offset = 0xC0000
message_index = 0
pointer_format = "16-bit same-bank LoROM pointer"
target_address = "99:8100"
target_offset = 0xC0100
''', encoding="utf-8")
            with self.assertRaisesRegex(WorkstationError, "has no reference"):
                load_translation_manifests(patches, references)


@unittest.skipUnless((PROJECT_ROOT / "rom" / "original.sfc").is_file(), "original ROM absent")
class OriginalRomExpansionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (PROJECT_ROOT / "rom" / "original.sfc").read_bytes()
        cls.records = load_translation_manifests(
            PROJECT_ROOT / "translation" / "patches",
            PROJECT_ROOT / "translation" / "references.toml",
        )

    def test_existing_records_plan_without_relocation_and_match_opening_bytes(self):
        plans = plan_translations(self.original, self.records[:len(OPENING_TEXTS)], [])
        self.assertEqual(len(plans), len(OPENING_TEXTS))
        self.assertTrue(all(plan.allocation.strategy == "in-place" for plan in plans))
        for plan, opening in zip(plans, OPENING_TEXTS):
            with self.subTest(id=plan.record.id):
                self.assertEqual(plan.record.selector, opening.selector)
                self.assertEqual(plan.encoded.data, encode_opening_stream(opening))

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
                self.assertLessEqual(len(record.english), presentation.height_cells)
                self.assertTrue(all(len(line) <= limit for line in record.english))
                validate_visible_line_width(record, presentation)

    def test_default_presentations_omit_unconfirmed_line_limit(self):
        from dbz_kakusei_hen.scenario import decode_text_slots

        slots = decode_text_slots(self.original)
        defaults = [record for record in self.records if slots[record.selector].presentation.kind == "default"]
        self.assertEqual(
            [record.id for record in defaults],
            ["opening_recap_01", "opening_recap_04", "opening_recap_15", "opening_recap_19"],
        )
        self.assertTrue(all(record.max_line_length is None for record in defaults))

    def test_tournament_relocation_count_and_span_are_stable(self):
        regions = load_reviewed_free_regions(PROJECT_ROOT / "translation" / "ranges.toml")
        tournament = [
            record for record in self.records
            if record.id.startswith("tournament_opening_")
        ]
        plans = plan_translations(self.original, tournament, regions)
        relocated = [plan for plan in plans if plan.needs_pointer_update]
        self.assertEqual(len(relocated), 11)
        self.assertEqual(relocated[0].allocation.new_offset, 0x0CF8EE)
        self.assertEqual(relocated[-1].allocation.end_offset - 1, 0x0CFAA1)

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

    def test_generic_builder_matches_the_established_opening_build(self):
        expected = bytearray(apply_opening_translation(self.original))
        from snesworkbench.patching import write_snes_checksum

        write_snes_checksum(expected, 0x7FDE)
        result = build_translation(self.original, self.records[:len(OPENING_TEXTS)], [])
        self.assertEqual(result.data, bytes(expected))
        self.assertEqual(result.metadata["translation_count"], len(OPENING_TEXTS))

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