"""Command-line interface for the multi-project translation workstation."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from .analysis import (
    calculate_coverage,
    format_text_report,
    load_analysis_manifest,
    write_reports,
)
from .errors import WorkstationError
from .project import build_project, discover_projects, load_adapter, load_project, repository_root
from .status import load_project_status, status_to_dict


def _project_summary(project) -> dict[str, object]:
    return {
        "id": project.identifier,
        "name": project.name,
        "platform": project.platform,
        "input": {
            "default_path": str(project.input.default_path),
            "size": project.input.size,
            "sha256": project.input.sha256,
        },
        "output": {
            "default_path": str(project.output.default_path),
            "size": project.output.size,
            "sha256": project.output.sha256,
        },
        "manifests": {name: str(path) for name, path in project.manifests.items()},
        "approved_ranges": [
            {"name": region.name, "start": region.start, "end": region.end}
            for region in project.approved_ranges
        ],
    }


def _validate_project(project) -> None:
    missing = [path for path in project.manifests.values() if not path.exists()]
    if missing:
        raise WorkstationError(
            "missing project manifests: " + ", ".join(str(path) for path in missing)
        )
    adapter = load_adapter(project)
    validator = getattr(adapter, "validate", None)
    if validator is not None:
        validator(project)
    analysis_path = project.manifests.get("analysis")
    if analysis_path is not None:
        manifest = load_analysis_manifest(analysis_path)
        if manifest.rom_size != project.input.size:
            raise WorkstationError(
                f"analysis ROM size {manifest.rom_size} does not match "
                f"project input size {project.input.size}"
            )
    status_path = project.manifests.get("status")
    if status_path is not None:
        load_project_status(status_path)


def _summary(project) -> dict[str, object]:
    """Build a concise cross-project summary with an optional adapter extension."""

    present = sum(path.exists() for path in project.manifests.values())
    status_path = project.manifests.get("status")
    status = load_project_status(status_path) if status_path is not None else None
    result: dict[str, object] = {
        "id": project.identifier,
        "name": project.name,
        "platform": project.platform,
        "input_rom": "present" if project.input.default_path.is_file() else "missing",
        "output_identity": "pinned" if project.output.sha256 else "unpinned",
        "manifests": {"present": present, "total": len(project.manifests)},
        "approved_ranges": len(project.approved_ranges),
        "commands": {
            "validate": f"make validate PROJECT={project.identifier}",
            "test": f"make test-project PROJECT={project.identifier}",
            "build": f"make build PROJECT={project.identifier}",
        },
    }
    if status is not None:
        result["status"] = status_to_dict(status)
    adapter = load_adapter(project)
    summarize = getattr(adapter, "summarize", None)
    if summarize is not None:
        details = summarize(project)
        if not isinstance(details, dict):
            raise WorkstationError("adapter summarize() must return a dictionary")
        result["project_details"] = details
    return result


def _format_summary(summary: dict[str, object], *, full: bool = False) -> str:
    manifests = summary["manifests"]
    commands = summary["commands"]
    lines = [
        f"Project: {summary['id']} — {summary['name']}",
        f"Platform: {summary['platform']}",
        f"Input ROM: {summary['input_rom']}",
        f"Output identity: {summary['output_identity']}",
        f"Manifests: {manifests['present']}/{manifests['total']} present",
        f"Approved ranges: {summary['approved_ranges']}",
    ]
    status = summary.get("status")
    if isinstance(status, dict):
        counts: dict[str, int] = {}
        for milestone in status["milestones"]:
            value = milestone["status"]
            counts[value] = counts.get(value, 0) + 1
        count_text = ", ".join(f"{count} {name}" for name, count in sorted(counts.items()))
        lines.extend(
            [
                f"Phase: {status['phase']}",
                f"Status: {status['summary']}",
                f"Milestones: {count_text or 'none'}",
                f"Open tasks: {len(status['recommended_tasks'])}",
                f"Known unknowns: {len(status['unknowns'])}",
            ]
        )
        if full:
            for heading, key in (
                ("Milestone details", "milestones"),
                ("Unknowns", "unknowns"),
                ("Recommended tasks", "recommended_tasks"),
            ):
                items = status[key]
                if not items:
                    continue
                lines.append(f"{heading}:")
                for item in items:
                    qualifiers = []
                    for name in ("status", "priority"):
                        if name in item:
                            qualifiers.append(str(item[name]))
                    if item.get("requires_rom"):
                        qualifiers.append("requires ROM")
                    if item.get("requires_runtime"):
                        qualifiers.append("requires runtime")
                    suffix = f" ({', '.join(qualifiers)})" if qualifiers else ""
                    lines.append(f"  {item['id']}{suffix}: {item['summary']}")
    details = summary.get("project_details")
    if isinstance(details, dict) and details:
        lines.append("Project details:")
        for key, value in details.items():
            label = key.replace("_", " ").capitalize()
            if isinstance(value, dict):
                rendered = ", ".join(f"{name}={item}" for name, item in value.items())
            elif isinstance(value, list):
                rendered = ", ".join(str(item) for item in value)
            else:
                rendered = str(value)
            lines.append(f"  {label}: {rendered}")
    lines.extend(
        [
            f"Validate: {commands['validate']}",
            f"Test: {commands['test']}",
            f"Build: {commands['build']}",
        ]
    )
    return "\n".join(lines)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="snes-workstation", description="Build and validate SNES translation projects."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list checked-in translation projects")

    info = commands.add_parser("info", help="show resolved project metadata")
    info.add_argument("project")

    summary = commands.add_parser("summary", help="show concise project and task status")
    summary.add_argument("project")
    summary_output = summary.add_mutually_exclusive_group()
    summary_output.add_argument("--json", action="store_true", help="emit structured JSON")
    summary_output.add_argument("--full", action="store_true", help="include every status entry")

    validate = commands.add_parser("validate", help="validate a project without requiring a ROM")
    validate.add_argument("project")

    build = commands.add_parser("build", help="build a translated ROM")
    build.add_argument("project")
    build.add_argument("--rom", type=Path)
    build.add_argument("-o", "--output", type=Path)

    analyze = commands.add_parser("analyze", help="generate ROM analysis coverage reports")
    analyze.add_argument("project")
    analyze.add_argument("--manifest", type=Path, help="override the project analysis manifest")
    analyze.add_argument(
        "--output-dir",
        type=Path,
        help="report directory (default: build/<project>/analysis)",
    )

    test = commands.add_parser("test", help="run one project's unit tests")
    test.add_argument("project")
    test.add_argument("--verbose", action="store_true", help="show every test name")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            for project in discover_projects():
                print(f"{project.identifier}\t{project.name}")
            return 0

        project = load_project(args.project)
        if args.command == "info":
            print(json.dumps(_project_summary(project), indent=2))
            return 0
        if args.command == "summary":
            value = _summary(project)
            print(json.dumps(value, indent=2) if args.json else _format_summary(value, full=args.full))
            return 0
        if args.command == "validate":
            _validate_project(project)
            print(f"Project {project.identifier} is valid.")
            return 0
        if args.command == "analyze":
            manifest_path = args.manifest or project.manifests.get("analysis")
            if manifest_path is None:
                raise WorkstationError(f"project {project.identifier} has no analysis manifest")
            manifest = load_analysis_manifest(manifest_path)
            if manifest.rom_size != project.input.size:
                raise WorkstationError(
                    f"analysis ROM size {manifest.rom_size} does not match "
                    f"project input size {project.input.size}"
                )
            report = calculate_coverage(manifest)
            output_directory = (
                args.output_dir
                or repository_root() / "build" / project.identifier / "analysis"
            )
            json_path, svg_path = write_reports(manifest, output_directory)
            print(format_text_report(report))
            print(f"\nWrote {json_path.resolve()}")
            print(f"Wrote {svg_path.resolve()}")
            return 0
        if args.command == "build":
            result = build_project(project, rom_path=args.rom, output_path=args.output)
            output = (args.output or project.output.default_path).resolve()
            print(f"Wrote {output} ({len(result.data)} bytes).")
            print(f"Changed {len(result.changed_offsets)} bytes in approved ranges.")
            print(f"SHA-256: {result.sha256}")
            return 0
        if args.command == "test":
            _validate_project(project)
            environment = {**os.environ, "PYTHONPATH": str(repository_root() / "toolkit")}
            verbosity = "-v" if args.verbose else "-q"
            completed = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", str(project.root / "tests"), verbosity],
                cwd=repository_root(),
                env=environment,
                check=False,
            )
            return completed.returncode
    except (OSError, WorkstationError, ValueError) as error:
        parser.error(str(error))
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())