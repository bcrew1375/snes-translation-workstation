"""Generic build-executor safety tests using synthetic ROMs and adapters."""

import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from snesworkbench.errors import WorkstationError
from snesworkbench.patching import BuildResult, sha256
from snesworkbench.project import (
    ApprovedRange,
    ProjectConfig,
    RomConfig,
    build_project,
)


class BuildProjectTest(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix="snes-build-project-test-"))
        self.addCleanup(shutil.rmtree, self.directory, True)
        self.original = b"ABCD"
        self.input_path = self.directory / "original.sfc"
        self.output_path = self.directory / "translated.sfc"
        self.input_path.write_bytes(self.original)

    def project(self, *ranges: ApprovedRange) -> ProjectConfig:
        return ProjectConfig(
            root=self.directory,
            identifier="synthetic",
            name="Synthetic test project",
            platform="snes",
            adapter="synthetic.build",
            source_directory=self.directory,
            input=RomConfig(self.input_path, len(self.original), sha256(self.original)),
            output=RomConfig(self.output_path),
            manifests={},
            approved_ranges=tuple(ranges),
        )

    def build(
        self,
        data: bytes,
        reported: frozenset[int],
        *ranges: ApprovedRange,
        digest: str | None = None,
        write_output: bool = True,
    ) -> BuildResult:
        result = BuildResult(
            data=data,
            sha256=digest or sha256(data),
            changed_offsets=reported,
            metadata={},
        )
        adapter = SimpleNamespace(build=lambda original, project: result)
        with patch("snesworkbench.project.load_adapter", return_value=adapter):
            return build_project(
                self.project(*ranges),
                write_output=write_output,
            )

    def test_unchanged_build_succeeds_without_approved_ranges(self):
        result = self.build(self.original, frozenset(), write_output=False)
        self.assertEqual(result.data, self.original)

    def test_changed_build_fails_without_approved_ranges(self):
        with self.assertRaisesRegex(WorkstationError, "unapproved byte at ROM \\$00001"):
            self.build(b"AXCD", frozenset({1}), write_output=False)

    def test_change_inside_inclusive_approved_range_succeeds(self):
        result = self.build(
            b"AXYD",
            frozenset({1, 2}),
            ApprovedRange("translated data", 1, 2),
        )
        self.assertEqual(result.changed_offsets, frozenset({1, 2}))
        self.assertEqual(self.output_path.read_bytes(), b"AXYD")

    def test_change_outside_approved_ranges_fails(self):
        with self.assertRaisesRegex(WorkstationError, "unapproved byte at ROM \\$00002"):
            self.build(
                b"ABXD",
                frozenset({2}),
                ApprovedRange("different resource", 0, 1),
                write_output=False,
            )

    def test_adapter_cannot_omit_an_actual_changed_byte(self):
        with self.assertRaisesRegex(WorkstationError, "omitted actual byte at ROM \\$00001"):
            self.build(
                b"AXCD",
                frozenset(),
                ApprovedRange("translated data", 1, 1),
                write_output=False,
            )

    def test_adapter_cannot_report_an_unchanged_byte(self):
        with self.assertRaisesRegex(WorkstationError, "reported unchanged byte at ROM \\$00002"):
            self.build(
                b"AXCD",
                frozenset({1, 2}),
                ApprovedRange("translated data", 1, 2),
                write_output=False,
            )

    def test_output_size_change_is_rejected(self):
        with self.assertRaisesRegex(
            WorkstationError, "output size changed from 4 bytes to 5 bytes"
        ):
            self.build(
                b"ABCDE",
                frozenset(),
                ApprovedRange("translated data", 0, 4),
                write_output=False,
            )

    def test_incorrect_adapter_output_digest_is_rejected(self):
        with self.assertRaisesRegex(WorkstationError, "incorrect output SHA-256"):
            self.build(
                self.original,
                frozenset(),
                digest="0" * 64,
                write_output=False,
            )

    def test_failed_validation_leaves_existing_output_untouched(self):
        existing = b"existing translated output"
        self.output_path.write_bytes(existing)
        with self.assertRaisesRegex(WorkstationError, "unapproved byte"):
            self.build(b"AXCD", frozenset({1}))
        self.assertEqual(self.output_path.read_bytes(), existing)


if __name__ == "__main__":
    unittest.main()
