"""Concise, reusable project-status metadata for humans and automation agents."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .errors import WorkstationError


STATUS_VALUES = frozenset({"planned", "in_progress", "partial", "blocked", "complete"})
IDENTIFIER = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)*")


@dataclass(frozen=True)
class StatusItem:
    """One current milestone, unknown, or recommended task."""

    id: str
    summary: str
    status: str | None = None
    priority: str | None = None
    requires_rom: bool = False
    requires_runtime: bool = False


@dataclass(frozen=True)
class ProjectStatus:
    """Small current-state manifest shared by all workstation projects."""

    phase: str
    summary: str
    milestones: tuple[StatusItem, ...]
    unknowns: tuple[StatusItem, ...]
    recommended_tasks: tuple[StatusItem, ...]


def _items(data: object, section: str, *, require_status: bool) -> tuple[StatusItem, ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        raise WorkstationError(f"status section {section!r} must be an array of tables")
    items = []
    seen: set[str] = set()
    for index, raw in enumerate(data, start=1):
        if not isinstance(raw, dict):
            raise WorkstationError(f"status {section} item {index} must be a table")
        identifier = raw.get("id")
        summary = raw.get("summary")
        status = raw.get("status")
        if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
            raise WorkstationError(f"status {section} item {index} has an invalid id")
        if identifier in seen:
            raise WorkstationError(f"status {section} repeats id {identifier!r}")
        seen.add(identifier)
        if not isinstance(summary, str) or not summary.strip():
            raise WorkstationError(f"status item {identifier!r} has an empty summary")
        if require_status and status not in STATUS_VALUES:
            raise WorkstationError(
                f"status milestone {identifier!r} has invalid status {status!r}"
            )
        if not require_status and status is not None:
            raise WorkstationError(f"status {section} item {identifier!r} must not set status")
        priority = raw.get("priority")
        if priority is not None and (not isinstance(priority, str) or not priority.strip()):
            raise WorkstationError(f"status item {identifier!r} has an invalid priority")
        requires_rom = raw.get("requires_rom", False)
        requires_runtime = raw.get("requires_runtime", False)
        if not isinstance(requires_rom, bool) or not isinstance(requires_runtime, bool):
            raise WorkstationError(
                f"status item {identifier!r} runtime requirements must be booleans"
            )
        items.append(
            StatusItem(
                identifier,
                summary.strip(),
                status,
                priority.strip() if isinstance(priority, str) else None,
                requires_rom,
                requires_runtime,
            )
        )
    return tuple(items)


def load_project_status(path: str | Path) -> ProjectStatus:
    """Load and validate one optional project ``status.toml`` manifest."""

    source = Path(path)
    try:
        with source.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise WorkstationError(f"cannot load project status {source}: {error}") from error
    if data.get("schema_version") != 1:
        raise WorkstationError(f"unsupported project status schema in {source}")
    phase = data.get("phase")
    summary = data.get("summary")
    if not isinstance(phase, str) or not IDENTIFIER.fullmatch(phase):
        raise WorkstationError(f"project status {source} has an invalid phase")
    if not isinstance(summary, str) or not summary.strip():
        raise WorkstationError(f"project status {source} has an empty summary")
    return ProjectStatus(
        phase=phase,
        summary=summary.strip(),
        milestones=_items(data.get("milestones"), "milestones", require_status=True),
        unknowns=_items(data.get("unknowns"), "unknowns", require_status=False),
        recommended_tasks=_items(
            data.get("recommended_tasks"), "recommended_tasks", require_status=False
        ),
    )


def status_to_dict(status: ProjectStatus) -> dict[str, object]:
    """Return a stable JSON-compatible representation."""

    def item(value: StatusItem) -> dict[str, object]:
        result: dict[str, object] = {"id": value.id, "summary": value.summary}
        if value.status is not None:
            result["status"] = value.status
        if value.priority is not None:
            result["priority"] = value.priority
        if value.requires_rom:
            result["requires_rom"] = True
        if value.requires_runtime:
            result["requires_runtime"] = True
        return result

    return {
        "phase": status.phase,
        "summary": status.summary,
        "milestones": [item(value) for value in status.milestones],
        "unknowns": [item(value) for value in status.unknowns],
        "recommended_tasks": [item(value) for value in status.recommended_tasks],
    }