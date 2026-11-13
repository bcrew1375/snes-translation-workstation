import unittest

from snesworkbench.repo_policy import prohibited_path, validate_source_text


PATCH = """schema_version = 1

[[record]]
id = "opening_001"
selector = 0x0123
reference_address = "8C:8020"
reference_offset = 0x060020
pointer_format = "16-bit same-bank LoROM pointer"
original_address = "8C:8123"
original_offset = 0x060123
original_length = 24
source_sha256 = "{digest}"
english = ["English replacement."]
max_line_length = 21
status = "draft"
notes = "Opening message"
"""


class RepositoryPathPolicyTest(unittest.TestCase):
    def test_local_decoded_catalogs_are_prohibited(self):
        self.assertIn(
            "decoded-original",
            prohibited_path("projects/example/translation/strings.tsv"),
        )
        self.assertIn(
            "decoded-original",
            prohibited_path("projects/example/translation/text_layout.tsv"),
        )

    def test_english_translation_manifests_are_allowed(self):
        for name in (
            "patches.toml", "ranges.toml", "glossary.toml",
            "menu.toml", "name_entry.toml", "choices.toml",
            "battle_text.toml", "hud.toml",
        ):
            self.assertIsNone(prohibited_path(f"projects/example/translation/{name}"))

    def test_rom_and_extracted_artwork_are_prohibited(self):
        self.assertIn("ROM input", prohibited_path("projects/example/rom/original.sfc"))
        self.assertIn(
            "extracted project artwork",
            prohibited_path("projects/example/analysis/tiles/bank00.png"),
        )


class RepositoryContentPolicyTest(unittest.TestCase):
    def test_empty_translation_manifests_are_valid(self):
        fixtures = {
            "patches.toml": "record",
            "ranges.toml": "record",
            "glossary.toml": "term",
            "menu.toml": "record",
            "name_entry.toml": "record",
            "choices.toml": "record",
            "battle_text.toml": "record",
            "hud.toml": "record",
        }
        for name, table in fixtures.items():
            with self.subTest(name=name):
                text = f"schema_version = 1\n{table} = []\n"
                self.assertEqual(
                    validate_source_text(f"projects/example/translation/{name}", text), []
                )

    def test_english_patch_with_source_hash_is_valid(self):
        self.assertEqual(
            validate_source_text(
                "projects/example/translation/patches.toml", PATCH.format(digest="a" * 64)
            ),
            [],
        )

    def test_split_patch_manifest_uses_the_patch_schema(self):
        for relative in (
            "projects/example/translation/patches/01_opening.toml",
            "projects/example/translation/patches/01_arc/01_scene.toml",
        ):
            with self.subTest(relative=relative):
                self.assertEqual(
                    validate_source_text(relative, PATCH.format(digest="a" * 64)), []
                )
                failures = validate_source_text(relative, "schema_version = 1\nrecord = [")
                self.assertTrue(any("not valid TOML" in failure for failure in failures))

    def test_split_range_manifest_uses_the_range_schema(self):
        relative = "projects/example/translation/ranges/story/01_arc.toml"
        valid = '''schema_version = 1

[[record]]
name = "scene_streams"
rom_start = 0x0100
rom_end = 0x01FF
cpu_start = "$8100"
cpu_end = "$81FF"
bank = 0x80
alignment = 2
evidence = "Confirmed source allocation."
confidence = "confirmed"
'''
        self.assertEqual(validate_source_text(relative, valid), [])
        failures = validate_source_text(relative, "schema_version = 1\nrecord = [")
        self.assertTrue(any("not valid TOML" in failure for failure in failures))

    def test_nested_typed_collections_use_their_schemas(self):
        battle = '''schema_version = 1

[[record]]
id = "battle_line"
path = "opening"
speaker = "Goku"
resource_id = 0x1000
pointer_address = "B4:8000"
pointer_offset = 0x1A0000
original_address = "B4:8800"
original_offset = 0x1A0800
original_length = 12
source_sha256 = "{digest}"
english = ["Let's go!"]
max_line_length = 21
status = "implemented"
notes = "Confirmed battle line."
'''.format(digest="a" * 64)
        hud = '''schema_version = 1

[[record]]
id = "hud_label"
original_offset = 0x0100
original_length = 8
source_sha256 = "{digest}"
patch_offsets = [0x0100, 0x0102]
english = "HP"
status = "implemented"
notes = "Confirmed HUD label."
'''.format(digest="b" * 64)
        for relative, text in (
            ("projects/example/translation/battle_text/01_arc/opening.toml", battle),
            ("projects/example/translation/hud/encounters/01.toml", hud),
        ):
            with self.subTest(relative=relative):
                self.assertEqual(validate_source_text(relative, text), [])

    def test_unknown_keys_and_wrong_types_are_rejected(self):
        unknown = PATCH.format(digest="a" * 64) + "unexpected = true\n"
        failures = validate_source_text("projects/example/translation/patches.toml", unknown)
        self.assertTrue(any("unknown keys" in failure for failure in failures))

        wrong_type = PATCH.format(digest="a" * 64).replace(
            "original_length = 24", 'original_length = "24"'
        )
        failures = validate_source_text(
            "projects/example/translation/patches.toml", wrong_type
        )
        self.assertTrue(any("invalid type" in failure for failure in failures))

    def test_patch_line_arrays_and_limits_are_validated(self):
        valid = PATCH.format(digest="a" * 64)
        cases = (
            (valid.replace('english = ["English replacement."]', "english = []"), "empty English"),
            (valid.replace('english = ["English replacement."]', 'english = ["ok", 2]'), "non-string"),
            (valid.replace('english = ["English replacement."]', 'english = ["", "   "]'), "no nonblank English lines"),
            (valid.replace("max_line_length = 21", "max_line_length = 22"), "invalid max_line_length"),
            (
                valid.replace('english = ["English replacement."]', f'english = ["{"x" * 22}"]'),
                "has 22 characters",
            ),
        )
        for text, expected in cases:
            with self.subTest(expected=expected):
                failures = validate_source_text(
                    "projects/example/translation/patches.toml", text
                )
                self.assertTrue(any(expected in failure for failure in failures), failures)

    def test_patch_line_arrays_allow_intentional_blank_lines(self):
        valid = PATCH.format(digest="a" * 64)
        for english in ('["", "ok"]', '["one", "", "two"]', '["ok", ""]'):
            with self.subTest(english=english):
                text = valid.replace('english = ["English replacement."]', f"english = {english}")
                self.assertEqual(
                    validate_source_text("projects/example/translation/patches.toml", text),
                    [],
                )

    def test_patch_alias_selectors_are_validated(self):
        valid = PATCH.format(digest="a" * 64) + "alias_selectors = [0x0309]\n"
        self.assertEqual(
            validate_source_text("projects/example/translation/patches.toml", valid),
            [],
        )
        failures = validate_source_text(
            "projects/example/translation/patches.toml",
            valid.replace("[0x0309]", '["0309"]'),
        )
        self.assertTrue(any("invalid alias selectors" in failure for failure in failures))

    def test_patch_source_line_layout_flag_is_validated(self):
        valid = PATCH.format(digest="a" * 64) + "preserve_source_line_layout = true\n"
        self.assertEqual(
            validate_source_text("projects/example/translation/patches.toml", valid),
            [],
        )
        failures = validate_source_text(
            "projects/example/translation/patches.toml",
            valid.replace("true", '"true"'),
        )
        self.assertTrue(any("invalid type" in failure for failure in failures))

    def test_menu_record_type_and_character_offsets_are_validated(self):
        valid = """schema_version = 1

[[record]]
id = "title_menu"
original_address = "84:A1D8"
original_offset = 0x0221D8
original_length = 34
source_sha256 = "{digest}"
record_type = "terminated"
character_offsets = [5, 6]
english = "New Game\\nOptions"
status = "implemented"
notes = "Opening menu"
""".format(digest="a" * 64)
        self.assertEqual(
            validate_source_text("projects/example/translation/menu.toml", valid), []
        )
        invalid = valid.replace('record_type = "terminated"', 'record_type = "unknown"')
        invalid = invalid.replace("character_offsets = [5, 6]", "character_offsets = [-1]")
        failures = validate_source_text("projects/example/translation/menu.toml", invalid)
        self.assertTrue(any("invalid record type" in failure for failure in failures))
        self.assertTrue(any("invalid character offsets" in failure for failure in failures))

    def test_name_entry_record_type_is_validated(self):
        valid = """schema_version = 1

[[record]]
id = "picker_page_1"
original_address = "84:A3E0"
original_offset = 0x0223E0
original_length = 240
source_sha256 = "{digest}"
record_type = "picker_page"
english = "letters_and_pairs"
status = "implemented"
notes = "Name picker"
""".format(digest="a" * 64)
        self.assertEqual(
            validate_source_text("projects/example/translation/name_entry.toml", valid), []
        )
        failures = validate_source_text(
            "projects/example/translation/name_entry.toml",
            valid.replace('record_type = "picker_page"', 'record_type = "unknown"'),
        )
        self.assertTrue(any("invalid record type" in failure for failure in failures))

    def test_choices_record_fields_are_validated(self):
        valid = """schema_version = 1

[[record]]
id = "quiz_x"
record_type = "option"
button = "X"
pointer_address = "98:9B2A"
pointer_offset = 0x0C1B2A
original_address = "98:9E2A"
original_offset = 0x0C1E2A
original_length = 16
source_sha256 = "{digest}"
destination_address = "98:F4D8"
destination_offset = 0x0C74D8
prefix_words = 2
english = "You're bleeding!"
status = "implemented"
notes = "Opening choice"
""".format(digest="a" * 64)
        self.assertEqual(
            validate_source_text("projects/example/translation/choices.toml", valid), []
        )
        failures = validate_source_text(
            "projects/example/translation/choices.toml",
            valid.replace('button = "X"', 'button = "A"'),
        )
        self.assertTrue(any("invalid button" in failure for failure in failures))

    def test_japanese_dialogue_is_rejected(self):
        decoded_source = "decoded: " + "".join(chr(value) for value in (0x65E5, 0x672C, 0x8A9E))
        failures = validate_source_text("projects/example/notes.md", decoded_source)
        self.assertTrue(any("Japanese/CJK" in failure for failure in failures))

    def test_long_original_byte_stream_is_rejected(self):
        byte_stream = ", ".join(f"0x{value:02X}" for value in range(16)) + ","
        failures = validate_source_text("projects/example/notes.md", byte_stream)
        self.assertTrue(any("embedded byte array" in failure for failure in failures))

    def test_malformed_patch_manifest_is_rejected(self):
        failures = validate_source_text(
            "projects/example/translation/patches.toml", "schema_version = 1\nrecord = ["
        )
        self.assertTrue(any("not valid TOML" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()