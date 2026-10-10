"""Build entry point for the Kakusei Hen English translation."""

from __future__ import annotations

from .opening_translation import OPENING_TEXTS
from .translation_build import (
    build_translation,
    load_reviewed_free_regions,
    load_translation_manifests,
)


def build(original: bytes, project):
    """Build from tracked manifests through the validated generic text path."""

    if project is None:
        # Tests may call the adapter directly; resolve the project-owned files
        # without weakening normal ProjectConfig-based builds.
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        patches = root / "translation" / "patches.tsv"
        references = root / "translation" / "references.tsv"
        ranges = root / "translation" / "ranges.tsv"
    else:
        patches = project.manifests["patches"]
        references = project.manifests["references"]
        ranges = project.manifests["ranges"]

    result = build_translation(
        original,
        load_translation_manifests(patches, references),
        load_reviewed_free_regions(ranges),
    )
    result.metadata.update(
        {
            "opening_selectors": [f"${record.selector:04X}" for record in OPENING_TEXTS],
            "opening_lines": [list(record.lines) for record in OPENING_TEXTS],
        }
    )
    return result