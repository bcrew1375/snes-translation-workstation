"""Deterministic same-bank allocation for translated text streams.

Only evidence-reviewed regions supplied by the caller are allocatable. Gaps
between known objects and streams that merely lack a scenario-root reference
are deliberately not treated as free space.
"""

from __future__ import annotations

from dataclasses import dataclass

from snesworkbench.errors import WorkstationError


LOROM_BANK_SIZE = 0x8000


@dataclass(frozen=True, order=True)
class FreeSpaceRegion:
    """One reviewed half-open allocation region in a LoROM bank."""

    bank: int
    rom_start: int
    rom_end: int
    alignment: int = 2
    name: str = "reviewed free space"

    def __post_init__(self) -> None:
        bank_start = (self.bank & 0x7F) * LOROM_BANK_SIZE
        bank_end = bank_start + LOROM_BANK_SIZE
        if not 0 <= self.bank <= 0xFF:
            raise WorkstationError(f"invalid allocation bank ${self.bank:X}")
        if not bank_start <= self.rom_start < self.rom_end <= bank_end:
            raise WorkstationError(
                f"{self.name} ${self.rom_start:06X}-${self.rom_end:06X} "
                f"is not wholly inside LoROM bank ${self.bank:02X}"
            )
        if self.alignment < 1 or self.alignment & (self.alignment - 1):
            raise WorkstationError(f"{self.name} alignment must be a positive power of two")

    @property
    def size(self) -> int:
        return self.rom_end - self.rom_start

    @property
    def cpu_start(self) -> str:
        return f"{self.bank:02X}:{0x8000 + (self.rom_start & 0x7FFF):04X}"

    @property
    def cpu_end(self) -> str:
        return f"{self.bank:02X}:{0x8000 + ((self.rom_end - 1) & 0x7FFF):04X}"


@dataclass(frozen=True, order=True)
class CandidateGap:
    """An unverified structural gap that is not eligible for allocation."""

    bank: int
    rom_start: int
    rom_end: int

    @property
    def size(self) -> int:
        return self.rom_end - self.rom_start

    @property
    def cpu_start(self) -> str:
        return f"{self.bank:02X}:{0x8000 + (self.rom_start & 0x7FFF):04X}"

    @property
    def cpu_end(self) -> str:
        return f"{self.bank:02X}:{0x8000 + ((self.rom_end - 1) & 0x7FFF):04X}"


@dataclass(frozen=True)
class Allocation:
    """One complete stream allocation."""

    selector: int
    original_offset: int
    original_length: int
    new_offset: int
    new_length: int
    bank: int
    strategy: str
    region_name: str | None = None

    @property
    def end_offset(self) -> int:
        return self.new_offset + self.new_length


class StreamAllocator:
    """Stateful deterministic allocator that consumes and splits regions."""

    def __init__(self, regions: list[FreeSpaceRegion] | tuple[FreeSpaceRegion, ...]):
        ordered = sorted(regions, key=lambda region: (region.bank, region.rom_start, region.name))
        for left, right in zip(ordered, ordered[1:]):
            if left.bank == right.bank and right.rom_start < left.rom_end:
                raise WorkstationError(
                    f"reviewed allocation regions overlap at ROM ${right.rom_start:06X}"
                )
        self._regions = list(ordered)

    @property
    def remaining_regions(self) -> tuple[FreeSpaceRegion, ...]:
        return tuple(self._regions)

    def allocate(
        self,
        *,
        selector: int,
        original_offset: int,
        original_length: int,
        new_length: int,
        bank: int,
        force_relocation: bool = False,
    ) -> Allocation:
        if original_length <= 0 or new_length <= 0:
            raise WorkstationError("text stream lengths must be positive")
        bank_start = (bank & 0x7F) * LOROM_BANK_SIZE
        bank_end = bank_start + LOROM_BANK_SIZE
        if not bank_start <= original_offset < original_offset + original_length <= bank_end:
            raise WorkstationError(
                f"selector ${selector:04X} source allocation crosses bank ${bank:02X}"
            )
        if new_length <= original_length and not force_relocation:
            return Allocation(
                selector, original_offset, original_length, original_offset,
                new_length, bank, "in-place",
            )

        for index, region in enumerate(self._regions):
            if region.bank != bank:
                continue
            alignment = region.alignment
            start = (region.rom_start + alignment - 1) & ~(alignment - 1)
            end = start + new_length
            if end > region.rom_end:
                continue
            replacement: list[FreeSpaceRegion] = []
            if region.rom_start < start:
                replacement.append(
                    FreeSpaceRegion(
                        region.bank, region.rom_start, start, region.alignment, region.name
                    )
                )
            if end < region.rom_end:
                replacement.append(
                    FreeSpaceRegion(region.bank, end, region.rom_end, region.alignment, region.name)
                )
            self._regions[index : index + 1] = replacement
            return Allocation(
                selector, original_offset, original_length, start, new_length,
                bank, "in-bank", region.name,
            )

        available = sum(region.size for region in self._regions if region.bank == bank)
        raise WorkstationError(
            f"cannot allocate full {new_length}-byte stream for selector ${selector:04X} "
            f"in bank ${bank:02X}; {available} reviewed bytes remain"
        )


def allocate_stream(
    selector: int,
    original_offset: int,
    original_length: int,
    new_length: int,
    original_bank: int,
    free_regions: list[FreeSpaceRegion],
    min_gap: int = 64,
    force_relocation: bool = False,
) -> Allocation:
    """Compatibility wrapper for one allocation; ``min_gap`` is not a safety rule."""

    del min_gap
    return StreamAllocator(free_regions).allocate(
        selector=selector,
        original_offset=original_offset,
        original_length=original_length,
        new_length=new_length,
        bank=original_bank,
        force_relocation=force_relocation,
    )


def allocate_streams(
    streams: list[dict[str, int]], free_regions: list[FreeSpaceRegion]
) -> list[Allocation]:
    allocator = StreamAllocator(free_regions)
    return [
        allocator.allocate(
            selector=stream["selector"],
            original_offset=stream["original_offset"],
            original_length=stream["original_length"],
            new_length=stream["new_length"],
            bank=stream["original_bank"],
            force_relocation=bool(stream.get("force_relocation", 0)),
        )
        for stream in streams
    ]


def validate_allocation(allocation: Allocation, rom_size: int) -> bool:
    bank_start = (allocation.bank & 0x7F) * LOROM_BANK_SIZE
    bank_end = bank_start + LOROM_BANK_SIZE
    return (
        0 <= allocation.new_offset < allocation.end_offset <= rom_size
        and bank_start <= allocation.new_offset < allocation.end_offset <= bank_end
    )


def calculate_expansion_ratio(original_length: int, new_length: int) -> float:
    return float("inf") if original_length == 0 else new_length / original_length