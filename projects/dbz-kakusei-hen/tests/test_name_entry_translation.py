"""Tests for the packed-character five-name editor."""

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
from dbz_kakusei_hen.glyphs import (  # noqa: E402
    BASIC_LATIN_CHARACTERS,
    EXTENDED_LATIN_CHARACTERS,
    LATIN_MARKER,
    encode_latin_cell,
)
from dbz_kakusei_hen.name_entry_translation import (  # noqa: E402
    ACTION_GLYPH_INDICES,
    DEFAULT_NAME_COUNT,
    DEFAULT_NAMES_LENGTH,
    DEFAULT_NAMES_OFFSET,
    LATIN_GLYPH_CODES,
    LATIN_GLYPH_SOURCE_SHA256,
    LATIN_PICKER_PAGE_1_OFFSET,
    LATIN_PICKER_PAGE_2_OFFSET,
    LATIN_SELECTION_MAP_1_OFFSET,
    LATIN_SELECTION_MAP_2_OFFSET,
    NAME_FIELD_CHARACTERS,
    NAME_RENDER_PATCH_RANGES,
    NAME_RENDER_PATCH_SOURCE_SHA256,
    PAGE_1_CHARACTERS,
    PAGE_2_CHARACTERS,
    PICKER_PAGE_1_OFFSET,
    PICKER_PAGE_2_OFFSET,
    PICKER_PAGE_LENGTH,
    PICKER_STREAM_ENTRY_INDICES,
    SELECTION_MAP_1_OFFSET,
    SELECTION_MAP_2_OFFSET,
    SELECTION_MAP_LENGTH,
    SINGLE_CHARACTERS,
    backspace_name_fields,
    decode_name_words,
    encode_default_name_words,
    encode_latin_glyph,
    encode_name_words,
    load_name_entry_records,
    name_cursor_x,
    overwrite_name_character,
    picker_word,
    prepare_name_field_for_edit,
    render_latin_character,
)
from dbz_kakusei_hen.scenario import decode_glyph, decode_text_slots, decode_unique_text_streams, glyph_source  # noqa: E402


class PackedNameTest(unittest.TestCase):
    def test_names_use_five_words_for_ten_independent_characters(self):
        for name in ("Goku", "Piccolo", "Chiaotzu", "1234567890"):
            words = encode_name_words(name)
            with self.subTest(name=name):
                self.assertEqual(len(words), 5)
                self.assertTrue(all(word & LATIN_MARKER for word in words))
                self.assertEqual(decode_name_words(words), name)

    def test_name_limit_and_unsupported_characters_are_strict(self):
        with self.assertRaisesRegex(WorkstationError, "10 name characters"):
            encode_name_words("12345678901")
        with self.assertRaisesRegex(WorkstationError, "unsupported Latin character"):
            encode_name_words("Goku@")

    def test_extended_names_round_trip(self):
        for name in ("José", "Björk", "Tōru", "François"):
            with self.subTest(name=name):
                self.assertEqual(decode_name_words(encode_name_words(name)), name)

    def test_default_names_use_ordinary_packed_latin(self):
        words = encode_default_name_words("Aiyah")
        self.assertEqual(words, encode_name_words("Aiyah"))
        self.assertEqual(decode_name_words(words), "Aiyah")

    def test_first_edit_overwrites_only_selected_character_in_all_fields(self):
        defaults = tuple(
            encode_default_name_words(name)
            for name in ("Aiyah", "Buddy", "Meanie", "Sally", "Teach")
        )
        for field_index in range(5):
            for position, character in ((0, "Z"), (1, "Á"), (8, "x"), (9, "ū")):
                fields = list(defaults)
                fields[field_index] = overwrite_name_character(fields[field_index], position, character)
                before = decode_name_words(defaults[field_index]).ljust(NAME_FIELD_CHARACTERS)
                after = decode_name_words(fields[field_index]).ljust(NAME_FIELD_CHARACTERS)
                with self.subTest(field=field_index, position=position, character=character):
                    self.assertEqual(after[position], character)
                    self.assertEqual(after[:position] + after[position + 1:], before[:position] + before[position + 1:])
                    self.assertEqual(fields[:field_index], list(defaults[:field_index]))
                    self.assertEqual(fields[field_index + 1:], list(defaults[field_index + 1:]))

    def test_first_edit_preserves_packed_latin_and_clears_legacy(self):
        edited = encode_name_words("Goku")
        self.assertEqual(prepare_name_field_for_edit(edited), edited)
        self.assertEqual(prepare_name_field_for_edit((0x0123,) * 5), (0x8000,) * 5)

    def test_overwrite_covers_even_odd_and_high_page_two_ids(self):
        original = encode_name_words("ABCDEFGHIJ")
        for position, character in ((2, "Á"), (3, "\""), (6, "ū"), (7, "+")):
            updated = overwrite_name_character(original, position, character)
            expected = list("ABCDEFGHIJ")
            expected[position] = character
            with self.subTest(position=position, character=character):
                self.assertEqual(decode_name_words(updated), "".join(expected))

    def test_backspace_only_moves_the_cursor_for_every_valid_position(self):
        field_sets = (
            tuple(encode_name_words("ABCDEFGHIJ") for _ in range(5)),
            tuple(
                encode_default_name_words(name)
                for name in ("Aiyah", "Buddy", "Meanie", "Sally", "Teach")
            ),
            (
                encode_name_words("Goku"),
                encode_default_name_words("Buddy"),
                (0x8000,) * 5,
                encode_name_words("1234567890"),
                (0x0123,) * 5,
            ),
        )
        for fields in field_sets:
            for cursor in range(DEFAULT_NAME_COUNT * NAME_FIELD_CHARACTERS):
                with self.subTest(cursor=cursor, fields=fields):
                    self.assertEqual(backspace_name_fields(cursor, fields), (max(cursor - 1, 0), fields))

    def test_backspace_rejects_invalid_editor_shapes_and_cursors(self):
        fields = tuple(encode_name_words("Goku") for _ in range(5))
        for cursor in (-1, 50):
            with self.subTest(cursor=cursor):
                with self.assertRaisesRegex(WorkstationError, "outside the five name fields"):
                    backspace_name_fields(cursor, fields)
        with self.assertRaisesRegex(WorkstationError, "name editor has 4 fields"):
            backspace_name_fields(1, fields[:4])
        with self.assertRaisesRegex(WorkstationError, "every name field must contain 5 words"):
            backspace_name_fields(1, fields[:4] + ((0x8000,) * 4,))

    def test_cursor_advances_six_pixels_per_character_and_resets_per_field(self):
        self.assertEqual(NAME_FIELD_CHARACTERS, 10)
        self.assertEqual(
            [name_cursor_x(i) for i in range(12)],
            [0xB0, 0xB6, 0xBC, 0xC2, 0xC8, 0xCE, 0xD4, 0xDA, 0xE0, 0xE6, 0xB0, 0xB6],
        )

    def test_single_character_glyphs_round_trip_through_game_decoder(self):
        for character, code in LATIN_GLYPH_CODES.items():
            source = glyph_source(code)
            fixture = bytearray(max(source.block_offsets) + 16)
            for offset, block in zip(source.block_offsets, encode_latin_glyph(character), strict=True):
                fixture[offset:offset + 16] = block
            with self.subTest(character=character):
                self.assertEqual(decode_glyph(bytes(fixture), code), render_latin_character(character))

    def test_picker_pages_contain_only_single_characters_or_blanks(self):
        self.assertEqual(len(PAGE_1_CHARACTERS), 85)
        self.assertEqual(len(PAGE_2_CHARACTERS), 85)
        self.assertTrue(all(len(character) == 1 for character in PAGE_1_CHARACTERS))
        self.assertTrue(all(len(character) == 1 for character in PAGE_2_CHARACTERS))
        self.assertNotEqual(PAGE_1_CHARACTERS, PAGE_2_CHARACTERS)
        self.assertEqual(PAGE_1_CHARACTERS[:len(BASIC_LATIN_CHARACTERS)], BASIC_LATIN_CHARACTERS)
        self.assertEqual(PAGE_2_CHARACTERS[:len(EXTENDED_LATIN_CHARACTERS)], EXTENDED_LATIN_CHARACTERS)
        self.assertEqual(set(SINGLE_CHARACTERS), set(BASIC_LATIN_CHARACTERS + EXTENDED_LATIN_CHARACTERS))


@unittest.skipUnless((PROJECT_ROOT / "rom" / "original.sfc").is_file(), "original ROM absent")
class OriginalRomNameEntryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (PROJECT_ROOT / "rom" / "original.sfc").read_bytes()
        cls.records = load_name_entry_records(PROJECT_ROOT / "translation" / "name_entry.toml")
        cls.translated = build(cls.original, None).data

    def test_marker_is_unused_by_all_original_compositor_inputs(self):
        slots = decode_text_slots(self.original)
        words = {
            word
            for stream in decode_unique_text_streams(self.original, slots)
            for word in stream.words
        }
        defaults = {
            int.from_bytes(self.original[offset:offset + 2], "little")
            for offset in range(DEFAULT_NAMES_OFFSET, DEFAULT_NAMES_OFFSET + DEFAULT_NAMES_LENGTH, 2)
        }
        self.assertFalse(any(word & LATIN_MARKER for word in words | defaults))

    def test_runtime_and_glyph_source_digests_are_pinned(self):
        runtime = b"".join(self.original[start:end] for start, end in NAME_RENDER_PATCH_RANGES)
        self.assertEqual(hashlib.sha256(runtime).hexdigest(), NAME_RENDER_PATCH_SOURCE_SHA256)
        glyphs = b"".join(
            self.original[offset:offset + 16]
            for code in LATIN_GLYPH_CODES.values()
            for offset in glyph_source(code).block_offsets
        )
        self.assertEqual(hashlib.sha256(glyphs).hexdigest(), LATIN_GLYPH_SOURCE_SHA256)

    def test_extended_glyph_records_are_zero_filled_and_unreferenced(self):
        original_codes = {
            code
            for stream in decode_unique_text_streams(self.original, decode_text_slots(self.original))
            for code in stream.glyph_codes
        }
        for character in EXTENDED_LATIN_CHARACTERS:
            code = LATIN_GLYPH_CODES[character]
            source = glyph_source(code)
            with self.subTest(character=character, code=f"${code:04X}"):
                self.assertNotIn(code, original_codes)
                self.assertTrue(all(
                    self.original[offset:offset + 16] == bytes(16)
                    for offset in source.block_offsets
                ))

    def test_runtime_hooks_preserve_done_exit_and_narrow_only_character_selector(self):
        insertion_hook = self.translated[0x008AD7:0x008ADB]
        self.assertEqual(insertion_hook[0], 0x5C)
        self.assertEqual(insertion_hook[3], 0x81)
        self.assertIn(int.from_bytes(insertion_hook[1:3], "little"), range(0xDA50, 0xDD14))
        self.assertEqual(
            self.translated[0x008B50:0x008B5D],
            self.original[0x008B50:0x008B5D],
        )
        self.assertEqual(self.translated[0x008B5E:0x008B63][-1], 0x60)
        self.assertEqual(self.translated[0x008BDD:0x008BE2][-1], 0x60)
        self.assertEqual(self.translated[0x008C38:0x008C3D][-1], 0x60)
        routines = self.translated[0x00DA50:0x00DD14]
        self.assertGreaterEqual(routines.count(bytes.fromhex("ad 16 02")), 3)
        self.assertIn(bytes.fromhex("c9 28 00 90 11 28 60"), routines)
        self.assertIn(bytes.fromhex("a9 0c 00 80 03 a9 0d 00"), routines)
        self.assertNotIn(bytes.fromhex("ad 2b 02 f0 43 c9 0a 00"), routines)

    def test_password_insertion_rejoins_the_original_one_word_path(self):
        insertion_hook = self.translated[0x008AD7:0x008ADB]
        dispatcher_cpu = int.from_bytes(insertion_hook[1:3], "little")
        dispatcher_offset = 0x00DA50 + (dispatcher_cpu - 0xDA50)
        dispatcher = self.translated[dispatcher_offset:dispatcher_offset + 32]

        # LDA $0216 / BNE password; fresh names long-jump to translated work.
        self.assertEqual(dispatcher[:5], bytes.fromhex("ad 16 02 d0 04"))
        self.assertEqual(dispatcher[5], 0x5C)
        self.assertEqual(dispatcher[8], 0x81)

        # Password mode reproduces the hook's displaced LDA/CMP and rejoins at
        # $81:8ADD, where the original BCS selects action handling. Everything
        # after that point remains the original map/store/redraw/cursor path.
        self.assertEqual(dispatcher[9:19], bytes.fromhex("ad 29 02 c9 55 00 5c dd 8a 81"))
        self.assertEqual(
            self.translated[0x008ADD:0x008B50],
            self.original[0x008ADD:0x008B50],
        )
        self.assertIn(bytes.fromhex("20 aa 8b"), self.translated[0x008ADD:0x008B50])

    def test_password_dispatch_bypasses_translated_name_only_work(self):
        routines = self.translated[0x00DA50:0x00DD14]
        dispatcher_jump = bytes.fromhex("5c dd 8a 81")
        latin_redraw = bytes.fromhex("22 2e ed 80")
        self.assertEqual(routines.count(dispatcher_jump), 1)
        self.assertEqual(routines.count(latin_redraw), 1)
        self.assertNotIn(dispatcher_jump, routines[routines.index(latin_redraw):])

    def test_both_character_selectors_are_narrowed_relative_to_their_oam_position(self):
        routines = self.translated[0x00DA50:0x00DD14]
        narrow_helper = bytes.fromhex(
            "c2 10 ae 15 01 e2 20 bf f0 1f 7e 38 e9 06 9f f0 1f 7e "
            "bf f4 1f 7e 38 e9 06 9f f4 1f 7e 60"
        )
        helper_offset = routines.index(narrow_helper)
        helper_cpu = 0xDA50 + helper_offset
        narrow_call = bytes((0x20, helper_cpu & 0xFF, helper_cpu >> 8))
        self.assertEqual(routines.count(narrow_call), 2)
        self.assertIn(
            narrow_helper,
            routines,
        )

    def test_picker_and_name_selectors_are_shifted_up_two_pixels(self):
        routines = self.translated[0x00DA50:0x00DD14]
        self.assertIn(bytes.fromhex("69 96 00 85 48"), routines)
        self.assertIn(bytes.fromhex("bf 71 8c 81 29 ff 00 3a 3a 85 48"), routines)

    def test_opening_menu_selector_rows_are_shifted_up_two_pixels(self):
        self.assertEqual(self.translated[0x008685:0x00868B], bytes.fromhex("9e 00 ae 00 be 00"))

    def test_blank_latin_id_uses_the_six_pixel_advance_fast_path(self):
        compositor = self.translated[0x006BCF:0x006DB3]
        self.assertIn(bytes.fromhex("c9 00 00 f0 29"), compositor)
        self.assertIn(bytes.fromhex("ad 08 02 18 69 06 00 8d 08 02"), compositor)

    def test_edits_call_the_bounded_name_field_redraw(self):
        routines = self.translated[0x00DA50:0x00DD14]
        self.assertEqual(routines.count(bytes.fromhex("22 2e ed 80")), 1)
        self.assertNotIn(bytes.fromhex("20 aa 8b"), routines)
        redraw = self.translated[0x006D2E:0x006DB3]
        self.assertIn(bytes.fromhex("85 ef 18 69 00 01 85 0c 85 ed a9 20 11 85 eb"), redraw)
        self.assertIn(bytes.fromhex("a9 08 00 8d 0e 02 a9 0a 00 8d 10 02 a9 40 00 8d 0a 02"), redraw)
        self.assertIn(bytes.fromhex("22 d7 88 80"), redraw)

    def test_first_edit_preserves_packed_latin_and_detects_only_legacy_fields(self):
        routines = self.translated[0x00DA50:0x00DD14]
        self.assertIn(bytes.fromhex("bd 00 0c 30 0e"), routines)
        self.assertNotIn(bytes.fromhex("89 00 40"), routines)

    def test_picker_pages_match_selection_maps(self):
        for page_offset, map_offset, characters in (
            (LATIN_PICKER_PAGE_1_OFFSET, LATIN_SELECTION_MAP_1_OFFSET, PAGE_1_CHARACTERS),
            (LATIN_PICKER_PAGE_2_OFFSET, LATIN_SELECTION_MAP_2_OFFSET, PAGE_2_CHARACTERS),
        ):
            page_words = tuple(
                int.from_bytes(self.translated[page_offset + i * 2:page_offset + i * 2 + 2], "little")
                for i in PICKER_STREAM_ENTRY_INDICES
            )
            map_words = tuple(
                int.from_bytes(self.translated[map_offset + i * 2:map_offset + i * 2 + 2], "little")
                for i in range(85)
            )
            with self.subTest(page=f"${page_offset:06X}"):
                self.assertEqual(page_words, map_words)
                self.assertEqual(map_words, tuple(picker_word(character) for character in characters))

    def test_picker_control_structure_and_done_label_are_preserved(self):
        expected = (encode_latin_cell("D", "O"), encode_latin_cell("N", "E"), 0x8000, 0x8000)
        for source_offset, page_offset in (
            (PICKER_PAGE_1_OFFSET, LATIN_PICKER_PAGE_1_OFFSET),
            (PICKER_PAGE_2_OFFSET, LATIN_PICKER_PAGE_2_OFFSET),
        ):
            original = self.original[source_offset:source_offset + PICKER_PAGE_LENGTH]
            translated = self.translated[page_offset:page_offset + PICKER_PAGE_LENGTH]
            original_words = tuple(int.from_bytes(original[i:i + 2], "little") for i in range(0, len(original), 2))
            translated_words = tuple(int.from_bytes(translated[i:i + 2], "little") for i in range(0, len(translated), 2))
            mutable = set(PICKER_STREAM_ENTRY_INDICES) | set(ACTION_GLYPH_INDICES)
            self.assertEqual(
                tuple(word for i, word in enumerate(original_words) if i not in mutable),
                tuple(word for i, word in enumerate(translated_words) if i not in mutable),
            )
            self.assertEqual(tuple(translated_words[i] for i in ACTION_GLYPH_INDICES), expected)

    def test_password_resources_and_messages_remain_byte_identical(self):
        for start, end in (
            (PICKER_PAGE_1_OFFSET, PICKER_PAGE_2_OFFSET + PICKER_PAGE_LENGTH),
            (SELECTION_MAP_1_OFFSET, SELECTION_MAP_2_OFFSET + SELECTION_MAP_LENGTH),
            (0x022630, 0x0226B4),
        ):
            with self.subTest(start=f"${start:06X}"):
                self.assertEqual(self.translated[start:end], self.original[start:end])

    def test_password_selection_codes_do_not_use_overwritten_latin_glyph_records(self):
        password_codes = {
            int.from_bytes(self.original[offset:offset + 2], "little")
            for start in (SELECTION_MAP_1_OFFSET, SELECTION_MAP_2_OFFSET)
            for offset in range(start, start + SELECTION_MAP_LENGTH, 2)
        }
        self.assertTrue(password_codes.isdisjoint(LATIN_GLYPH_CODES.values()))

    def test_default_five_name_fields_are_localized_in_place(self):
        data = self.translated[DEFAULT_NAMES_OFFSET:DEFAULT_NAMES_OFFSET + DEFAULT_NAMES_LENGTH]
        words = tuple(int.from_bytes(data[offset:offset + 2], "little") for offset in range(0, len(data), 2))
        self.assertEqual(
            tuple(decode_name_words(words[index:index + 5]) for index in range(0, 25, 5)),
            ("Aiyah", "Buddy", "Meanie", "Sally", "Teach"),
        )
        self.assertEqual(
            tuple(words[index:index + 5] for index in range(0, 25, 5)),
            tuple(encode_name_words(name) for name in ("Aiyah", "Buddy", "Meanie", "Sally", "Teach")),
        )

    def test_project_build_reports_name_editor_metadata(self):
        result = build(self.original, None)
        self.assertEqual(result.metadata["name_entry_defaults"], ["Aiyah", "Buddy", "Meanie", "Sally", "Teach"])
        self.assertIn(["Player", "Friend", "Bully", "Girl", "Teacher"], result.metadata["name_entry_lines"])


if __name__ == "__main__":
    unittest.main()