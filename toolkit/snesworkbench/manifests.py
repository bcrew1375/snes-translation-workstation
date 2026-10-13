"""Strict readers for repository-authored TSV and TOML manifests."""

from __future__ import annotations

import csv
import io
from pathlib import Path
import tomllib
from typing import Any

from .errors import WorkstationError


def read_tsv(path: str | Path) -> list[dict[str, str]]:
    """Read a UTF-8 TSV manifest and return its records."""
    source_path = Path(path)
    try:
        with source_path.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source, delimiter="\t")
            if reader.fieldnames is None:
                raise WorkstationError(f"manifest has no header: {source_path}")
            return list(reader)
    except OSError as error:
        raise WorkstationError(str(error)) from error


def _matches_type(value: object, expected: type | tuple[type, ...]) -> bool:
    """Match TOML values without accepting booleans as integers."""

    expected_types = expected if isinstance(expected, tuple) else (expected,)
    if isinstance(value, bool) and bool not in expected_types:
        return False
    return isinstance(value, expected_types)


def parse_manifest_text(
    path: str | Path,
    text: str,
    fields: dict[str, type | tuple[type, ...]],
    *,
    table: str = "record",
    optional_fields: dict[str, type | tuple[type, ...]] | None = None,
) -> list[dict[str, Any]]:
    """Parse one strict manifest while preserving its declared record order.

    TOML is the tracked format. TSV remains supported temporarily so migrations
    can compare old and new manifests through exactly the same consumers.
    """

    source_path = Path(path)
    optional_fields = {} if optional_fields is None else optional_fields
    expected_names = list(fields) + list(optional_fields)
    if source_path.suffix == ".tsv":
        try:
            reader = csv.DictReader(io.StringIO(text), delimiter="\t")
            if reader.fieldnames != expected_names:
                raise WorkstationError(f"manifest has an invalid header: {source_path}")
            return list(reader)
        except (csv.Error, TypeError) as error:
            raise WorkstationError(f"manifest is not valid TSV: {source_path}") from error
    if source_path.suffix != ".toml":
        raise WorkstationError(f"unsupported manifest format: {source_path}")

    try:
        document = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise WorkstationError(f"manifest is not valid TOML: {source_path}: {error}") from error
    expected_root = {"schema_version", table}
    unknown_root = sorted(set(document) - expected_root)
    missing_root = sorted(expected_root - set(document))
    if unknown_root:
        raise WorkstationError(
            f"manifest {source_path} has unknown top-level keys: {', '.join(unknown_root)}"
        )
    if missing_root:
        raise WorkstationError(
            f"manifest {source_path} is missing top-level keys: {', '.join(missing_root)}"
        )
    if document["schema_version"] != 1:
        raise WorkstationError(
            f"manifest {source_path} has unsupported schema version "
            f"{document['schema_version']!r}"
        )
    records = document[table]
    if not isinstance(records, list):
        raise WorkstationError(f"manifest {source_path} key {table!r} must be an array of tables")

    validated: list[dict[str, Any]] = []
    expected = set(fields) | set(optional_fields)
    required = set(fields)
    for index, record in enumerate(records, start=1):
        context = f"manifest {source_path} {table} {index}"
        if not isinstance(record, dict):
            raise WorkstationError(f"{context} is not a table")
        unknown = sorted(set(record) - expected)
        missing = sorted(required - set(record))
        if unknown:
            raise WorkstationError(f"{context} has unknown keys: {', '.join(unknown)}")
        if missing:
            raise WorkstationError(f"{context} is missing keys: {', '.join(missing)}")
        for name, expected_type in {**fields, **optional_fields}.items():
            if name not in record:
                continue
            if not _matches_type(record[name], expected_type):
                raise WorkstationError(
                    f"{context} key {name!r} has invalid type "
                    f"{type(record[name]).__name__}"
                )
        validated.append(record)
    return validated


def read_manifest(
    path: str | Path,
    fields: dict[str, type | tuple[type, ...]],
    *,
    table: str = "record",
    optional_fields: dict[str, type | tuple[type, ...]] | None = None,
) -> list[dict[str, Any]]:
    """Read a UTF-8 TSV or TOML manifest with a strict declared schema."""

    source_path = Path(path)
    try:
        text = source_path.read_text(encoding="utf-8")
    except OSError as error:
        raise WorkstationError(str(error)) from error
    return parse_manifest_text(
        source_path, text, fields, table=table, optional_fields=optional_fields
    )


def read_manifest_collection(
    path: str | Path,
    fields: dict[str, type | tuple[type, ...]],
    *,
    table: str = "record",
    optional_fields: dict[str, type | tuple[type, ...]] | None = None,
) -> list[dict[str, Any]]:
    """Read one manifest or an ordered directory of TOML manifests.

    Directory members are direct ``*.toml`` children loaded in lexical filename
    order. Each member is independently schema-validated by ``read_manifest``;
    record order is then preserved while the results are concatenated.
    """

    source_path = Path(path)
    if not source_path.is_dir():
        return read_manifest(
            source_path, fields, table=table, optional_fields=optional_fields
        )

    members = sorted(
        member for member in source_path.iterdir() if member.is_file() and member.suffix == ".toml"
    )
    if not members:
        raise WorkstationError(f"manifest directory has no TOML files: {source_path}")
    records: list[dict[str, Any]] = []
    for member in members:
        records.extend(
            read_manifest(member, fields, table=table, optional_fields=optional_fields)
        )
    return records


def manifest_int(value: object, field: str, *, hexadecimal: bool = False) -> int:
    """Normalize a native TOML integer or a legacy TSV numeric string."""

    if isinstance(value, bool):
        raise WorkstationError(f"invalid {field}: {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            if hexadecimal:
                return int(value.removeprefix("$"), 16)
            return int(value, 0)
        except ValueError as error:
            raise WorkstationError(f"invalid {field}: {value!r}") from error
    raise WorkstationError(f"invalid {field}: {value!r}")


def manifest_int_list(value: object, field: str) -> tuple[int, ...]:
    """Normalize a TOML integer array or a legacy comma-separated TSV field."""

    values: object = value.split(",") if isinstance(value, str) else value
    if not isinstance(values, list):
        raise WorkstationError(f"invalid {field}: {value!r}")
    result = tuple(manifest_int(item, field) for item in values)
    return result


def require_columns(path: str | Path, rows: list[dict[str, str]], columns: set[str]) -> None:
    """Require columns even when a manifest contains no data records."""
    source_path = Path(path)
    try:
        with source_path.open(encoding="utf-8", newline="") as source:
            fieldnames = csv.DictReader(source, delimiter="\t").fieldnames or []
    except OSError as error:
        raise WorkstationError(str(error)) from error
    missing = sorted(columns - set(fieldnames))
    if missing:
        raise WorkstationError(f"manifest {source_path} is missing columns: {', '.join(missing)}")