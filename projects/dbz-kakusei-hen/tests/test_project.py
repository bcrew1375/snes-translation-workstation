"""Project metadata checks that do not require the original ROM.

The ROM-independent test suite in ``tests/toolkit`` runs everywhere. These
checks confirm that the project descriptor is well-formed and internally
consistent, so a malformed ``project.toml`` is caught even without the
copyrighted input present.
"""

import tomllib
import unittest
from pathlib import Path

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

    def test_translated_rom_identity_is_optional(self):
        """No translated ROM exists yet, so it need not declare one."""
        output = self.data["output"]
        self.assertEqual(output.get("size"), None)
        self.assertEqual(output.get("sha256"), None)
        self.assertTrue(output["default_path"].endswith("translated.sfc"))

    def test_analysis_manifest_exists(self):
        manifest = PROJECT_ROOT / self.data["manifests"]["analysis"]
        self.assertTrue(manifest.is_file(), f"missing analysis manifest {manifest}")


class AnalysisManifestTest(unittest.TestCase):
    def test_regions_are_non_overlapping_and_in_range(self):
        import json

        document = json.loads(
            (PROJECT_ROOT / "analysis" / "project.json").read_text(encoding="utf-8")
        )
        rom_size = document["rom"]["size_bytes"]
        regions = document["regions"]
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
        import json

        document = json.loads(
            (PROJECT_ROOT / "analysis" / "project.json").read_text(encoding="utf-8")
        )
        for region in document["regions"]:
            self.assertNotEqual(region["type"], "unknown")


if __name__ == "__main__":
    unittest.main()