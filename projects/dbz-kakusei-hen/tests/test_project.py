"""Project metadata checks that do not require the original ROM.

The ROM-independent test suite in ``tests/toolkit`` runs everywhere. These
checks confirm that the project descriptor is well-formed and internally
consistent, so a malformed ``project.toml`` is caught even without the
copyrighted input present.
"""

import re
import tomllib
import unittest
from pathlib import Path

from snesworkbench.status import load_project_status

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ProjectDescriptorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (PROJECT_ROOT / "project.toml").open("rb") as handle:
            cls.data = tomllib.load(handle)

    def test_identity_matches_directory(self):
        self.assertEqual(self.data["id"], PROJECT_ROOT.name)

    def test_platform_is_snes(self):
        self.assertEqual(self.data["platform"], "snes")

    def test_rom_path_is_project_relative(self):
        """The project owns its ROM; the ID must not be repeated in the path."""
        rom = self.data["input"]["default_path"]
        self.assertEqual(rom, "rom/original.sfc")
        self.assertNotIn(self.data["id"], rom)

    def test_original_rom_is_fully_pinned(self):
        """The source ROM must always declare size and digest."""
        self.assertIsInstance(self.data["input"]["size"], int)
        self.assertRegex(self.data["input"]["sha256"], r"^[0-9a-f]{64}$")

    def test_translated_rom_is_fully_pinned(self):
        """The implemented opening translation has a deterministic identity."""
        output = self.data["output"]
        self.assertEqual(output["size"], self.data["input"]["size"])
        self.assertRegex(output["sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(output["default_path"].endswith("translated.sfc"))

    def test_analysis_manifest_exists(self):
        manifest = PROJECT_ROOT / self.data["manifests"]["analysis"]
        self.assertTrue(manifest.is_file(), f"missing analysis manifest {manifest}")

    def test_translation_manifests_exist(self):
        patches = PROJECT_ROOT / self.data["manifests"]["patches"]
        self.assertTrue(patches.is_dir(), f"missing translation manifest collection {patches}")
        for name in ("references", "ranges", "menu", "name_entry", "choices", "glossary"):
            manifest = PROJECT_ROOT / self.data["manifests"][name]
            self.assertTrue(manifest.is_file(), f"missing translation manifest {manifest}")

    def test_status_manifest_is_valid(self):
        status = load_project_status(PROJECT_ROOT / self.data["manifests"]["status"])
        self.assertEqual(status.phase, "opening_tournament_quiz")
        self.assertTrue(status.milestones)
        self.assertTrue(status.recommended_tasks)

    def test_runtime_evidence_ledger_exists(self):
        ledger = PROJECT_ROOT / self.data["manifests"]["runtime_evidence"]
        self.assertTrue(ledger.is_file(), f"missing runtime evidence ledger {ledger}")


class TranslationManifestTest(unittest.TestCase):
    @staticmethod
    def load(name: str, table: str = "record") -> list[dict[str, object]]:
        with (PROJECT_ROOT / "translation" / name).open("rb") as source:
            return tomllib.load(source)[table]

    @staticmethod
    def load_patches() -> list[dict[str, object]]:
        records = []
        for path in sorted((PROJECT_ROOT / "translation" / "patches").glob("*.toml")):
            with path.open("rb") as source:
                document = tomllib.load(source)
            records.extend(document["record"])
        return records

    def test_tracked_manifests_are_versioned_toml_with_records(self):
        for name, table in (
            ("references.toml", "record"), ("ranges.toml", "record"), ("menu.toml", "record"),
            ("name_entry.toml", "record"), ("choices.toml", "record"),
            ("glossary.toml", "term"),
        ):
            with self.subTest(name=name):
                with (PROJECT_ROOT / "translation" / name).open("rb") as source:
                    document = tomllib.load(source)
                self.assertEqual(document["schema_version"], 1)
                self.assertTrue(document[table])

        patch_paths = sorted((PROJECT_ROOT / "translation" / "patches").glob("*.toml"))
        self.assertEqual(
            [path.name for path in patch_paths],
            [
                "01_opening_narration.toml",
                "02_opening_recap.toml",
                "03_tournament_opening.toml",
            ],
        )
        for path in patch_paths:
            with self.subTest(name=path.name):
                with path.open("rb") as source:
                    document = tomllib.load(source)
                self.assertEqual(document["schema_version"], 1)
                self.assertTrue(document["record"])

    def test_tracked_manifests_preserve_opening_records(self):
        patches = self.load_patches()
        self.assertEqual(len(patches), 53)
        self.assertEqual(
            [patch["id"] for patch in patches[:4]],
            ["opening_narration", "opening_narration_2", "opening_narration_3", "opening_narration_4"],
        )
        self.assertEqual(
            [patch["id"] for patch in patches[4:26]],
            [f"opening_recap_{index:02d}" for index in range(1, 23)],
        )
        self.assertEqual(
            [patch["id"] for patch in patches[26:]],
            [f"tournament_opening_{index:02d}" for index in range(27)],
        )
        self.assertEqual(
            [patch["original_address"] for patch in patches[:4]],
            ["9C:9358", "9C:93D0", "9C:9444", "9C:948C"],
        )
        self.assertEqual(
            [patch["original_offset"] for patch in patches[:4]],
            [0x0E1358, 0x0E13D0, 0x0E1444, 0x0E148C],
        )
        self.assertEqual([patch["original_length"] for patch in patches[:4]], [120, 116, 72, 26])
        self.assertTrue(all(patch["status"] == "implemented" for patch in patches))
        self.assertEqual([len(patch["english"]) for patch in patches[:4]], [4, 4, 3, 1])
        self.assertTrue(
            all(
                isinstance(line, str) and line
                for patch in patches
                for line in patch["english"]
            )
        )
        self.assertEqual(
            {patch["id"] for patch in patches if "max_line_length" not in patch},
            {"opening_recap_01", "opening_recap_04", "opening_recap_15", "opening_recap_19"},
        )
        self.assertEqual(sum(patch.get("max_line_length") == 21 for patch in patches), 44)
        self.assertEqual(sum(patch.get("max_line_length") == 28 for patch in patches), 5)

        references = self.load("references.toml")
        self.assertEqual(len(references), 55)
        self.assertEqual(
            [reference["message_index"] for reference in references[4:26]],
            [
                0x0026, 0x07E5, 0x07E6, 0x002E, 0x07E7, 0x076B,
                0x07E8, 0x07E9, 0x07EA, 0x07EB, 0x07EC, 0x07ED,
                0x07EE, 0x07EF, 0x0000, 0x0800, 0x0801, 0x0802,
                0x0003, 0x0803, 0x0804, 0x0805,
            ],
        )
        self.assertEqual(
            [reference["id"] for reference in references[-2:]],
            ["tournament_arena_label", "papaya_island_label"],
        )
        self.assertEqual(
            [reference["reference_type"] for reference in references[-2:]],
            ["fixed_resource_pointer", "fixed_resource_pointer"],
        )

        menu = self.load("menu.toml")
        self.assertEqual(
            [record["id"] for record in menu],
            [
                "title_menu_no_save", "title_menu_with_save", "new_game_start_method",
                "options_sound_stereo", "options_sound_mono",
            ] + [f"options_bgm_{index:02d}" for index in range(20)],
        )
        self.assertEqual(
            [record["original_offset"] for record in menu],
            [0x0221D8, 0x0221FA, 0x02222E, 0x022254, 0x022266]
            + [0x022278 + index * 18 for index in range(20)],
        )
        self.assertTrue(all(record["status"] == "implemented" for record in menu))

        name_entry = self.load("name_entry.toml")
        self.assertEqual(
            [record["id"] for record in name_entry],
            [
                "picker_page_1", "picker_page_2", "selection_map_1", "selection_map_2",
                "default_names", "name_controls", "name_labels",
            ],
        )
        self.assertEqual(
            [record["original_offset"] for record in name_entry[:4]],
            [0x0223E0, 0x0224D0, 0x008D56, 0x008E00],
        )
        self.assertTrue(all(record["status"] == "implemented" for record in name_entry))

        choices = self.load("choices.toml")
        self.assertEqual(len(choices), 5)
        self.assertEqual([row["button"] for row in choices], ["", "", "X", "Y", "B"])
        self.assertEqual([row["english"] for row in choices], [
            "World Tournament Arena", "Papaya Island",
            "You're bleeding!", "Are you sick?", "You look sexy.",
        ])

    def test_local_decoded_catalog_names_remain_ignored(self):
        ignore = (PROJECT_ROOT.parents[1] / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/projects/*/translation/strings.tsv", ignore)
        self.assertIn("/projects/*/translation/text_layout.tsv", ignore)


class AnalysisManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import json

        cls.document = json.loads(
            (PROJECT_ROOT / "analysis" / "project.json").read_text(encoding="utf-8")
        )

    def test_regions_are_non_overlapping_and_in_range(self):
        rom_size = self.document["rom"]["size_bytes"]
        regions = self.document["regions"]
        self.assertTrue(regions, "expected at least one region")
        for region in regions:
            self.assertLess(int(region["rom_end"][1:], 16), rom_size)
            self.assertLessEqual(
                int(region["rom_start"][1:], 16), int(region["rom_end"][1:], 16)
            )
        spans = sorted(
            (int(r["rom_start"][1:], 16), int(r["rom_end"][1:], 16)) for r in regions
        )
        for (_, left_end), (right_start, _) in zip(spans, spans[1:]):
            self.assertGreater(right_start, left_end, "regions must not overlap")

    def test_no_region_is_declared_unknown(self):
        """Unlisted bytes are reported as unknown; regions must classify bytes."""
        for region in self.document["regions"]:
            self.assertNotEqual(region["type"], "unknown")

    def test_confirmed_glyph_regions_are_recorded(self):
        regions = {
            (region["rom_start"], region["rom_end"]): region
            for region in self.document["regions"]
        }
        lower = regions[("$1B00A0", "$1B3BBF")]
        self.assertEqual(lower["bank"], 0x36)
        self.assertEqual((lower["cpu_start"], lower["cpu_end"]), ("$80A0", "$BBBF"))
        self.assertEqual(lower["type"], "graphics")
        self.assertEqual(lower["confidence"], "confirmed")

        upper = regions[("$1B3CA0", "$1B63BF")]
        self.assertEqual(upper["bank"], 0x36)
        self.assertEqual((upper["cpu_start"], upper["cpu_end"]), ("$BCA0", "$E3BF"))
        self.assertEqual(upper["type"], "graphics")
        self.assertEqual(upper["confidence"], "confirmed")

        region = regions[("$1B8000", "$1BFFFF")]
        self.assertEqual(region["bank"], 0x37)
        self.assertEqual((region["cpu_start"], region["cpu_end"]), ("$8000", "$FFFF"))
        self.assertEqual(region["type"], "graphics")
        self.assertEqual(region["confidence"], "confirmed")

        finding = self.document["findings"]["font_regions"]
        self.assertEqual(finding["status"], "confirmed_graphics")
        self.assertEqual(finding["confidence"], "confirmed")
        self.assertIn("16x16 bitmap", finding["format"])
        self.assertIn("12 pixels", finding["format"])
        self.assertIn("716 distinct codes", finding["evidence"])
        self.assertIn("$B6:80A0", finding["location"])
        self.assertIn("$B7:8000", finding["location"])

    def test_scenario_interpreter_tables_are_recorded(self):
        regions = {
            (region["rom_start"], region["rom_end"]): region
            for region in self.document["regions"]
        }
        self.assertEqual(regions[("$01B24F", "$01B2A6")]["type"], "code")
        self.assertEqual(regions[("$01B2A7", "$01B338")]["type"], "pointer_table")
        self.assertEqual(regions[("$01EA41", "$01EE96")]["type"], "pointer_table")

        finding = self.document["findings"]["scenario_bytecode"]
        self.assertEqual(finding["status"], "confirmed_interpreter_partial_schema")
        self.assertEqual(finding["terminator"], "$49 ends the interpreter loop")
        self.assertIn("370 three-byte selector slots", finding["root_table"])
        self.assertIn("slots $0161-$016E are null", finding["root_table"])
        self.assertIn("$08", finding["known_commands"])
        self.assertIn("$48", finding["known_commands"])
        self.assertIn("3,989", finding["text_tables"])
        self.assertIn("3,553 unique", finding["text_tables"])
        self.assertIn("716 distinct glyph codes", finding["text_streams"])
        self.assertIn("portrait resource/variant pairs", finding["text_streams"])
        self.assertIn("3,389 unique streams", finding["text_streams"])
        self.assertIn("2,794 are multiline", finding["text_streams"])
        self.assertIn("100 roots", finding["root_entry_text"])
        self.assertIn("95 distinct", finding["root_entry_text"])
        self.assertIn("82 are multiline", finding["root_entry_text"])
        self.assertIn("text selector $07E1", finding["renderer_evidence"])
        self.assertIn("$9C:9358", finding["renderer_evidence"])
        self.assertIn("four 14-cell lines", finding["renderer_evidence"])
        self.assertIn("decoded passage", finding["note"])
        self.assertIn("CPU $83:E2A8", finding["note"])
        self.assertIn("sampled stale $0C37", finding["note"])

    def test_direct_dma_access_correction_is_recorded(self):
        finding = self.document["findings"]["hardware_register_access"]
        self.assertEqual(finding["status"], "confirmed_direct_access")
        self.assertEqual(finding["confidence"], "confirmed")
        self.assertIn("$2118", finding["evidence"])
        self.assertIn("not ROM bank $18", finding["note"])


class GlossaryTest(unittest.TestCase):
    """Validate the English glossary structure, terms, and consistency."""

    EXPECTED_COLUMNS = [
        "id", "category", "canonical", "aliases", "usage_notes", "status",
    ]
    ALLOWED_CATEGORIES = {
        "character", "race", "group", "place", "object", "form", "concept",
        "technique", "arc",
    }
    ALLOWED_STATUSES = {"approved"}
    PINNED_CANONICAL = {
        "character_frieza": "Frieza",
        "character_krillin": "Krillin",
        "character_tien": "Tien",
        "character_chiaotzu": "Chiaotzu",
        "character_jeice": "Jeice",
        "character_king_kai": "King Kai",
        "character_grand_elder_guru": "Grand Elder Guru",
        "character_goku": "Goku",
        "character_piccolo": "Piccolo",
        "character_vegeta": "Vegeta",
        "character_gohan": "Gohan",
        "character_raditz": "Raditz",
        "character_shenron": "Shenron",
        "character_porunga": "Porunga",
        "character_captain_ginyu": "Captain Ginyu",
        "character_burter": "Burter",
        "character_recoome": "Recoome",
        "character_guldo": "Guldo",
        "character_dende": "Dende",
        "character_nail": "Nail",
        "character_master_roshi": "Master Roshi",
        "race_saiyan": "Saiyan",
        "race_namekian": "Namekian",
        "group_ginyu_force": "Ginyu Force",
        "group_frieza_force": "Frieza Force",
        "form_great_ape": "Great Ape",
        "form_super_saiyan": "Super Saiyan",
        "arc_23rd_world_tournament": "23rd World Tournament",
        "technique_kamehameha": "Kamehameha",
        "technique_special_beam_cannon": "Special Beam Cannon",
        "technique_destructo_disc": "Destructo Disc",
        "technique_tri_beam": "Tri-Beam",
        "technique_spirit_bomb": "Spirit Bomb",
        "technique_kaioken": "Kaio-ken",
        "technique_masenko": "Masenko",
        "technique_body_change": "Body Change",
    }
    PROHIBITED_CANONICAL = {
        "Freeza", "Kuririn", "Jiece", "Tenshinhan", "Chaozu",
        "Muten Roshi", "Kame-Sen'nin", "Kamesennin",
        "Kaio", "Saiya-jin", "Oozaru", "Super Saiya-jin",
        "Super Saiyajin", "Makankosappo", "Kienzan", "Genki Dama",
        "Tenkaichi Budokai", "Planet Trade Organization",
        "Radditz", "Gurdo",
    }

    @classmethod
    def setUpClass(cls):
        path = PROJECT_ROOT / "translation" / "glossary.toml"
        with path.open("rb") as source:
            document = tomllib.load(source)
        cls.fieldnames = list(document["term"][0])
        cls.rows = document["term"]

    def test_glossary_exists(self):
        self.assertTrue(
            (PROJECT_ROOT / "translation" / "glossary.toml").is_file(),
            "glossary.toml must exist",
        )

    def test_glossary_has_expected_columns(self):
        self.assertEqual(self.fieldnames, self.EXPECTED_COLUMNS)

    def test_glossary_has_records(self):
        self.assertGreater(len(self.rows), 0)

    def test_ids_are_unique_and_valid(self):
        identifiers: set[str] = set()
        pattern = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)*")
        for row in self.rows:
            with self.subTest(id=row["id"]):
                self.assertIsNotNone(
                    pattern.fullmatch(row["id"]),
                    f"id {row['id']!r} does not match expected pattern",
                )
                self.assertNotIn(row["id"], identifiers, f"duplicate id {row['id']}")
                identifiers.add(row["id"])

    def test_categories_are_in_allowed_set(self):
        for row in self.rows:
            with self.subTest(id=row["id"]):
                self.assertIn(
                    row["category"],
                    self.ALLOWED_CATEGORIES,
                    f"{row['id']} has unexpected category {row['category']!r}",
                )

    def test_statuses_are_approved(self):
        for row in self.rows:
            with self.subTest(id=row["id"]):
                self.assertIn(
                    row["status"],
                    self.ALLOWED_STATUSES,
                    f"{row['id']} has unexpected status {row['status']!r}",
                )

    def test_canonical_forms_are_unique_within_category(self):
        canonicals: dict[tuple[str, str], str] = {}
        for row in self.rows:
            key = (row["category"], row["canonical"])
            self.assertNotIn(
                key,
                canonicals,
                f"duplicate canonical {row['canonical']!r} in {row['category']}",
            )
            canonicals[key] = row["id"]

    def test_pinned_canonical_terms_are_correct(self):
        by_id = {row["id"]: row for row in self.rows}
        for identifier, expected in self.PINNED_CANONICAL.items():
            with self.subTest(id=identifier):
                self.assertIn(identifier, by_id, f"glossary missing {identifier}")
                self.assertEqual(
                    by_id[identifier]["canonical"],
                    expected,
                    f"{identifier} canonical must be {expected!r}",
                )

    def test_canonical_column_has_no_prohibited_spellings(self):
        for row in self.rows:
            for prohibited in self.PROHIBITED_CANONICAL:
                with self.subTest(id=row["id"], prohibited=prohibited):
                    self.assertNotEqual(
                        row["canonical"],
                        prohibited,
                        f"{row['id']} uses prohibited canonical {prohibited!r}",
                    )

    def test_existing_patches_do_not_use_prohibited_spellings(self):
        rows = TranslationManifestTest.load_patches()
        for row in rows:
            text = row.get("english", "")
            for prohibited in self.PROHIBITED_CANONICAL:
                with self.subTest(id=row["id"], prohibited=prohibited):
                    self.assertNotIn(
                        prohibited,
                        text,
                        f"{row['id']} contains prohibited spelling {prohibited!r}",
                    )


if __name__ == "__main__":
    unittest.main()
