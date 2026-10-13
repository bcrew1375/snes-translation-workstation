"""Repository policy checks for ROM-derived and translation source material."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from .errors import WorkstationError
from .manifests import manifest_int, manifest_int_list, parse_manifest_text


BANNED_PREFIXES = ("analysis/", "build/", "disassembly/")
BANNED_PROJECT_COMPONENTS = {"disassembly", "local", "original"}
BANNED_TRANSLATION_BASENAMES = {"strings.tsv", "text_layout.tsv"}
BANNED_SUFFIXES = (
    ".sfc",
    ".smc",
    ".fig",
    ".swc",
    ".sfv",
    ".rom",
    ".spc",
    ".srm",
    ".wav",
    ".bin",
    ".png",
    ".o",
    ".map",
    ".sym",
)
CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
LONG_HEX_ARRAY = re.compile(r"(?:0x[0-9a-fA-F]{2}\s*,\s*){16,}")
LONG_BYTE_ESCAPE = re.compile(r"(?:\\x[0-9a-fA-F]{2}){16,}")

TRANSLATION_SCHEMAS = {
    "patches.toml": ("record", {
        "id": str, "original_address": str, "original_offset": int,
        "original_length": int, "source_sha256": str, "english": list,
        "status": str, "notes": str,
    }, {"max_line_length": int}),
    "references.toml": ("record", {
        "id": str, "reference_type": str, "reference_address": str,
        "reference_offset": int, "message_index": int, "pointer_format": str,
        "target_address": str, "target_offset": int,
    }, {}),
    "ranges.toml": ("record", {
        "name": str, "rom_start": int, "rom_end": int, "cpu_start": str,
        "cpu_end": str, "bank": int, "alignment": int, "evidence": str,
        "confidence": str,
    }, {}),
    "glossary.toml": ("term", {
        "id": str, "category": str, "canonical": str, "aliases": list,
        "usage_notes": str, "status": str,
    }, {}),
    "menu.toml": ("record", {
        "id": str, "original_address": str, "original_offset": int,
        "original_length": int, "source_sha256": str, "record_type": str,
        "character_offsets": list, "english": str, "status": str, "notes": str,
    }, {}),
    "name_entry.toml": ("record", {
        "id": str, "original_address": str, "original_offset": int,
        "original_length": int, "source_sha256": str, "record_type": str,
        "english": str, "status": str, "notes": str,
    }, {}),
    "choices.toml": ("record", {
        "id": str, "record_type": str, "button": str, "pointer_address": str,
        "pointer_offset": int, "original_address": str, "original_offset": int,
        "original_length": int, "source_sha256": str,
        "destination_address": str, "destination_offset": int,
        "prefix_words": int, "english": str, "status": str, "notes": str,
    }, {}),
}


def source_files(root: Path) -> list[str]:
    """Return tracked and prospective non-ignored files relative to ``root``."""
    import subprocess

    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return sorted(
        value.decode()
        for value in result.stdout.split(b"\x00")
        if value and (root / value.decode()).is_file()
    )


def prohibited_path(relative: str) -> str | None:
    """Return a failure message when a repository-relative path is prohibited."""
    path = PurePosixPath(relative)
    if any(relative.startswith(prefix) for prefix in BANNED_PREFIXES):
        return f"prohibited generated path: {relative}"
    if path.parts and path.parts[0] == "projects":
        if BANNED_PROJECT_COMPONENTS.intersection(path.parts):
            return f"prohibited project-local evidence: {relative}"
        if "rom" in path.parts and path.name != "README.md":
            return f"prohibited ROM input path: {relative}"
        if "translation" in path.parts and path.name in BANNED_TRANSLATION_BASENAMES:
            return f"prohibited decoded-original catalog: {relative}"
        if len(path.parts) >= 4 and path.parts[2] == "analysis" and path.parts[3] == "tiles":
            return f"prohibited extracted project artwork: {relative}"
    if relative.lower().endswith(BANNED_SUFFIXES):
        return f"prohibited file type: {relative}"
    return None


def _translation_manifest_name(relative: str) -> str | None:
    path = PurePosixPath(relative)
    if len(path.parts) == 4 and path.parts[0] == "projects" and path.parts[2] == "translation":
        if path.name in TRANSLATION_SCHEMAS:
            return path.name
    if (
        len(path.parts) == 5
        and path.parts[0] == "projects"
        and path.parts[2:4] == ("translation", "patches")
        and path.suffix == ".toml"
    ):
        return "patches.toml"
    return None


def validate_translation_manifest(relative: str, text: str) -> list[str]:
    """Validate a tracked English/reference manifest without requiring data rows."""
    name = _translation_manifest_name(relative)
    if name is None:
        return []
    table, fields, optional_fields = TRANSLATION_SCHEMAS[name]
    try:
        rows = parse_manifest_text(
            relative, text, fields, table=table, optional_fields=optional_fields
        )
    except WorkstationError as error:
        return [str(error)]

    failures: list[str] = []
    identifiers: set[str] = set()
    for record_number, row in enumerate(rows, start=1):
        identifier_column = "name" if name == "ranges.toml" else "id"
        identifier = row[identifier_column]
        if not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", identifier):
            failures.append(
                f"{relative} record {record_number} has an invalid {identifier_column}"
            )
        if identifier in identifiers:
            failures.append(
                f"{relative} record {record_number} repeats {identifier_column} {identifier}"
            )
        identifiers.add(identifier)
        if name in ("patches.toml", "menu.toml", "name_entry.toml", "choices.toml"):
            digest = row["source_sha256"]
            if digest and not re.fullmatch(r"[0-9a-f]{64}", digest):
                failures.append(
                    f"{relative} record {record_number} has an invalid source SHA-256"
                )
            length = manifest_int(row["original_length"], "original length")
            if length <= 0:
                failures.append(
                    f"{relative} record {record_number} has an invalid original length"
                )
            if not row["english"]:
                failures.append(f"{relative} record {record_number} has empty English text")
            if name == "patches.toml":
                lines = row["english"]
                if any(not isinstance(line, str) for line in lines):
                    failures.append(
                        f"{relative} record {record_number} has a non-string English line"
                    )
                else:
                    if any(not line for line in lines):
                        failures.append(
                            f"{relative} record {record_number} has an empty English line"
                        )
                    if any("\n" in line or "\r" in line for line in lines):
                        failures.append(
                            f"{relative} record {record_number} has an embedded English line break"
                        )
                    limit = row.get("max_line_length")
                    if limit is not None and limit not in {21, 28}:
                        failures.append(
                            f"{relative} record {record_number} has invalid max_line_length"
                        )
                    elif limit is not None:
                        for line_number, line in enumerate(lines, start=1):
                            if len(line) > limit:
                                failures.append(
                                    f"{relative} record {record_number} line {line_number} "
                                    f"has {len(line)} characters; max_line_length is {limit}"
                                )
            if name == "menu.toml":
                if row["record_type"] not in {"terminated", "fixed", "fixed_native_suffix"}:
                    failures.append(
                        f"{relative} record {record_number} has an invalid record type"
                    )
                try:
                    offsets = manifest_int_list(row["character_offsets"], "character offsets")
                except WorkstationError:
                    offsets = []
                if not offsets or any(offset < 0 for offset in offsets):
                    failures.append(
                        f"{relative} record {record_number} has invalid character offsets"
                    )
            if name == "name_entry.toml" and row["record_type"] not in {
                "picker_page", "selection_map", "fixed_text", "default_names"
            }:
                failures.append(
                    f"{relative} record {record_number} has an invalid record type"
                )
            if name == "choices.toml":
                if row["record_type"] not in {"fixed_label", "option"}:
                    failures.append(
                        f"{relative} record {record_number} has an invalid record type"
                    )
                if row["button"] not in {"", "X", "Y", "B"}:
                    failures.append(f"{relative} record {record_number} has an invalid button")
                if row["prefix_words"] < 0:
                    failures.append(
                        f"{relative} record {record_number} has invalid prefix words"
                    )
        if name == "glossary.toml":
            if any(not isinstance(alias, str) for alias in row["aliases"]):
                failures.append(f"{relative} record {record_number} has invalid aliases")
    return failures


def validate_source_text(relative: str, text: str) -> list[str]:
    """Validate text content after path-level policy has accepted the file."""
    failures = validate_translation_manifest(relative, text)
    if CJK.search(text):
        failures.append(f"Japanese/CJK content requires explicit review: {relative}")
    if LONG_HEX_ARRAY.search(text) or LONG_BYTE_ESCAPE.search(text):
        failures.append(f"suspicious embedded byte array requires review: {relative}")
    return failures


def audit_repository(root: Path) -> list[str]:
    """Return all repository policy failures beneath ``root``."""
    failures: list[str] = []
    for relative in source_files(root):
        path_failure = prohibited_path(relative)
        if path_failure:
            failures.append(path_failure)
            continue
        try:
            text = (root / relative).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            failures.append(f"unreviewed binary file: {relative}")
            continue
        failures.extend(validate_source_text(relative, text))
    return failures