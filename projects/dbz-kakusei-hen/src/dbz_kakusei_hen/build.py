"""Build entry point for the Kakusei Hen English translation."""

from __future__ import annotations

from snesworkbench.patching import BuildResult, changed_offsets, sha256, write_snes_checksum

from .opening_translation import OPENING_TEXTS, apply_opening_translation


def build(original: bytes, project) -> BuildResult:
    """Apply the validated complete automatic-opening translation."""

    translated_bytes = bytearray(apply_opening_translation(original))
    write_snes_checksum(translated_bytes, 0x7FDE)
    translated = bytes(translated_bytes)
    return BuildResult(
        data=translated,
        sha256=sha256(translated),
        changed_offsets=changed_offsets(original, translated),
        metadata={
            "translated": True,
            "opening_selectors": [f"${record.selector:04X}" for record in OPENING_TEXTS],
            "opening_lines": [list(record.lines) for record in OPENING_TEXTS],
        },
    )