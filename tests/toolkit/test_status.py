"""Generic project-status and concise-summary tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from snesworkbench.cli import _format_summary, _summary, main
from snesworkbench.errors import WorkstationError
from snesworkbench.project import ProjectConfig, RomConfig
from snesworkbench.status import load_project_status, status_to_dict


VALID_STATUS = """\
schema_version = 1
phase = "text_discovery"
summary = "Text encoding is understood; pointer discovery continues."

[[milestones]]
id = "font_format"
status = "complete"
summary = "Font layout confirmed."

[[milestones]]
id = "pointer_tables"
status = "partial"
summary = "Two pointer-table families remain."

[[unknowns]]
id = "compression"
summary = "Some streams may be compressed."
priority = "medium"

[[recommended_tasks]]
id = "trace_stream"
summary = "Trace one unresolved stream."
requires_rom = true
requires_runtime = true
"""


class ProjectStatusTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="snes-status-test-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def write(self, text: str = VALID_STATUS) -> Path:
        path = self.root / "status.toml"
        path.write_text(text, encoding="utf-8")
        return path

    def test_valid_status_round_trips_to_json_data(self):
        status = load_project_status(self.write())
        self.assertEqual(status.phase, "text_discovery")
        self.assertEqual([item.status for item in status.milestones], ["complete", "partial"])
        data = status_to_dict(status)
        self.assertEqual(data["recommended_tasks"][0]["requires_runtime"], True)

    def test_invalid_milestone_status_is_rejected(self):
        path = self.write(VALID_STATUS.replace('status = "partial"', 'status = "done"'))
        with self.assertRaisesRegex(WorkstationError, "invalid status"):
            load_project_status(path)

    def test_duplicate_ids_are_rejected_within_a_section(self):
        duplicate = VALID_STATUS.replace('id = "pointer_tables"', 'id = "font_format"')
        with self.assertRaisesRegex(WorkstationError, "repeats id"):
            load_project_status(self.write(duplicate))


class ProjectSummaryTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="snes-summary-test-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        status_path = self.root / "status.toml"
        status_path.write_text(VALID_STATUS, encoding="utf-8")
        self.project = ProjectConfig(
            root=self.root,
            identifier="synthetic",
            name="Synthetic Project",
            platform="snes",
            adapter="synthetic.build",
            source_directory=self.root,
            input=RomConfig(self.root / "rom" / "original.sfc", 4, "a" * 64),
            output=RomConfig(self.root / "build" / "translated.sfc", 4, "b" * 64),
            manifests={"status": status_path, "missing": self.root / "missing.tsv"},
            approved_ranges=(),
        )

    def test_summary_is_concise_and_accepts_adapter_details(self):
        adapter = SimpleNamespace(summarize=lambda project: {"translated_records": 12})
        with patch("snesworkbench.cli.load_adapter", return_value=adapter):
            summary = _summary(self.project)
        self.assertEqual(summary["manifests"], {"present": 1, "total": 2})
        self.assertEqual(summary["project_details"]["translated_records"], 12)
        rendered = _format_summary(summary)
        self.assertIn("Milestones: 1 complete, 1 partial", rendered)
        self.assertIn("Translated records: 12", rendered)
        self.assertLess(len(rendered.splitlines()), 20)

    def test_full_summary_includes_status_entries_and_requirements(self):
        with patch("snesworkbench.cli.load_adapter", return_value=SimpleNamespace()):
            rendered = _format_summary(_summary(self.project), full=True)
        self.assertIn("Milestone details:", rendered)
        self.assertIn("font_format (complete): Font layout confirmed.", rendered)
        self.assertIn("trace_stream (requires ROM, requires runtime)", rendered)

    def test_summary_rejects_non_dictionary_adapter_output(self):
        adapter = SimpleNamespace(summarize=lambda project: [])
        with patch("snesworkbench.cli.load_adapter", return_value=adapter):
            with self.assertRaisesRegex(WorkstationError, "must return a dictionary"):
                _summary(self.project)

    def test_summary_cli_supports_json(self):
        adapter = SimpleNamespace()
        with (
            patch("snesworkbench.cli.load_project", return_value=self.project),
            patch("snesworkbench.cli.load_adapter", return_value=adapter),
            redirect_stdout(StringIO()) as output,
        ):
            self.assertEqual(main(["summary", "synthetic", "--json"]), 0)
        document = json.loads(output.getvalue())
        self.assertEqual(document["id"], "synthetic")
        self.assertEqual(document["status"]["phase"], "text_discovery")

    def test_missing_status_and_missing_summary_hook_are_backward_compatible(self):
        project = ProjectConfig(
            root=self.root,
            identifier="legacy",
            name="Legacy Project",
            platform="snes",
            adapter="legacy.build",
            source_directory=self.root,
            input=self.project.input,
            output=self.project.output,
            manifests={},
            approved_ranges=(),
        )
        with patch("snesworkbench.cli.load_adapter", return_value=SimpleNamespace()):
            summary = _summary(project)
        self.assertNotIn("status", summary)
        self.assertNotIn("project_details", summary)


if __name__ == "__main__":
    unittest.main()