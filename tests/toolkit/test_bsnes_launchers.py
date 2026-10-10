"""Tests for bsnes-plus launch recovery; no emulator or commercial ROM required."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class BsnesLauncherTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bsnes-launcher-test-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.home = self.directory / "home"
        self.config = self.home / ".bsnes" / "bsnes-qt.cfg"
        self.config.parent.mkdir(parents=True)
        self.bin = self.directory / "bin"
        self.bin.mkdir()
        self.capture = self.directory / "capture.txt"
        emulator = self.bin / "bsnes-plus"
        emulator.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n%s\\n' \"$*\" \"${LD_PRELOAD-}\" >\"$BSNES_TEST_CAPTURE\"\n",
            encoding="utf-8",
        )
        emulator.chmod(0o755)
        self.rom = self.directory / "synthetic.sfc"
        self.rom.write_bytes(b"synthetic-rom")

    def run_launcher(
        self, name: str, *, unthrottled: bool = True
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "HOME": str(self.home),
                "PATH": f"{self.bin}:{environment['PATH']}",
                "BSNES_TEST_CAPTURE": str(self.capture),
            }
        )
        if unthrottled:
            environment["BSNES_UNTHROTTLED"] = "1"
        else:
            environment.pop("BSNES_UNTHROTTLED", None)
        return subprocess.run(
            [str(ROOT / "tools" / "bin" / name), str(self.rom)],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

    def test_disabled_video_and_stale_crash_marker_are_repaired(self):
        for launcher in ("snes-run", "snes-debug"):
            with self.subTest(launcher=launcher):
                self.config.write_text(
                    'system.video = "None"\n'
                    'system.audio = "None"\n'
                    'system.input = "None"\n'
                    'system.crashedOnLastRun = true\n',
                    encoding="utf-8",
                )
                result = self.run_launcher(launcher)
                self.assertEqual(result.returncode, 0, result.stderr)
                settings = self.config.read_text(encoding="utf-8")
                self.assertIn('system.video = "OpenGL"', settings)
                self.assertIn("system.crashedOnLastRun = false", settings)
                self.assertIn('system.audio = "None"', settings)
                self.assertIn('system.input = "None"', settings)
                self.assertIn("selected bsnes-plus OpenGL video output", result.stderr)
                self.assertEqual(self.capture.read_text().splitlines()[0], str(self.rom))

    def test_paced_launch_replaces_non_gl_driver(self):
        original = (
            'system.video = "Qt-Raster"\n'
            'system.crashedOnLastRun = true\n'
        )
        self.config.write_text(original, encoding="utf-8")
        result = self.run_launcher("snes-run", unthrottled=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.config.read_text(encoding="utf-8"),
            'system.video = "OpenGL"\n'
            'system.crashedOnLastRun = false\n',
        )
        self.assertIn("required for frame pacing", result.stderr)

    def test_unthrottled_launch_preserves_non_gl_driver(self):
        original = (
            'system.video = "Qt-Raster"\n'
            'system.crashedOnLastRun = false\n'
        )
        self.config.write_text(original, encoding="utf-8")
        result = self.run_launcher("snes-run", unthrottled=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.config.read_text(encoding="utf-8"), original)
        self.assertEqual(result.stderr, "")

    def test_unthrottled_opt_out_does_not_set_preload(self):
        self.config.write_text('system.video = "OpenGL"\n', encoding="utf-8")
        result = self.run_launcher("snes-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.capture.read_text().splitlines(), [str(self.rom), ""])

    def test_default_launch_preloads_frame_pacer(self):
        self.config.write_text('system.video = "OpenGL"\n', encoding="utf-8")
        result = self.run_launcher("snes-run", unthrottled=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        command, preload = self.capture.read_text().splitlines()
        self.assertEqual(command, str(self.rom))
        self.assertTrue(preload.endswith("/snes-workstation/bsnes-glx-throttle.so"))
        self.assertTrue(Path(preload).is_file())

    def test_direct_bsnes_plus_invocation_is_paced_and_forwards_arguments(self):
        self.config.write_text('system.video = "OpenGL"\n', encoding="utf-8")
        environment = os.environ.copy()
        environment.update(
            {
                "HOME": str(self.home),
                "PATH": f"{ROOT / 'tools' / 'bin'}:{self.bin}:{environment['PATH']}",
                "BSNES_TEST_CAPTURE": str(self.capture),
            }
        )
        environment.pop("BSNES_UNTHROTTLED", None)
        result = subprocess.run(
            ["bsnes-plus", "--flag", str(self.rom)],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        command, preload = self.capture.read_text().splitlines()
        self.assertEqual(command, f"--flag {self.rom}")
        self.assertTrue(preload.endswith("/snes-workstation/bsnes-glx-throttle.so"))


if __name__ == "__main__":
    unittest.main()