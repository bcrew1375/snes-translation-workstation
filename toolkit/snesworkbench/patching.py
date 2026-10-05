"""Generic validation and bounded-ROM patching primitives."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .errors import WorkstationError


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_rom(
    data: bytes,
    *,
    size: int | None,
    digest: str | None,
    description: str,
) -> None:
    """Check a ROM against expected identity, skipping absent expectations.

    An output ROM whose size/digest are not yet recorded passes through this
    check; the input ROM always supplies both, so an unsupported source image
    is still rejected.
    """
    actual_size = len(data)
    actual_digest = sha256(data)
    problems = []
    if size is not None and actual_size != size:
        problems.append(f"expected {size} bytes")
    if digest is not None and actual_digest != digest:
        problems.append(f"expected SHA-256 {digest}")
    if problems:
        raise WorkstationError(
            f"unsupported {description}: {'; '.join(problems)}, "
            f"got {actual_size} bytes with SHA-256 {actual_digest}"
        )


def fixed_slot(data: bytes, size: int, name: str, *, fill: int = 0) -> bytes:
    if not 0 <= fill <= 0xFF:
        raise WorkstationError("slot fill must be a byte")
    if len(data) > size:
        raise WorkstationError(f"{name} is {len(data)} bytes; slot is {size}")
    return data.ljust(size, bytes((fill,)))


def bounded_write(rom: bytearray, offset: int, data: bytes, name: str) -> None:
    if offset < 0 or offset + len(data) > len(rom):
        raise WorkstationError(
            f"{name} write at ROM ${offset:05X} with length {len(data)} exceeds ROM"
        )
    rom[offset : offset + len(data)] = data


def changed_offsets(before: bytes, after: bytes) -> frozenset[int]:
    if len(before) != len(after):
        raise WorkstationError(
            f"output size changed from {len(before)} bytes to {len(after)} bytes"
        )
    return frozenset(index for index, values in enumerate(zip(before, after)) if values[0] != values[1])


def validate_changed_scope(changed: frozenset[int], allowed: set[int]) -> None:
    outside = changed - allowed
    if outside:
        first = min(outside)
        raise WorkstationError(f"build changed an unapproved byte at ROM ${first:05X}")


def write_snes_checksum(rom: bytearray, checksum_offset: int) -> None:
    """Write complement/checksum fields at an already-resolved SNES header offset."""
    if checksum_offset < 2 or checksum_offset + 2 > len(rom):
        raise WorkstationError("SNES checksum field exceeds ROM")
    rom[checksum_offset-2:checksum_offset+2] = b"\x00\x00\x00\x00"
    checksum = sum(rom) & 0xFFFF
    complement = checksum ^ 0xFFFF
    rom[checksum_offset-2:checksum_offset] = complement.to_bytes(2, "little")
    rom[checksum_offset:checksum_offset+2] = checksum.to_bytes(2, "little")


@dataclass(frozen=True)
class BuildResult:
    data: bytes
    sha256: str
    changed_offsets: frozenset[int]
    metadata: dict[str, object]