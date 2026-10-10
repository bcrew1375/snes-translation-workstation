"""Tests for the bounded mesen-agent wrapper; no emulator or commercial ROM required."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]


def load_tool():
    path = ROOT / "tools" / "bin" / "snes-automate"
    loader = importlib.machinery.SourceFileLoader("snes_automate", str(path))
    spec = importlib.util.spec_from_loader("snes_automate", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class SnesAutomateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = load_tool()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="snes-automate-test-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.rom = self.directory / "input.sfc"
        self.rom.write_bytes(b"synthetic-rom")
        self.backend = self.directory / "mesen-agent"
        self.backend.write_text("backend", encoding="utf-8")
        self.backend.chmod(0o755)

    def test_repository_output_must_be_ignored(self):
        with self.assertRaisesRegex(ValueError, "build/ or projects/<id>/local"):
            self.tool.require_safe_artifact_dir(ROOT / "evidence")
        self.assertEqual(
            self.tool.require_safe_artifact_dir(ROOT / "build" / "evidence"),
            ROOT / "build" / "evidence",
        )

    def test_missing_default_backend_recommends_rebuilding_container(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(
            self.tool.shutil, "which", return_value=None
        ):
            with self.assertRaisesRegex(ValueError, "rebuild the devcontainer"):
                self.tool.backend_path()

    def test_missing_explicit_backend_identifies_environment_override(self):
        with patch.dict(os.environ, {"MESEN_AGENT": "/missing/mesen-agent"}), patch.object(
            self.tool.shutil, "which", return_value=None
        ):
            with self.assertRaisesRegex(ValueError, "configured by MESEN_AGENT"):
                self.tool.backend_path()

    def test_revision_prefers_installed_sidecar(self):
        (self.directory / "mesen-agent.revision").write_text("pinned-revision\n")
        self.assertEqual(self.tool.revision_for(self.backend), "pinned-revision")

    def test_revision_uses_git_checkout_for_temporary_build(self):
        checkout = self.directory / "checkout"
        backend = checkout / "bin" / "linux-x64" / "Release" / "mesen-agent"
        backend.parent.mkdir(parents=True)
        backend.write_text("backend", encoding="utf-8")
        (checkout / ".git").mkdir()
        with patch.object(
            self.tool.subprocess, "check_output", return_value="temporary-revision\n"
        ) as check_output:
            self.assertEqual(self.tool.revision_for(backend), "temporary-revision")
        check_output.assert_called_once_with(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            stderr=self.tool.subprocess.DEVNULL,
            text=True,
            timeout=5,
        )

    def test_command_has_isolated_home_and_bounds(self):
        args = self.tool.parser().parse_args(
            [
                str(self.rom),
                "--artifact-dir", str(self.directory / "artifacts"),
                "--frames", "12",
                "--timeout", "9",
                "--input", "0:start@0-2",
                "--breakpoint", "SnesMemory:0x008000:x",
                "--read-memory", "SnesWorkRam:0x10:1",
                "--pc",
                "--screenshot",
            ]
        )
        command = self.tool.build_command(
            args, self.backend, self.rom, self.directory / "artifacts", []
        )
        self.assertEqual(command[0:2], [str(self.backend), str(self.rom)])
        self.assertIn(str(self.directory / "artifacts" / "home"), command)
        self.assertIn("0:start@0-2", command)
        self.assertIn("SnesMemory:0x008000:x", command)
        self.assertIn(str(self.directory / "artifacts" / "frame.png"), command)

    def test_successful_run_writes_reproducibility_metadata(self):
        artifact_dir = self.directory / "artifacts"

        def fake_run(command, *, stdout, stderr, check, timeout):
            self.assertFalse(check)
            self.assertEqual(timeout, 10)
            stdout.write(
                b'{"event":"loaded","console":"Snes","cpu":"Snes"}\n'
                b'{"event":"summary","ok":true,"reason":"frame_limit"}\n'
            )
            return type("Completed", (), {"returncode": 0})()

        with patch.dict(os.environ, {"MESEN_AGENT": str(self.backend)}), patch.object(
            self.tool.subprocess, "run", side_effect=fake_run
        ):
            result = self.tool.main(
                [
                    str(self.rom),
                    "--artifact-dir", str(artifact_dir),
                    "--frames", "1",
                    "--timeout", "5",
                ]
            )
        self.assertEqual(result, 0)
        metadata = json.loads((artifact_dir / "metadata.json").read_text())
        self.assertTrue(metadata["trustworthy"])
        self.assertEqual(metadata["rom"]["size"], len(b"synthetic-rom"))
        self.assertEqual(metadata["summary"]["reason"], "frame_limit")

    def test_missing_summary_is_not_trusted(self):
        artifact_dir = self.directory / "failed"

        def fake_run(command, *, stdout, stderr, check, timeout):
            stdout.write(b'{"event":"loaded","console":"Snes"}\n')
            return type("Completed", (), {"returncode": 0})()

        with patch.dict(os.environ, {"MESEN_AGENT": str(self.backend)}), patch.object(
            self.tool.subprocess, "run", side_effect=fake_run
        ):
            result = self.tool.main(
                [str(self.rom), "--artifact-dir", str(artifact_dir), "--timeout", "5"]
            )
        self.assertEqual(result, 1)
        self.assertFalse(json.loads((artifact_dir / "metadata.json").read_text())["trustworthy"])


if __name__ == "__main__":
    unittest.main()