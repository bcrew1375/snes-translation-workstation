"""Byte-faithful assembly tests.

These use synthetic ROM images rather than a copyrighted ROM so the suite runs
anywhere (.clinerules sections 30 and 31). The tamper cases exist to prove the
check can actually fail: a round-trip test that always passes proves nothing.
"""

import shutil
import unittest
from pathlib import Path

from snesworkbench.asmbuild import (
    ASAR_COPIER_HEADER,
    assemble,
    emit_faithful_asm,
    plan_banks,
    rebuild_faithful,
)
from snesworkbench.errors import WorkstationError

HAVE_ASAR = shutil.which("asar") is not None


def synthetic_lorom(banks: int = 3) -> bytes:
    """A deterministic pseudo-ROM whose bytes differ from any real game."""
    data = bytearray()
    state = 0x1234
    for _ in range(banks * 0x8000):
        state = (state * 1103515245 + 12345) & 0xFFFFFFFF
        data.append((state >> 16) & 0xFF)
    return bytes(data)


class PlanBanksTest(unittest.TestCase):
    def test_lorom_uses_32k_banks(self):
        plans = plan_banks(0x18000, "lorom")
        self.assertEqual([p.size for p in plans], [0x8000, 0x8000, 0x8000])
        self.assertEqual([p.org_address for p in plans],
                         [0x008000, 0x018000, 0x028000])

    def test_partial_final_bank_is_kept(self):
        plans = plan_banks(0x18000 + 0x1234, "lorom")
        self.assertEqual(plans[-1].size, 0x1234)

    def test_hirom_uses_64k_banks(self):
        plans = plan_banks(0x20000, "hirom")
        self.assertEqual([p.size for p in plans], [0x10000, 0x10000])
        self.assertEqual([p.org_address for p in plans], [0x800000, 0x810000])

    def test_unknown_mapping_is_rejected(self):
        with self.assertRaises(WorkstationError):
            plan_banks(0x8000, "exhirom")


@unittest.skipUnless(HAVE_ASAR, "asar is not installed")
class FaithfulAssemblyTest(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.directory = Path(tempfile.mkdtemp(prefix="fidelity-test-"))
        self.addCleanup(shutil.rmtree, self.directory, True)
        self.rom = synthetic_lorom()
        self.rom_path = self.directory / "synthetic.sfc"
        self.rom_path.write_bytes(self.rom)

    def test_round_trip_is_byte_identical(self):
        rebuilt = rebuild_faithful(self.rom_path, mapping="lorom")
        self.assertEqual(rebuilt, self.rom)

    def test_assembled_body_excludes_asar_copier_header(self):
        chunks = self.directory / "banks"
        asm = emit_faithful_asm(self.rom_path, chunks, mapping="lorom")
        raw = assemble(asm, self.directory / "out.smc", workdir=chunks)
        # The body is the ROM; the raw file carried Asar's 512-byte header.
        self.assertEqual(len(raw), len(self.rom))
        full = (self.directory / "out.smc").read_bytes()
        self.assertEqual(len(full), len(self.rom) + ASAR_COPIER_HEADER)

    def test_single_flipped_byte_is_detected(self):
        """Guards against a check that reports MATCH unconditionally."""
        chunks = self.directory / "banks"
        asm = emit_faithful_asm(self.rom_path, chunks, mapping="lorom")
        baseline = assemble(asm, self.directory / "a.smc", workdir=chunks)
        self.assertEqual(baseline, self.rom)

        chunk = chunks / "bank_01.bin"
        data = bytearray(chunk.read_bytes())
        data[0x40] ^= 0xFF
        chunk.write_bytes(bytes(data))

        tampered = assemble(asm, self.directory / "b.smc", workdir=chunks)
        differing = [
            i for i, (a, b) in enumerate(zip(self.rom, tampered)) if a != b
        ]
        self.assertEqual(differing, [0x8000 + 0x40])


if __name__ == "__main__":
    unittest.main()