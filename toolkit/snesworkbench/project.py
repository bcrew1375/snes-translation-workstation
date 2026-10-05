"""Project discovery, configuration, adapter loading, and build execution."""

from __future__ import annotations

import importlib
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from .errors import WorkstationError
from .patching import BuildResult, sha256, validate_rom


@dataclass(frozen=True)
class RomConfig:
    default_path: Path
    size: int
    sha256: str


@dataclass(frozen=True)
class ApprovedRange:
    name: str
    start: int
    end: int


@dataclass(frozen=True)
class ProjectConfig:
    root: Path
    identifier: str
    name: str
    platform: str
    adapter: str
    source_directory: Path
    input: RomConfig
    output: RomConfig
    manifests: dict[str, Path]
    approved_ranges: tuple[ApprovedRange, ...]


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def project_descriptor(project: str | Path, root: Path | None = None) -> Path:
    repo = (root or repository_root()).resolve()
    candidate = Path(project)
    if candidate.exists():
        candidate = candidate.resolve()
        return candidate / "project.toml" if candidate.is_dir() else candidate
    return repo / "projects" / str(project) / "project.toml"


def _path(repo: Path, project_root: Path, value: str, *, repository_relative: bool) -> Path:
    return (repo if repository_relative else project_root) / value


def load_project(project: str | Path, root: Path | None = None) -> ProjectConfig:
    descriptor = project_descriptor(project, root)
    try:
        with descriptor.open("rb") as source:
            data = tomllib.load(source)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise WorkstationError(f"cannot load project descriptor {descriptor}: {error}") from error
    try:
        if data["schema_version"] != 1:
            raise WorkstationError(f"unsupported project schema: {data['schema_version']}")
        repo = (root or repository_root()).resolve()
        project_root = descriptor.parent.resolve()
        input_data = data["input"]
        output_data = data["output"]
        manifests = {
            name: _path(repo, project_root, value, repository_relative=False)
            for name, value in data.get("manifests", {}).items()
        }
        approved_ranges = tuple(
            ApprovedRange(item["name"], item["start"], item["end"])
            for item in data.get("approved_ranges", [])
        )
        for region in approved_ranges:
            if not 0 <= region.start <= region.end:
                raise WorkstationError(
                    f"invalid approved range {region.name}: ${region.start:X}-${region.end:X}"
                )
        config = ProjectConfig(
            root=project_root,
            identifier=data["id"],
            name=data["name"],
            platform=data["platform"],
            adapter=data["adapter"],
            source_directory=project_root / data.get("source_directory", "src"),
            input=RomConfig(
                _path(repo, project_root, input_data["default_path"], repository_relative=True),
                input_data["size"],
                input_data["sha256"],
            ),
            output=RomConfig(
                _path(repo, project_root, output_data["default_path"], repository_relative=True),
                output_data["size"],
                output_data["sha256"],
            ),
            manifests=manifests,
            approved_ranges=approved_ranges,
        )
    except (KeyError, TypeError) as error:
        raise WorkstationError(f"invalid project descriptor {descriptor}: missing {error}") from error
    if config.identifier != project_root.name:
        raise WorkstationError(
            f"project ID {config.identifier!r} does not match directory {project_root.name!r}"
        )
    return config


def discover_projects(root: Path | None = None) -> list[ProjectConfig]:
    repo = (root or repository_root()).resolve()
    return [load_project(path, repo) for path in sorted((repo / "projects").glob("*/project.toml"))]


def load_adapter(project: ProjectConfig) -> ModuleType:
    source = str(project.source_directory)
    if source not in sys.path:
        sys.path.insert(0, source)
    try:
        return importlib.import_module(project.adapter)
    except ImportError as error:
        raise WorkstationError(
            f"cannot import adapter {project.adapter!r} for {project.identifier}: {error}"
        ) from error


def build_project(
    project: ProjectConfig,
    *,
    rom_path: Path | None = None,
    output_path: Path | None = None,
    write_output: bool = True,
) -> BuildResult:
    source_path = (rom_path or project.input.default_path).resolve()
    target_path = (output_path or project.output.default_path).resolve()
    if source_path == target_path:
        raise WorkstationError("output path must not overwrite the original ROM")
    try:
        original = source_path.read_bytes()
    except OSError as error:
        raise WorkstationError(str(error)) from error
    validate_rom(
        original,
        size=project.input.size,
        digest=project.input.sha256,
        description="original ROM",
    )
    adapter = load_adapter(project)
    if not hasattr(adapter, "build"):
        raise WorkstationError(f"adapter {project.adapter!r} has no build function")
    result = adapter.build(original, project)
    validate_rom(
        result.data,
        size=project.output.size,
        digest=project.output.sha256,
        description="translated ROM",
    )
    if result.sha256 != sha256(result.data):
        raise WorkstationError("adapter returned an incorrect output SHA-256")
    if write_output:
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(result.data)
        except OSError as error:
            raise WorkstationError(str(error)) from error
    return result