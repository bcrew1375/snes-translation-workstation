"""Small helpers for repository-authored tab-separated manifests."""

from __future__ import annotations

import csv
from pathlib import Path

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