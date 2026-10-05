"""Byte-faithful Asar assembly of a ROM, used to prove a byte-identical rebuild.

This module exists to satisfy one project invariant: the ROM must be
reproducible byte-for-byte from source. It deliberately makes no attempt to
interpret CPU, data, or graphics -- every byte is emitted verbatim so that a
successful `MATCH` proves only that the assembly pipeline is lossless, never
that the disassembly is semantically correct (see .clinerules sections 7, 8
and 28).

Four Asar behaviours were verified experimentally and are encoded here as
invariants rather than rediscovered by trial and error:

1. Asar requires an explicit mapping directive (``lorom`` / ``hirom``). Without
   it, ``org $7FC0`` fails with ``Esnes_address_doesnt_map_to_rom``.
2. Asar 1.91's ``incbin`` accepts **no** offset or length arguments; passing
   any yields ``Egarbage_near_quoted_string``. The ROM must therefore be split
   into one chunk per bank.
3. A repeated ``org $008000`` does not advance to the next bank -- it resets to
   bank 0. Each bank needs an explicit full address.
4. Asar prepends a 512-byte copier header to its output, so the rebuilt image
   is 512 bytes longer than the input and the header must be stripped.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .errors import WorkstationError

ASAR = "asar"

#: Asar always writes this many bytes of copier header in front of the image.
ASAR_COPIER_HEADER = 0x200


@dataclass(frozen=True)
class BankPlan:
    """One contiguous run of the ROM addressed by a single Asar ``org``."""

    index: int
    file_offset: int
    size: int
    org_address: int


def plan_banks(rom_size: int, mapping: str) -> tuple[BankPlan, ...]:
    """Split a ROM into one Asar-addressable bank per ``org`` statement.

    For LoROM a bank is $8000 bytes and file offset N maps to bank N/0x8000 at
    CPU $8000. For HiROM a bank is $10000 bytes and file offset N maps to bank
    $80+(N/0x10000) at CPU $0000, because the $8000-$FFFF half of low bank
    numbers is a WRAM mirror rather than cartridge ROM.
    """
    if rom_size <= 0:
        raise WorkstationError("ROM size must be positive")
    mapping = mapping.lower()
    plans: list[BankPlan] = []
    if mapping == "lorom":
        step = 0x8000
        for index, offset in enumerate(range(0, rom_size, step)):
            size = min(step, rom_size - offset)
            plans.append(BankPlan(index, offset, size, (index << 16) | 0x8000))
        return tuple(plans)
    if mapping == "hirom":
        step = 0x10000
        for index, offset in enumerate(range(0, rom_size, step)):
            size = min(step, rom_size - offset)
            plans.append(BankPlan(index, offset, size, 0x800000 | (index << 16)))
        return tuple(plans)
    raise WorkstationError(f"{mapping} is not supported for byte-faithful assembly")


def emit_faithful_asm(
    rom_path: Path,
    chunk_directory: Path,
    *,
    mapping: str,
    comment_header: str = "",
) -> Path:
    """Write per-bank chunk files plus the Asar source that embeds them."""
    rom = rom_path.read_bytes()
    plans = plan_banks(len(rom), mapping)
    chunk_directory.mkdir(parents=True, exist_ok=True)

    lines = [f"{mapping.lower()}\n"]
    if comment_header:
        lines.extend(f"; {line}" for line in comment_header.splitlines())
        lines.append("")
    for plan in plans:
        chunk_name = f"bank_{plan.index:02X}.bin"
        chunk = rom[plan.file_offset : plan.file_offset + plan.size]
        (chunk_directory / chunk_name).write_bytes(chunk)
        lines.append(f"; bank {plan.index:02X}: ROM ${plan.file_offset:06X}"
                     f"-${plan.file_offset + plan.size - 1:06X}")
        lines.append(f"org ${plan.org_address:06X}")
        lines.append(f'incbin "{chunk_name}"')
        lines.append("")

    asm_path = chunk_directory / "faithful.asm"
    asm_path.write_text("\n".join(lines), encoding="utf-8")
    return asm_path


def assemble(asm_path: Path, output_path: Path, *, workdir: Path) -> bytes:
    """Run Asar and return the ROM body with Asar's copier header stripped."""
    result = subprocess.run(
        [ASAR, "--no-title-check", "--fix-checksum=off",
         str(asm_path), str(output_path)],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise WorkstationError(
            f"asar failed (exit {result.returncode}): "
            f"{(result.stdout + result.stderr).strip()[:500]}"
        )
    if not output_path.exists():
        raise WorkstationError("asar reported success but produced no output")
    data = output_path.read_bytes()
    if len(data) < ASAR_COPIER_HEADER:
        raise WorkstationError("asar output is smaller than its copier header")
    return data[ASAR_COPIER_HEADER:]


def rebuild_faithful(
    rom_path: Path,
    *,
    mapping: str,
    workdir: Path | None = None,
    comment_header: str = "",
) -> bytes:
    """Assemble the ROM back from its own bytes and return the rebuilt body.

    ``workdir`` is created if absent and is expected to be a git-ignored
    scratch directory; the per-bank chunks it holds are ROM-derived.
    """
    owned = workdir is None
    directory = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="snes-fidelity-"))
    try:
        directory.mkdir(parents=True, exist_ok=True)
        chunk_directory = directory / "banks"
        asm_path = emit_faithful_asm(
            rom_path, chunk_directory, mapping=mapping, comment_header=comment_header
        )
        return assemble(asm_path, directory / "rebuilt.smc", workdir=chunk_directory)
    finally:
        if owned:
            shutil.rmtree(directory, ignore_errors=True)