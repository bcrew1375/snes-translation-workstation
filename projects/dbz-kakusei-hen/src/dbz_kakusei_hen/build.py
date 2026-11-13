"""Build entry point for the Kakusei Hen English translation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from snesworkbench.patching import BuildResult, changed_offsets, sha256, write_snes_checksum

from .allocator import FreeSpaceRegion
from .battle_text_translation import (
    BattleTextRecord,
    apply_battle_text_translation,
    load_battle_text_records,
)
from .fixed_resource_translation import (
    FixedResourceRecord,
    apply_fixed_resource_translation,
    load_fixed_resource_records,
)
from .hud_translation import HudTextRecord, apply_hud_translation, load_hud_text_records
from .name_entry_translation import (
    NameEntryRecord,
    apply_name_entry_translation,
    load_name_entry_records,
)
from .opening_translation import OPENING_TEXTS
from .title_menu_translation import (
    TitleMenuRecord,
    apply_title_menu_translation,
    load_title_menu_records,
)
from .translation_build import (
    TranslationRecord,
    build_translation,
    load_reviewed_free_regions,
    load_translation_manifests,
)


@dataclass(frozen=True)
class TranslationCatalog:
    """Validated translation inputs loaded exactly once for one operation."""

    dialogue: tuple[TranslationRecord, ...]
    free_regions: tuple[FreeSpaceRegion, ...]
    menu: tuple[TitleMenuRecord, ...]
    name_entry: tuple[NameEntryRecord, ...]
    fixed_resources: tuple[FixedResourceRecord, ...]
    battle_text: tuple[BattleTextRecord, ...]
    hud: tuple[HudTextRecord, ...]


def _manifest_paths(project) -> dict[str, Path]:
    if project is not None:
        return {name: Path(path) for name, path in project.manifests.items()}
    root = Path(__file__).resolve().parents[2]
    return {
        "patches": root / "translation" / "patches",
        "ranges": root / "translation" / "ranges",
        "menu": root / "translation" / "menu.toml",
        "name_entry": root / "translation" / "name_entry.toml",
        "choices": root / "translation" / "choices.toml",
        "battle_text": root / "translation" / "battle_text.toml",
        "hud": root / "translation" / "hud.toml",
    }


def load_translation_catalog(project) -> TranslationCatalog:
    """Load and validate every translation manifest once."""

    paths = _manifest_paths(project)
    return TranslationCatalog(
        dialogue=tuple(load_translation_manifests(paths["patches"])),
        free_regions=tuple(load_reviewed_free_regions(paths["ranges"])),
        menu=tuple(load_title_menu_records(paths["menu"])),
        name_entry=tuple(load_name_entry_records(paths["name_entry"])),
        fixed_resources=tuple(load_fixed_resource_records(paths["choices"])),
        battle_text=tuple(load_battle_text_records(paths["battle_text"])),
        hud=tuple(load_hud_text_records(paths["hud"])),
    )


def summarize(project) -> dict[str, object]:
    """Return concise DBZ-specific facts for the generic project summary."""

    catalog = load_translation_catalog(project)
    return {
        "implemented_records": {
            "command_08": sum(record.status == "implemented" for record in catalog.dialogue),
            "title_menu": sum(record.status == "implemented" for record in catalog.menu),
            "name_entry": sum(record.status == "implemented" for record in catalog.name_entry),
            "fixed_resources": sum(
                record.status == "implemented" for record in catalog.fixed_resources
            ),
            "battle_text": sum(record.status == "implemented" for record in catalog.battle_text),
            "battle_hud": sum(record.status == "implemented" for record in catalog.hud),
        },
        "dialogue_line_limits": {"portrait_free": 28, "portrait": 21},
        "documentation": "translation/README.md",
    }


def build(original: bytes, project):
    """Build from tracked manifests through the validated generic text path."""

    catalog = load_translation_catalog(project)
    result = build_translation(original, list(catalog.dialogue), list(catalog.free_regions))
    translated = apply_fixed_resource_translation(
        original, result.data, list(catalog.fixed_resources)
    )
    translated = apply_title_menu_translation(original, translated, list(catalog.menu))
    translated = apply_name_entry_translation(original, translated, list(catalog.name_entry))
    translated = apply_battle_text_translation(original, translated, list(catalog.battle_text))
    translated = bytearray(apply_hud_translation(original, translated, list(catalog.hud)))
    write_snes_checksum(translated, 0x7FDE)
    data = bytes(translated)
    metadata = dict(result.metadata)
    metadata.update(
        {
            "opening_selectors": [f"${record.selector:04X}" for record in OPENING_TEXTS],
            "opening_lines": [list(record.lines) for record in OPENING_TEXTS],
            "title_menu_lines": [
                record.english.split("\n")
                for record in catalog.menu
                if record.status == "implemented"
            ],
            "name_entry_lines": [
                record.english.split("\n")
                for record in catalog.name_entry
                if record.status == "implemented" and record.record_type == "fixed_text"
            ],
            "name_entry_defaults": next(
                record.english.split("\n")
                for record in catalog.name_entry
                if record.status == "implemented" and record.record_type == "default_names"
            ),
            "fixed_labels": {
                record.id: record.english
                for record in catalog.fixed_resources
                if record.status == "implemented" and record.record_type == "fixed_label"
            },
            "opening_choices": {
                record.button: record.english
                for record in catalog.fixed_resources
                if record.status == "implemented"
                and record.id in {"tournament_quiz_x", "tournament_quiz_y", "tournament_quiz_b"}
            },
            "fixed_options": {
                record.id: record.english
                for record in catalog.fixed_resources
                if record.status == "implemented" and record.record_type == "option"
            },
            "battle_text": {
                record.id: {
                    "path": record.path,
                    "speaker": record.speaker,
                    "resource": f"${record.resource_id:04X}",
                    "lines": list(record.english),
                }
                for record in catalog.battle_text
                if record.status == "implemented"
            },
            "battle_hud": {
                record.id: record.english
                for record in catalog.hud
                if record.status == "implemented"
            },
        }
    )
    return BuildResult(
        data=data,
        sha256=sha256(data),
        changed_offsets=changed_offsets(original, data),
        metadata=metadata,
    )
