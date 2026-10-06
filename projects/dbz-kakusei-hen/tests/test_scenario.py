"""ROM-independent tests for conservative scenario-root handling."""

from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "toolkit"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from snesworkbench.graphics import encode_tiles  # noqa: E402

from dbz_kakusei_hen.scenario import (  # noqa: E402
    KNOWN_COMMAND_SCHEMAS,
    TextTableRange,
    decode_glyph,
    decode_scenario_command,
    decode_dispatch_table,
    decode_scenario_roots,
    decode_scenario_slots,
    decode_text_presentation,
    decode_text_slots,
    decode_text_stream,
    decode_unique_text_streams,
    encode_root_table,
    encode_root_slots,
    glyph_source,
    render_glyph_sheet,
    restore_candidate_ranges,
)


class ScenarioRootTest(unittest.TestCase):
    TABLE_OFFSET = 0x20

    @staticmethod
    def fixture() -> bytes:
        rom = bytearray(0x18000)
        rom[0x8000:0x8010] = bytes(range(0x10))
        rom[0x8010:0x10000] = bytes([0xA5]) * (0x7FF0)
        rom[0x10000:0x18000] = bytes([0x5A]) * 0x8000
        pointers = ((0x01, 0x8000), (0x01, 0x8010), (0x02, 0x8000))
        for index, (bank, address) in enumerate(pointers):
            start = ScenarioRootTest.TABLE_OFFSET + index * 3
            rom[start : start + 2] = address.to_bytes(2, "little")
            rom[start + 2] = bank
        return bytes(rom)

    def test_pointer_and_candidate_data_round_trip(self):
        rom = self.fixture()
        roots = decode_scenario_roots(rom, table_offset=self.TABLE_OFFSET, count=3)
        self.assertEqual([root.size for root in roots], [0x10, 0x7FF0, 0x8000])
        self.assertEqual(roots[0].cpu_address, "01:8000")
        self.assertEqual(
            encode_root_table(roots),
            rom[self.TABLE_OFFSET : self.TABLE_OFFSET + 9],
        )
        self.assertEqual(restore_candidate_ranges(rom, roots), rom)

    def test_resized_candidate_is_rejected(self):
        rom = self.fixture()
        roots = decode_scenario_roots(rom, table_offset=self.TABLE_OFFSET, count=3)
        changed = (replace(roots[0], data=roots[0].data + b"\x00"), *roots[1:])
        with self.assertRaisesRegex(ValueError, "data length changed"):
            restore_candidate_ranges(rom, changed)

    def test_unordered_roots_are_rejected(self):
        rom = bytearray(self.fixture())
        first = self.TABLE_OFFSET
        second = self.TABLE_OFFSET + 3
        rom[first : first + 2] = (0x8010).to_bytes(2, "little")
        rom[second : second + 2] = (0x8000).to_bytes(2, "little")
        with self.assertRaisesRegex(ValueError, "not ordered"):
            decode_scenario_roots(bytes(rom), table_offset=self.TABLE_OFFSET, count=3)

    def test_null_and_duplicate_slots_round_trip_without_duplicate_ranges(self):
        rom = bytearray(self.fixture())
        pointers = ((0x01, 0x8000), (0x00, 0x0000), (0x01, 0x8000), (0x01, 0x8010))
        for index, (bank, address) in enumerate(pointers):
            start = self.TABLE_OFFSET + index * 3
            rom[start : start + 2] = address.to_bytes(2, "little")
            rom[start + 2] = bank
        slots = decode_scenario_slots(bytes(rom), table_offset=self.TABLE_OFFSET, count=4)
        roots = decode_scenario_roots(bytes(rom), table_offset=self.TABLE_OFFSET, count=4)
        self.assertTrue(slots[1].is_null)
        self.assertEqual(slots[2].cpu_address, "01:8000")
        self.assertEqual([root.index for root in roots], [0, 3])
        self.assertEqual(encode_root_slots(slots), bytes(rom[self.TABLE_OFFSET : self.TABLE_OFFSET + 12]))

    def test_dispatch_zero_word_remains_explicitly_unknown(self):
        rom = bytes([0x00, 0x00, 0x3D, 0xB3])
        entries = decode_dispatch_table(rom, table_offset=0, opcode_count=2)
        self.assertIsNone(entries[0].handler)
        self.assertEqual(entries[1].cpu_address, "83:B33D")

    def test_command_08_decodes_little_endian_word(self):
        command = decode_scenario_command(bytes.fromhex("08 34 12 49"))
        self.assertEqual(command.opcode, 0x08)
        self.assertEqual(command.operand, 0x1234)
        self.assertEqual(command.raw, bytes.fromhex("08 34 12"))
        self.assertEqual(command.next_offset, 3)
        self.assertEqual(command.schema, KNOWN_COMMAND_SCHEMAS[0x08])

    def test_command_48_decodes_one_byte(self):
        command = decode_scenario_command(bytes.fromhex("48 0A 49"))
        self.assertEqual(command.operand, 0x0A)
        self.assertEqual(command.next_offset, 2)
        self.assertEqual(command.schema.handler, 0xD9BA)

    def test_command_can_be_decoded_at_an_explicit_offset(self):
        command = decode_scenario_command(bytes.fromhex("FF 48 03 49"), offset=1)
        self.assertEqual(command.offset, 1)
        self.assertEqual(command.operand, 0x03)
        self.assertEqual(command.next_offset, 3)

    def test_terminator_has_no_operand(self):
        command = decode_scenario_command(bytes.fromhex("49"))
        self.assertTrue(command.is_terminator)
        self.assertIsNone(command.operand)
        self.assertEqual(command.next_offset, 1)

    def test_truncated_known_command_is_rejected(self):
        with self.assertRaisesRegex(ValueError, r"scenario command \$08"):
            decode_scenario_command(bytes.fromhex("08 FF"))

    def test_unknown_command_keeps_remaining_bytes_opaque(self):
        command = decode_scenario_command(bytes.fromhex("12 08 34 12 49"))
        self.assertFalse(command.is_known)
        self.assertEqual(command.raw, bytes.fromhex("12 08 34 12 49"))
        self.assertIsNone(command.operand)
        self.assertIsNone(command.next_offset)


class TextTableTest(unittest.TestCase):
    TABLE = TextTableRange(0x0000, 0x0003, 0x01, 0x9000)

    @staticmethod
    def fixture() -> bytes:
        rom = bytearray(0x18000)
        table_offset = 0x9000
        pointers = (0xA000, 0x0000, 0xA000, 0xA010)
        for index, address in enumerate(pointers):
            rom[table_offset + index * 2 : table_offset + index * 2 + 2] = (
                address.to_bytes(2, "little")
            )
        rom[0xA000:0xA008] = bytes.fromhex("00 01 0A 00 01 01 00 00")
        rom[0xA010:0xA014] = bytes.fromhex("00 05 00 00")
        return bytes(rom)

    def test_slots_preserve_nulls_and_aliases(self):
        rom = self.fixture()
        slots = decode_text_slots(rom, table_ranges=(self.TABLE,))
        self.assertEqual(len(slots), 4)
        self.assertTrue(slots[1].is_null)
        self.assertEqual(slots[0].target_cpu_address, "01:A000")
        self.assertEqual(slots[2].target_cpu_address, "01:A000")
        self.assertEqual(slots[0].presentation.kind, "default")

        streams = decode_unique_text_streams(rom, slots)
        self.assertEqual(len(streams), 2)
        self.assertEqual(streams[0].selectors, (0, 2))
        self.assertEqual(streams[0].line_lengths, (1, 1))
        self.assertEqual(streams[0].glyph_codes, (0x0100, 0x0101))

    def test_table_ranges_must_be_contiguous(self):
        with self.assertRaisesRegex(ValueError, "contiguous"):
            decode_text_slots(
                self.fixture(),
                table_ranges=(TextTableRange(1, 1, 0x01, 0x9000),),
            )

    def test_invalid_non_null_pointer_is_rejected(self):
        rom = bytearray(self.fixture())
        rom[0x9000:0x9002] = (0x0120).to_bytes(2, "little")
        with self.assertRaisesRegex(ValueError, r"selector \$0000"):
            decode_text_slots(bytes(rom), table_ranges=(self.TABLE,))

    def test_stream_rejects_unknown_low_words(self):
        rom = bytearray(0x10000)
        rom[0x8000:0x8004] = bytes.fromhex("20 00 00 00")
        with self.assertRaisesRegex(ValueError, r"unknown low word \$0020"):
            decode_text_stream(bytes(rom), bank=0x01, address=0x8000)

    def test_unterminated_stream_is_rejected_at_bank_boundary(self):
        rom = bytearray(0x10000)
        rom[0xFFFC:0x10000] = bytes.fromhex("00 01 01 01")
        with self.assertRaisesRegex(ValueError, "no in-bank terminator"):
            decode_text_stream(bytes(rom), bank=0x01, address=0xFFFC)

    def test_presentation_classes_and_dimensions(self):
        rom = bytearray(0xC0100)
        rom[0xC0000:0xC0006] = bytes.fromhex("FF FF FE 00 12 34")
        default = decode_text_presentation(bytes(rom), 0x01FF)
        wide = decode_text_presentation(bytes(rom), 0x0200)
        marker = decode_text_presentation(bytes(rom), 0x0201)
        pair = decode_text_presentation(bytes(rom), 0x0202)
        self.assertEqual((default.kind, default.width_cells), ("default", 16))
        self.assertEqual((wide.kind, wide.width_cells), ("wide_marker", 21))
        self.assertEqual(marker.kind, "default_marker")
        self.assertEqual((pair.kind, pair.raw), ("context_pair", bytes.fromhex("12 34")))


class GlyphDecoderTest(unittest.TestCase):
    @staticmethod
    def tile(value: int) -> list[list[int]]:
        return [[value] * 8 for _ in range(8)]

    @classmethod
    def fixture(cls) -> bytes:
        rom = bytearray(0x1B2000)
        source = glyph_source(0x0100)
        for offset, value in zip(source.block_offsets, (1, 2, 3, 0)):
            rom[offset : offset + 16] = encode_tiles([cls.tile(value)], 2)
        return bytes(rom)

    def test_all_three_source_ranges(self):
        self.assertEqual(glyph_source(0x0100).cpu_address, "B6:80A0")
        self.assertEqual(glyph_source(0x0500).cpu_address, "B7:8000")
        self.assertEqual(glyph_source(0x0900).cpu_address, "B6:BCA0")

    def test_source_wrap_boundaries_are_rejected(self):
        self.assertEqual(glyph_source(0x04F2).address, 0xFEE0)
        self.assertEqual(glyph_source(0x08F7).address, 0xFEE0)
        self.assertEqual(glyph_source(0x0B12).address, 0xFEE0)
        for code in (0x00FF, 0x04F3, 0x08F8, 0x0B13):
            with self.subTest(code=code), self.assertRaises(ValueError):
                glyph_source(code)

    def test_four_blocks_form_one_16_by_16_glyph(self):
        glyph = decode_glyph(self.fixture(), 0x0100)
        self.assertEqual((len(glyph), len(glyph[0])), (16, 16))
        self.assertEqual(glyph[0], (1,) * 8 + (2,) * 8)
        self.assertEqual(glyph[8], (3,) * 8 + (0,) * 8)

    def test_sheet_is_deterministic_and_uses_unique_codes(self):
        image = render_glyph_sheet(
            self.fixture(),
            (0x0100, 0x0100),
            columns=1,
            scale=1,
            gap=0,
        )
        self.assertEqual(image.size, (16, 16))
        self.assertEqual(image.getpixel((0, 0)), 0)
        self.assertEqual(image.getpixel((15, 15)), 255)


@unittest.skipUnless((PROJECT_ROOT / "rom" / "original.sfc").is_file(), "original ROM absent")
class OriginalRomTextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = (PROJECT_ROOT / "rom" / "original.sfc").read_bytes()
        cls.slots = decode_text_slots(cls.rom)
        cls.streams = decode_unique_text_streams(cls.rom, cls.slots)

    def test_confirmed_text_corpus_shape(self):
        self.assertEqual(len(self.slots), 3989)
        self.assertEqual(sum(slot.is_null for slot in self.slots), 431)
        self.assertEqual(len(self.streams), 3553)
        self.assertEqual(
            len({code for stream in self.streams for code in stream.glyph_codes}),
            716,
        )
        self.assertFalse(
            [
                code
                for stream in self.streams
                for code in stream.glyph_codes
                if code < 0x0100
            ]
        )

    def test_startup_selector_structure_and_digest(self):
        slot = self.slots[0x07E1]
        self.assertEqual(slot.pointer_cpu_address, "9C:8064")
        self.assertEqual(slot.target_cpu_address, "9C:9358")
        self.assertEqual(slot.presentation.kind, "wide_marker")
        stream = next(
            stream
            for stream in self.streams
            if stream.bank == slot.pointer_bank and stream.address == slot.target_address
        )
        self.assertEqual(stream.selectors, (0x07E1,))
        self.assertEqual(stream.line_lengths, (14, 14, 14, 14))
        self.assertEqual(len(stream.glyph_codes), 56)
        self.assertEqual(len(set(stream.glyph_codes)), 40)
        self.assertEqual(
            stream.sha256,
            "1fc79be8e4185536a5e87ab8aaab3aa04ed7806a6fec92f2b876316f3f72ff38",
        )

    def test_all_corpus_glyph_sources_are_safe(self):
        for code in {code for stream in self.streams for code in stream.glyph_codes}:
            source = glyph_source(code)
            self.assertLessEqual(source.address + 0x11F, 0xFFFF)
            for offset in source.block_offsets:
                self.assertLessEqual(offset + 16, len(self.rom))


if __name__ == "__main__":
    unittest.main()
