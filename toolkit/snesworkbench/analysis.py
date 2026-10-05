"""Validate ROM analysis manifests and generate coverage reports."""

from __future__ import annotations

import html
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .errors import WorkstationError
ROM_BANK = 0x8000  # visualization chunk size; not a CPU mapping claim


UNKNOWN_TYPE = "unknown"
TYPE_COLORS = {
    "code": "#4e79a7",
    "data": "#f28e2b",
    "routine_data": "#ffbe7d",
    "pointer_table": "#b6992d",
    "graphics": "#59a14f",
    "compressed_graphics": "#8cd17d",
    "compressed_tilemap": "#76b7b2",
    "sgb_transfer_data": "#af7aa1",
    "text": "#e15759",
    "audio": "#edc948",
    "padding": "#bab0ac",
    UNKNOWN_TYPE: "#e6e6e6",
}


def _hex(value: object, field: str) -> int:
    if not isinstance(value, str) or not value.startswith("$"):
        raise WorkstationError(f"{field} must be a $-prefixed hexadecimal string")
    try:
        return int(value[1:], 16)
    except ValueError as error:
        raise WorkstationError(f"invalid hexadecimal value for {field}: {value!r}") from error


@dataclass(frozen=True)
class AnalysisRegion:
    bank: int
    cpu_start: int
    cpu_end: int
    rom_start: int
    rom_end: int
    type: str
    name: str
    confidence: str

    @property
    def size(self) -> int:
        return self.rom_end - self.rom_start + 1


@dataclass(frozen=True)
class AnalysisManifest:
    path: Path
    rom_size: int
    rom_banks: int
    regions: tuple[AnalysisRegion, ...]


@dataclass(frozen=True)
class CoverageRun:
    """A half-open run of bytes sharing one final classification."""

    start: int
    end: int
    type: str

    @property
    def size(self) -> int:
        return self.end - self.start


@dataclass(frozen=True)
class CoverageReport:
    rom_size: int
    bank_size: int
    type_bytes: dict[str, int]
    bank_type_bytes: tuple[dict[str, int], ...]
    runs: tuple[CoverageRun, ...]

    @property
    def analyzed_bytes(self) -> int:
        return self.rom_size - self.type_bytes.get(UNKNOWN_TYPE, 0)

    @property
    def analyzed_percent(self) -> float:
        return self.analyzed_bytes * 100 / self.rom_size if self.rom_size else 100.0


def load_analysis_manifest(path: Path) -> AnalysisManifest:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise WorkstationError(f"cannot load analysis manifest {path}: {error}") from error
    try:
        if document["schema_version"] != 1:
            raise WorkstationError(
                f"unsupported analysis schema {document['schema_version']} in {path}"
            )
        rom = document["rom"]
        rom_size = rom["size_bytes"]
        rom_banks = rom["rom_banks"]
        source_regions = document["regions"]
    except (KeyError, TypeError) as error:
        raise WorkstationError(f"invalid analysis manifest {path}: missing {error}") from error
    if not isinstance(rom_size, int) or rom_size <= 0:
        raise WorkstationError("analysis ROM size must be a positive integer")
    expected_banks = (rom_size + ROM_BANK - 1) // ROM_BANK
    if rom_banks != expected_banks:
        raise WorkstationError(
            f"analysis ROM bank count {rom_banks} does not match size ({expected_banks})"
        )
    if not isinstance(source_regions, list):
        raise WorkstationError("analysis regions must be a list")

    regions = []
    for index, source in enumerate(source_regions):
        label = f"regions[{index}]"
        try:
            bank = source["bank"]
            cpu_start = _hex(source["cpu_start"], f"{label}.cpu_start")
            cpu_end = _hex(source["cpu_end"], f"{label}.cpu_end")
            rom_start = _hex(source["rom_start"], f"{label}.rom_start")
            rom_end = _hex(source["rom_end"], f"{label}.rom_end")
            region_type = source["type"]
            name = source["name"]
            confidence = source["confidence"]
        except (KeyError, TypeError) as error:
            raise WorkstationError(f"invalid {label}: missing {error}") from error
        if not isinstance(bank, int) or bank < 0:
            raise WorkstationError(f"{label}.bank must be a non-negative integer")
        if cpu_start > cpu_end:
            raise WorkstationError(f"{label} has a reversed CPU range")
        if not isinstance(region_type, str) or not region_type or region_type == UNKNOWN_TYPE:
            raise WorkstationError(f"{label}.type must be a non-empty type other than unknown")
        if not isinstance(name, str) or not name:
            raise WorkstationError(f"{label}.name must be non-empty")
        if not isinstance(confidence, str) or not confidence:
            raise WorkstationError(f"{label}.confidence must be non-empty")
        if rom_end >= rom_size:
            raise WorkstationError(f"{label} extends beyond the ROM")
        regions.append(
            AnalysisRegion(
                bank,
                cpu_start,
                cpu_end,
                rom_start,
                rom_end,
                region_type,
                name,
                confidence,
            )
        )

    ordered = sorted(regions, key=lambda region: (region.rom_start, -region.rom_end))
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            if right.rom_start > left.rom_end:
                break
            nested = (
                left.rom_start <= right.rom_start <= right.rom_end <= left.rom_end
                or right.rom_start <= left.rom_start <= left.rom_end <= right.rom_end
            )
            if not nested:
                raise WorkstationError(
                    f"analysis regions partially overlap: {left.name!r} and {right.name!r}"
                )
            if left.rom_start == right.rom_start and left.rom_end == right.rom_end:
                raise WorkstationError(
                    f"analysis regions duplicate the same range: {left.name!r} and {right.name!r}"
                )
    return AnalysisManifest(path.resolve(), rom_size, rom_banks, tuple(regions))


def calculate_coverage(manifest: AnalysisManifest) -> CoverageReport:
    classifications = [UNKNOWN_TYPE] * manifest.rom_size
    # Broad containers are applied first. Smaller nested discoveries then supply
    # the more precise classification used by statistics and the graphical map.
    for region in sorted(manifest.regions, key=lambda item: (-item.size, item.rom_start)):
        classifications[region.rom_start : region.rom_end + 1] = [region.type] * region.size

    type_bytes = dict(sorted(Counter(classifications).items()))
    bank_type_bytes = []
    for start in range(0, manifest.rom_size, ROM_BANK):
        bank_type_bytes.append(
            dict(sorted(Counter(classifications[start : start + ROM_BANK]).items()))
        )

    runs = []
    start = 0
    for offset in range(1, manifest.rom_size + 1):
        if offset == manifest.rom_size or classifications[offset] != classifications[start]:
            runs.append(CoverageRun(start, offset, classifications[start]))
            start = offset
    return CoverageReport(
        manifest.rom_size,
        ROM_BANK,
        type_bytes,
        tuple(bank_type_bytes),
        tuple(runs),
    )


def report_document(manifest: AnalysisManifest, report: CoverageReport) -> dict[str, object]:
    def statistics(
        counts: dict[str, int],
        *,
        total: int,
        analyzed_total: int,
        total_label: str,
        analyzed_label: str,
    ) -> list[dict[str, object]]:
        return [
            {
                "type": region_type,
                "bytes": count,
                total_label: round(count * 100 / total, 6),
                analyzed_label: (
                    round(count * 100 / analyzed_total, 6)
                    if region_type != UNKNOWN_TYPE and analyzed_total
                    else None
                ),
            }
            for region_type, count in sorted(counts.items())
        ]

    banks = []
    for bank, counts in enumerate(report.bank_type_bytes):
        bank_total = sum(counts.values())
        unknown = counts.get(UNKNOWN_TYPE, 0)
        bank_analyzed = bank_total - unknown
        banks.append(
            {
                "bank": bank,
                "rom_start": bank * ROM_BANK,
                "rom_end": bank * ROM_BANK + bank_total - 1,
                "analyzed_bytes": bank_analyzed,
                "analyzed_percent": round(bank_analyzed * 100 / bank_total, 6),
                "types": statistics(
                    counts,
                    total=bank_total,
                    analyzed_total=bank_analyzed,
                    total_label="percent_of_bank",
                    analyzed_label="percent_of_bank_analyzed",
                ),
            }
        )
    return {
        "schema_version": 1,
        "source_manifest": str(manifest.path),
        "rom_size": report.rom_size,
        "analyzed_bytes": report.analyzed_bytes,
        "unknown_bytes": report.type_bytes.get(UNKNOWN_TYPE, 0),
        "analyzed_percent": round(report.analyzed_percent, 6),
        "types": statistics(
            report.type_bytes,
            total=report.rom_size,
            analyzed_total=report.analyzed_bytes,
            total_label="percent_of_rom",
            analyzed_label="percent_of_analyzed",
        ),
        "banks": banks,
    }


def format_text_report(report: CoverageReport) -> str:
    rows = [
        f"Analyzed: {report.analyzed_bytes:,} / {report.rom_size:,} bytes "
        f"({report.analyzed_percent:.2f}%)",
        "",
        "Type                         Bytes    ROM %   Analyzed %",
        "------------------------ --------- -------- ------------",
    ]
    for region_type, count in sorted(
        report.type_bytes.items(), key=lambda item: (item[0] == UNKNOWN_TYPE, -item[1], item[0])
    ):
        analyzed = (
            f"{count * 100 / report.analyzed_bytes:10.2f}%"
            if region_type != UNKNOWN_TYPE and report.analyzed_bytes
            else "           -"
        )
        rows.append(
            f"{region_type:<24} {count:>9,} "
            f"{count * 100 / report.rom_size:>7.2f}% {analyzed}"
        )
    rows.extend(["", "Bank coverage:"])
    for bank, counts in enumerate(report.bank_type_bytes):
        total = sum(counts.values())
        analyzed = total - counts.get(UNKNOWN_TYPE, 0)
        rows.append(
            f"  {bank:02X}: {analyzed:>5,} / {total:>5,} bytes "
            f"({analyzed * 100 / total:6.2f}%)"
        )
    return "\n".join(rows)


def _color(region_type: str) -> str:
    if region_type in TYPE_COLORS:
        return TYPE_COLORS[region_type]
    checksum = sum((index + 1) * ord(value) for index, value in enumerate(region_type))
    return f"hsl({checksum % 360},55%,58%)"


def render_svg(manifest: AnalysisManifest, report: CoverageReport) -> str:
    width = 1200
    label_width = 64
    plot_width = 1080
    bar_height = 24
    row_height = 38
    top = 126
    legend_types = sorted(report.type_bytes, key=lambda value: (value == UNKNOWN_TYPE, value))
    legend_rows = (len(legend_types) + 4) // 5
    height = top + len(report.bank_type_bytes) * row_height + legend_rows * 28 + 55
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<style>text{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;fill:#222}'
        '.title{font:700 24px sans-serif}.subtitle{font:14px sans-serif}'
        '.bank{font-weight:700}.small{font-size:11px}</style>',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text class="title" x="24" y="34">ROM analysis coverage</text>',
        f'<text class="subtitle" x="24" y="60">{report.analyzed_bytes:,} of '
        f'{report.rom_size:,} bytes analyzed ({report.analyzed_percent:.2f}%)</text>',
        f'<rect x="24" y="76" width="{plot_width}" height="18" '
        f'fill="{_color(UNKNOWN_TYPE)}" stroke="#999"/>',
        f'<rect x="24" y="76" width="{plot_width * report.analyzed_bytes / report.rom_size:.3f}" '
        'height="18" fill="#4e79a7"/>',
        f'<text class="small" x="{24 + plot_width + 10}" y="89">total</text>',
    ]
    runs_by_bank: list[list[CoverageRun]] = [[] for _ in report.bank_type_bytes]
    for run in report.runs:
        cursor = run.start
        while cursor < run.end:
            bank = cursor // ROM_BANK
            bank_end = min(run.end, (bank + 1) * ROM_BANK, report.rom_size)
            runs_by_bank[bank].append(CoverageRun(cursor, bank_end, run.type))
            cursor = bank_end

    for bank, runs in enumerate(runs_by_bank):
        y = top + bank * row_height
        bank_start = bank * ROM_BANK
        bank_length = min(ROM_BANK, report.rom_size - bank_start)
        counts = report.bank_type_bytes[bank]
        analyzed = bank_length - counts.get(UNKNOWN_TYPE, 0)
        parts.append(f'<text class="bank" x="24" y="{y + 17}">{bank:02X}</text>')
        parts.append(
            f'<rect x="{label_width}" y="{y}" width="{plot_width}" '
            f'height="{bar_height}" fill="white" stroke="#777"/>'
        )
        for run in runs:
            x = label_width + (run.start - bank_start) * plot_width / bank_length
            run_width = run.size * plot_width / bank_length
            title = html.escape(
                f"Bank {bank:02X} ${run.start:05X}-${run.end - 1:05X}: "
                f"{run.type} ({run.size} bytes)"
            )
            parts.append(
                f'<rect x="{x:.3f}" y="{y + 1}" width="{max(run_width, 0.2):.3f}" '
                f'height="{bar_height - 2}" fill="{_color(run.type)}">'
                f'<title>{title}</title></rect>'
            )
        parts.append(
            f'<text class="small" x="{label_width + plot_width + 10}" '
            f'y="{y + 16}">{analyzed * 100 / bank_length:6.2f}%</text>'
        )

    legend_y = top + len(report.bank_type_bytes) * row_height + 12
    for index, region_type in enumerate(legend_types):
        column = index % 5
        row = index // 5
        x = 24 + column * 230
        y = legend_y + row * 28
        count = report.type_bytes[region_type]
        parts.extend(
            [
                f'<rect x="{x}" y="{y}" width="15" height="15" '
                f'fill="{_color(region_type)}" stroke="#777"/>',
                f'<text class="small" x="{x + 21}" y="{y + 12}">'
                f'{html.escape(region_type)} {count * 100 / report.rom_size:.2f}%</text>',
            ]
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def write_reports(manifest: AnalysisManifest, output_directory: Path) -> tuple[Path, Path]:
    report = calculate_coverage(manifest)
    output_directory.mkdir(parents=True, exist_ok=True)
    json_path = output_directory / "analysis-coverage.json"
    svg_path = output_directory / "analysis-map.svg"
    json_path.write_text(
        json.dumps(report_document(manifest, report), indent=2) + "\n", encoding="utf-8"
    )
    svg_path.write_text(render_svg(manifest, report), encoding="utf-8")
    return json_path, svg_path