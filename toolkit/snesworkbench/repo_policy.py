"""Repository policy checks for ROM-derived and translation source material."""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path, PurePosixPath


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

TRANSLATION_HEADERS = {
    "patches.tsv": [
        "id",
        "original_address",
        "original_offset",
        "original_length",
        "source_sha256",
        "english",
        "status",
        "notes",
    ],
    "references.tsv": [
        "id",
        "reference_type",
        "reference_address",
        "reference_offset",
        "message_index",
        "pointer_format",
        "target_address",
        "target_offset",
    ],
    "ranges.tsv": [
        "name",
        "rom_start",
        "rom_end",
        "cpu_start",
        "cpu_end",
        "bank",
        "alignment",
        "evidence",
        "confidence",
    ],
    "glossary.tsv": [
        "id",
        "category",
        "canonical",
        "aliases",
        "usage_notes",
        "status",
    ],
    "menu.tsv": [
        "id",
        "original_address",
        "original_offset",
        "original_length",
        "source_sha256",
        "record_type",
        "character_offsets",
        "english",
        "status",
        "notes",
    ],
    "name_entry.tsv": [
        "id",
        "original_address",
        "original_offset",
        "original_length",
        "source_sha256",
        "record_type",
        "english",
        "status",
        "notes",
    ],
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
        if path.name in TRANSLATION_HEADERS:
            return path.name
    return None


def validate_translation_manifest(relative: str, text: str) -> list[str]:
    """Validate a tracked English/reference manifest without requiring data rows."""
    name = _translation_manifest_name(relative)
    if name is None:
        return []
    try:
        reader = csv.DictReader(io.StringIO(text), delimiter="\t")
        if reader.fieldnames != TRANSLATION_HEADERS[name]:
            return [f"translation manifest has an invalid header: {relative}"]
        rows = list(reader)
    except (csv.Error, TypeError):
        return [f"translation manifest is not valid TSV: {relative}"]

    failures: list[str] = []
    identifiers: set[str] = set()
    for line_number, row in enumerate(rows, start=2):
        identifier_column = "name" if name == "ranges.tsv" else "id"
        identifier = row[identifier_column]
        if not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", identifier):
            failures.append(
                f"{relative} line {line_number} has an invalid {identifier_column}"
            )
        if identifier in identifiers:
            failures.append(f"{relative} line {line_number} repeats {identifier_column} {identifier}")
        identifiers.add(identifier)
        if name in ("patches.tsv", "menu.tsv", "name_entry.tsv"):
            digest = row["source_sha256"]
            if digest and not re.fullmatch(r"[0-9a-f]{64}", digest):
                failures.append(f"{relative} line {line_number} has an invalid source SHA-256")
            try:
                length = int(row["original_length"], 0)
            except ValueError:
                length = 0
            if length <= 0:
                failures.append(f"{relative} line {line_number} has an invalid original length")
            if not row["english"]:
                failures.append(f"{relative} line {line_number} has empty English text")
            if name == "menu.tsv":
                if row["record_type"] not in {"terminated", "fixed", "fixed_native_suffix"}:
                    failures.append(f"{relative} line {line_number} has an invalid record type")
                try:
                    offsets = [int(value, 0) for value in row["character_offsets"].split(",")]
                except ValueError:
                    offsets = []
                if not offsets or any(offset < 0 for offset in offsets):
                    failures.append(
                        f"{relative} line {line_number} has invalid character offsets"
                    )
            if name == "name_entry.tsv" and row["record_type"] not in {
                "picker_page", "selection_map", "fixed_text", "default_names"
            }:
                failures.append(f"{relative} line {line_number} has an invalid record type")
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