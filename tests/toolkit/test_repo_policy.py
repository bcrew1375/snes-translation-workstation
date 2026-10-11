import unittest

from snesworkbench.repo_policy import prohibited_path, validate_source_text


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
            "patches.tsv", "references.tsv", "ranges.tsv", "glossary.tsv", "menu.tsv",
            "name_entry.tsv",
        ):
            self.assertIsNone(prohibited_path(f"projects/example/translation/{name}"))

    def test_rom_and_extracted_artwork_are_prohibited(self):
        self.assertIn("ROM input", prohibited_path("projects/example/rom/original.sfc"))
        self.assertIn(
            "extracted project artwork",
            prohibited_path("projects/example/analysis/tiles/bank00.png"),
        )


class RepositoryContentPolicyTest(unittest.TestCase):
    def test_header_only_translation_manifests_are_valid(self):
        fixtures = {
            "patches.tsv": (
                "id\toriginal_address\toriginal_offset\toriginal_length\t"
                "source_sha256\tenglish\tstatus\tnotes\n"
            ),
            "references.tsv": (
                "id\treference_type\treference_address\treference_offset\t"
                "message_index\tpointer_format\ttarget_address\ttarget_offset\n"
            ),
            "ranges.tsv": (
                "name\trom_start\trom_end\tcpu_start\tcpu_end\tbank\talignment\t"
                "evidence\tconfidence\n"
            ),
            "glossary.tsv": (
                "id\tcategory\tcanonical\taliases\tusage_notes\tstatus\n"
            ),
            "menu.tsv": (
                "id\toriginal_address\toriginal_offset\toriginal_length\t"
                "source_sha256\trecord_type\tcharacter_offsets\tenglish\tstatus\tnotes\n"
            ),
            "name_entry.tsv": (
                "id\toriginal_address\toriginal_offset\toriginal_length\t"
                "source_sha256\trecord_type\tenglish\tstatus\tnotes\n"
            ),
        }
        for name, text in fixtures.items():
            with self.subTest(name=name):
                self.assertEqual(
                    validate_source_text(f"projects/example/translation/{name}", text), []
                )

    def test_english_patch_with_source_hash_is_valid(self):
        header = (
            "id\toriginal_address\toriginal_offset\toriginal_length\t"
            "source_sha256\tenglish\tstatus\tnotes\n"
        )
        row = (
            "opening_001\t0C:8123\t0x060123\t24\t"
            + "a" * 64
            + "\tAn English replacement.\tdraft\tOpening message\n"
        )
        self.assertEqual(
            validate_source_text("projects/example/translation/patches.tsv", header + row), []
        )

    def test_menu_record_type_and_character_offsets_are_validated(self):
        header = (
            "id\toriginal_address\toriginal_offset\toriginal_length\t"
            "source_sha256\trecord_type\tcharacter_offsets\tenglish\tstatus\tnotes\n"
        )
        valid = (
            "title_menu\t84:A1D8\t0x0221D8\t34\t" + "a" * 64
            + "\tterminated\t5,6\tNew Game\\nOptions\timplemented\tOpening menu\n"
        )
        self.assertEqual(
            validate_source_text("projects/example/translation/menu.tsv", header + valid), []
        )
        invalid = valid.replace("\tterminated\t5,6\t", "\tunknown\t-1\t")
        failures = validate_source_text(
            "projects/example/translation/menu.tsv", header + invalid
        )
        self.assertTrue(any("invalid record type" in failure for failure in failures))
        self.assertTrue(any("invalid character offsets" in failure for failure in failures))

    def test_name_entry_record_type_is_validated(self):
        header = (
            "id\toriginal_address\toriginal_offset\toriginal_length\t"
            "source_sha256\trecord_type\tenglish\tstatus\tnotes\n"
        )
        valid = (
            "picker_page_1\t84:A3E0\t0x0223E0\t240\t" + "a" * 64
            + "\tpicker_page\tletters_and_pairs\timplemented\tName picker\n"
        )
        self.assertEqual(
            validate_source_text("projects/example/translation/name_entry.tsv", header + valid), []
        )
        failures = validate_source_text(
            "projects/example/translation/name_entry.tsv",
            header + valid.replace("\tpicker_page\t", "\tunknown\t"),
        )
        self.assertTrue(any("invalid record type" in failure for failure in failures))

        default_names = (
            "default_names\t84:A048\t0x022048\t50\t" + "a" * 64
            + "\tdefault_names\tAiyah\\nBuddy\\nMeanie\\nSally\\nTeach\timplemented\t"
            "Localized defaults\n"
        )
        self.assertEqual(
            validate_source_text(
                "projects/example/translation/name_entry.tsv", header + default_names
            ),
            [],
        )

    def test_japanese_dialogue_is_rejected(self):
        # Construct the fixture at runtime so repository source does not itself
        # contain the CJK content that this test is intended to reject.
        decoded_source = "decoded: " + "".join(chr(value) for value in (0x65E5, 0x672C, 0x8A9E))
        failures = validate_source_text("projects/example/notes.md", decoded_source)
        self.assertTrue(any("Japanese/CJK" in failure for failure in failures))

    def test_long_original_byte_stream_is_rejected(self):
        byte_stream = ", ".join(f"0x{value:02X}" for value in range(16)) + ","
        failures = validate_source_text("projects/example/notes.md", byte_stream)
        self.assertTrue(any("embedded byte array" in failure for failure in failures))

    def test_malformed_patch_manifest_is_rejected(self):
        failures = validate_source_text(
            "projects/example/translation/patches.tsv", "id\tenglish\nexample\tText\n"
        )
        self.assertTrue(any("invalid header" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()