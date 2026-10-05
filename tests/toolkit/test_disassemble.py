"""Disassembly-wrapper tests.

Synthetic data only, so these run without a user-supplied ROM (.clinerules
sections 30 and 31). They lock in two bugs that were found and fixed while
bringing the vendored Asar disassembler up:

* staging a headerless ROM as ``.smc`` makes Asar assume a 512-byte copier
  header, silently shifting every read by $200 while still exiting 0;
* the LoROM bank address is ``bank<<16 | $8000``, not ``$8000 + bank*$8000``.
  The wrong form lands in the $0000-$7FFF WRAM mirror and reads back as $00,
  which Asar cannot resolve to an opcode macro.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HAVE_ASAR = shutil.which("asar") is not None

sys.path.insert(0, str(ROOT / "toolkit"))
from snesworkbench.errors import WorkstationError  # noqa: E402


def load_tool():
    """Import tools/bin/snes-disassemble, which is not an importable package."""
    path = ROOT / "tools" / "bin" / "snes-disassemble"
    spec = importlib.util.spec_from_loader(
        "snes_disassemble", importlib.machinery.SourceFileLoader("snes_disassemble", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SubstituteTest(unittest.TestCase):
    """Pure text substitution; no Asar required."""

    @classmethod
    def setUpClass(cls):
        cls.tool = load_tool()

    def test_bank_address_is_bank_shifted(self):
        script = self.tool.VENDOR / "Extras" / "SNESASMDis.asm"
        text = script.read_text(encoding="utf-8", errors="replace")
        for bank, expected in ((0, "$008000"), (1, "$018000"), (63, "$3F8000")):
            out = self.tool.substitute(text, "lorom", (bank << 16) | 0x8000, bank, 0x8000)
            self.assertIn(f"!ROMOffset = {expected}", out)

    def test_every_config_knob_is_replaced(self):
        script = self.tool.VENDOR / "Extras" / "SNESASMDis.asm"
        text = script.read_text(encoding="utf-8", errors="replace")
        out = self.tool.substitute(text, "lorom", 0x018000, 1, 0x8000)
        self.assertIn("!ROMOffset = $018000", out)
        self.assertIn("!MaxBytes = 32768", out)
        self.assertIn("!16BitA = 0", out)
        self.assertIn("!16BitXY = 0", out)
        self.assertIn("!Bank = 01", out)

    def test_hirom_switches_the_mapping_directive(self):
        script = self.tool.VENDOR / "Extras" / "SNESASMDis.asm"
        text = script.read_text(encoding="utf-8", errors="replace")
        out = self.tool.substitute(text, "hirom", 0x800000, 0, 0x10000)
        self.assertTrue(
            any(line.strip() == "hirom" for line in out.splitlines()),
            "hirom mapping directive was not emitted",
        )


@unittest.skipUnless(HAVE_ASAR, "asar is not installed")
class DecodeTest(unittest.TestCase):
    """End-to-end decode of a synthetic ROM with known leading bytes.

    The fixtures carry a real SNES internal header (title, valid
    checksum/complement pair, reset vector) because Asar refuses to assemble
    against a ROM whose header it cannot validate.
    """

    HEADER_OFFSET = 0x7FC0

    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix="disasm-test-"))
        self.addCleanup(shutil.rmtree, self.directory, True)
        self.tool = load_tool()

    def _rom_with_header(self, leading: bytes, banks: int = 2) -> bytes:
        data = bytearray(banks * 0x8000)
        data[0 : len(leading)] = leading
        header = self.HEADER_OFFSET
        # The title field is exactly 21 bytes; assigning fewer resizes the
        # bytearray and silently truncates the fixture.
        data[header : header + 21] = b"FIDELITYTESTROM".ljust(21, b"\x00")
        self.assertEqual(len(data), banks * 0x8000)
        data[header + 0x15] = 0x00  # LoROM, slow ROM
        # Asar trusts the ROM size code and rejects reads past it, so a fixture
        # that omits it is treated as 32 KiB and bank 1 fails to decode.
        data[header + 0x17] = 0x02  # 128 KiB
        data[header + 0x3C : header + 0x3E] = (0x8000).to_bytes(2, "little")
        checksum = sum(data) & 0xFFFF
        data[header + 0x1C : header + 0x1E] = (checksum ^ 0xFFFF).to_bytes(2, "little")
        data[header + 0x1E : header + 0x20] = checksum.to_bytes(2, "little")
        return bytes(data)

    def _decode_first(self, data: bytes, bank: int = 0) -> str:
        rom = self.directory / "input.sfc"
        rom.write_bytes(data)
        workdir = self.directory / f"work{bank}"
        workdir.mkdir(exist_ok=True)
        shutil.copyfile(rom, workdir / "ROM.sfc")
        script = (self.tool.VENDOR / "Extras" / "SNESASMDis.asm").read_text(
            encoding="utf-8", errors="replace"
        )
        text = self.tool.disassemble_bank(
            script, "lorom", bank, workdir, 4, "ROM.sfc"
        )
        instructions = [l.strip() for l in text.splitlines() if l.startswith("\t")]
        return instructions[0] if instructions else ""

    def test_lorom_decodes_from_offset_zero(self):
        # $78 SEI, $D8 CLD, $18 CLC, $FB XCE -- the canonical reset preamble.
        self.assertEqual(self._decode_first(self._rom_with_header(bytes([0x78, 0xD8, 0x18, 0xFB]))), "SEI")

    def test_second_bank_reads_the_second_bank(self):
        data = bytearray(self._rom_with_header(bytes([0x78, 0xD8, 0x18, 0xFB])))
        data[0x8000] = 0x60  # RTS -- bank 1 must start decoding here
        self.assertEqual(self._decode_first(bytes(data), bank=1), "RTS")

    def test_smc_staging_corrupts_the_decode(self):
        """Regression: a .smc staging must not be used.

        Asar assumes a ``.smc`` carries a 512-byte copier header, so it reads
        $200 past where the data actually is. With a real ROM that silently
        yields plausible but wrong mnemonics; with this fixture it fails
        outright. Either way the correct suffix must be used.
        """
        data = bytearray(self._rom_with_header(bytes([0x78, 0xD8, 0x18, 0xFB])))
        data[0x200] = 0x60  # decoy: what a .smc staging would wrongly reach
        rom = self.directory / "input.sfc"
        rom.write_bytes(bytes(data))
        workdir = self.directory / "work_hazard"
        workdir.mkdir(exist_ok=True)
        shutil.copyfile(rom, workdir / "ROM.sfc")
        script = (self.tool.VENDOR / "Extras" / "SNESASMDis.asm").read_text(
            encoding="utf-8", errors="replace"
        )

        good = self.tool.disassemble_bank(script, "lorom", 0, workdir, 4, "ROM.sfc")
        self.assertIn("SEI", good)

        try:
            bad = self.tool.disassemble_bank(script, "lorom", 0, workdir, 4, "ROM.smc")
        except WorkstationError as error:
            self.assertIn("bank 00", str(error))
        else:
            # If it assembled, the first instruction must not be SEI, because
            # the read is displaced by $200.
            self.assertNotIn("SEI", bad)


if __name__ == "__main__":
    unittest.main()