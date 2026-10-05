"""Build entry point for the Kakusei Hen project.

This is currently a **scaffold**, not a translation. It returns the original ROM
unchanged so the surrounding plumbing (input validation, output identity checks,
changed-byte auditing, manifest loading) can be exercised end to end before any
game-specific translation logic exists.

It deliberately does not modify a single byte. A pass-through build reports an
empty change set, which is the correct and honest result: it means "no
translation has been applied yet", and it must not be mistaken for a finished
English ROM.

When real translation logic lands, replace ``build`` and declare the regions it
writes in ``project.toml`` under ``[[approved_ranges]]``; the toolkit rejects any
changed byte outside those ranges.
"""

from __future__ import annotations

from snesworkbench.patching import BuildResult, sha256


def build(original: bytes, project) -> BuildResult:
    """Return the original ROM unchanged.

    Parameters
    ----------
    original:
        The validated source ROM, already checked against ``project.input``.
    project:
        The loaded :class:`~snesworkbench.project.ProjectConfig`.
    """
    return BuildResult(
        data=original,
        sha256=sha256(original),
        changed_offsets=frozenset(),
        metadata={
            "translated": False,
            "note": "scaffold build: no translation applied",
        },
    )