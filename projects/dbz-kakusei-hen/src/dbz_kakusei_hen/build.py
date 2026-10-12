"""Build entry point for the Kakusei Hen English translation."""

from __future__ import annotations

from snesworkbench.patching import BuildResult, changed_offsets, sha256, write_snes_checksum

from .fixed_resource_translation import (
    apply_fixed_resource_translation,
    load_fixed_resource_records,
)
from .name_entry_translation import apply_name_entry_translation, load_name_entry_records
from .opening_translation import OPENING_TEXTS
from .title_menu_translation import apply_title_menu_translation, load_title_menu_records
from .translation_build import (
    build_translation,
    load_reviewed_free_regions,
    load_translation_manifests,
)


def summarize(project) -> dict[str, object]:
    """Return concise DBZ-specific facts for the generic project summary."""

    records = load_translation_manifests(
        project.manifests["patches"], project.manifests["references"]
    )
    menu = load_title_menu_records(project.manifests["menu"])
    names = load_name_entry_records(project.manifests["name_entry"])
    fixed_resources = load_fixed_resource_records(project.manifests["choices"])
    return {
        "implemented_records": {
            "command_08": sum(record.status == "implemented" for record in records),
            "title_menu": sum(record.status == "implemented" for record in menu),
            "name_entry": sum(record.status == "implemented" for record in names),
            "fixed_resources": sum(record.status == "implemented" for record in fixed_resources),
        },
        "dialogue_line_limits": {"portrait_free": 28, "portrait": 21},
        "documentation": "translation/README.md",
    }


def build(original: bytes, project):
    """Build from tracked manifests through the validated generic text path."""

    if project is None:
        # Tests may call the adapter directly; resolve the project-owned files
        # without weakening normal ProjectConfig-based builds.
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        patches = root / "translation" / "patches.toml"
        references = root / "translation" / "references.toml"
        ranges = root / "translation" / "ranges.toml"
        menu = root / "translation" / "menu.toml"
        name_entry = root / "translation" / "name_entry.toml"
        fixed_resources = root / "translation" / "choices.toml"
    else:
        patches = project.manifests["patches"]
        references = project.manifests["references"]
        ranges = project.manifests["ranges"]
        menu = project.manifests["menu"]
        name_entry = project.manifests["name_entry"]
        fixed_resources = project.manifests["choices"]

    result = build_translation(
        original,
        load_translation_manifests(patches, references),
        load_reviewed_free_regions(ranges),
    )
    translated = bytearray(
        apply_name_entry_translation(
            original,
            apply_title_menu_translation(
                original,
                apply_fixed_resource_translation(
                    original,
                    result.data,
                    load_fixed_resource_records(fixed_resources),
                ),
                load_title_menu_records(menu),
            ),
            load_name_entry_records(name_entry),
        )
    )
    write_snes_checksum(translated, 0x7FDE)
    data = bytes(translated)
    metadata = dict(result.metadata)
    metadata.update(
        {
            "opening_selectors": [f"${record.selector:04X}" for record in OPENING_TEXTS],
            "opening_lines": [list(record.lines) for record in OPENING_TEXTS],
            "title_menu_lines": [
                record.english.split("\n")
                for record in load_title_menu_records(menu)
                if record.status == "implemented"
            ],
            "name_entry_lines": [
                record.english.split("\n")
                for record in load_name_entry_records(name_entry)
                if record.status == "implemented" and record.record_type == "fixed_text"
            ],
            "name_entry_defaults": next(
                record.english.split("\n")
                for record in load_name_entry_records(name_entry)
                if record.status == "implemented" and record.record_type == "default_names"
            ),
            "fixed_labels": {
                record.id: record.english
                for record in load_fixed_resource_records(fixed_resources)
                if record.status == "implemented" and record.record_type == "fixed_label"
            },
            "opening_choices": {
                record.button: record.english
                for record in load_fixed_resource_records(fixed_resources)
                if record.status == "implemented" and record.record_type == "option"
            },
        }
    )
    return BuildResult(
        data=data,
        sha256=sha256(data),
        changed_offsets=changed_offsets(original, data),
        metadata=metadata,
    )
