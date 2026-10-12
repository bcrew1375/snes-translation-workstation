"""Conservative helpers for the Kakusei Hen scenario bytecode.

The game indexes 370 three-byte selector slots at CPU $83:EA41.  Most slots are
LoROM pointers, while 14 are null and one target is duplicated.  The command
schema is not known well enough to split complete streams into instructions.
This module preserves each unique candidate range as opaque bytes and decodes
only individually requested commands whose operand sizes are confirmed from
their handlers.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable

from PIL import Image

from snesworkbench.graphics import decode_tiles
from snesworkbench.rom import cpu_to_offset


ROOT_TABLE_OFFSET = 0x01EA41
ROOT_COUNT = 0x172
DISPATCH_TABLE_OFFSET = 0x01B2A7
DISPATCH_OPCODE_COUNT = 0x49
TERMINATOR = 0x49
TEXT_TERMINATOR = 0x0000
TEXT_LINE_BREAK = 0x000A
TEXT_PRESENTATION_BANK = 0x98
TEXT_PRESENTATION_ADDRESS = 0x8000
TEXT_PRESENTATION_FIRST_SELECTOR = 0x0200
TEXT_SELECTOR_LAST = 0x0F94


@dataclass(frozen=True)
class TextTableRange:
    """One evidence-bounded command-$08 selector table."""

    selector_start: int
    selector_end: int
    bank: int
    address: int

    @property
    def count(self) -> int:
        return self.selector_end - self.selector_start + 1


TEXT_TABLE_RANGES = (
    TextTableRange(0x0000, 0x03DF, 0x99, 0x8000),
    TextTableRange(0x03E0, 0x05B6, 0x9A, 0x8000),
    TextTableRange(0x05B7, 0x07AE, 0x9B, 0x8000),
    TextTableRange(0x07AF, 0x097C, 0x9C, 0x8000),
    TextTableRange(0x097D, 0x0B44, 0x9D, 0x8000),
    TextTableRange(0x0B45, 0x0D15, 0x9E, 0x8000),
    TextTableRange(0x0D16, 0x0ED3, 0x9F, 0x8000),
    TextTableRange(0x0ED4, TEXT_SELECTOR_LAST, 0x98, 0xC1C8),
)


@dataclass(frozen=True)
class CommandSchema:
    """Evidence-backed operand layout for one scenario command."""

    opcode: int
    handler: int | None
    operand_size: int
    operand_encoding: str | None
    description: str

    @property
    def cpu_address(self) -> str | None:
        return None if self.handler is None else f"83:{self.handler:04X}"


KNOWN_COMMAND_SCHEMAS = {
    0x07: CommandSchema(
        opcode=0x07,
        handler=0xB9AA,
        operand_size=0,
        operand_encoding=None,
        description=(
            "opens the prepared X/Y/B choice prompt; the handler sets WRAM $0C3F "
            "to one, clears the tile work area, invokes CPU $81:8000 with a 21x8 "
            "presentation, and advances by only the opcode byte"
        ),
    ),
    0x08: CommandSchema(
        opcode=0x08,
        handler=0xB9EC,
        operand_size=2,
        operand_encoding="little_endian_u16",
        description=(
            "selects a zero-terminated 16-bit text/glyph stream and passes it "
            "to the renderer at CPU $80:9A0E"
        ),
    ),
    0x10: CommandSchema(
        opcode=0x10,
        handler=0xBFDE,
        operand_size=0,
        operand_encoding=None,
        description=(
            "invokes CPU $83:E600 to prepare a menu/choice presentation and "
            "advances by only the opcode byte"
        ),
    ),
    0x48: CommandSchema(
        opcode=0x48,
        handler=0xD9BA,
        operand_size=1,
        operand_encoding="u8",
        description=(
            "branches to CPU $83:847E for operand $0A or CPU $83:8537 for "
            "other values"
        ),
    ),
    TERMINATOR: CommandSchema(
        opcode=TERMINATOR,
        handler=None,
        operand_size=0,
        operand_encoding=None,
        description="ends the scenario interpreter loop",
    ),
}


@dataclass(frozen=True)
class ScenarioCommand:
    """One targeted command decode, or an opaque tail after an unknown opcode."""

    offset: int
    opcode: int
    schema: CommandSchema | None
    raw: bytes
    operand: int | None
    next_offset: int | None

    @property
    def is_known(self) -> bool:
        return self.schema is not None

    @property
    def is_terminator(self) -> bool:
        return self.opcode == TERMINATOR


@dataclass(frozen=True)
class ScenarioRoot:
    """One scenario root and its opaque candidate range."""

    index: int
    bank: int
    address: int
    offset: int
    end_offset: int
    data: bytes

    @property
    def size(self) -> int:
        return self.end_offset - self.offset

    @property
    def cpu_address(self) -> str:
        return f"{self.bank:02X}:{self.address:04X}"


@dataclass(frozen=True)
class ScenarioRootSlot:
    """One exact selector-table slot, including null and duplicate entries."""

    index: int
    bank: int
    address: int
    offset: int | None

    @property
    def is_null(self) -> bool:
        return self.bank == 0 and self.address == 0

    @property
    def cpu_address(self) -> str | None:
        return None if self.is_null else f"{self.bank:02X}:{self.address:04X}"


@dataclass(frozen=True)
class DispatchEntry:
    """One opcode-to-handler word from CPU $83:B2A7."""

    opcode: int
    handler: int | None

    @property
    def cpu_address(self) -> str | None:
        return None if self.handler is None else f"83:{self.handler:04X}"


@dataclass(frozen=True)
class TextPresentation:
    """Command-$08 presentation data and confirmed renderer dimensions."""

    kind: str
    raw: bytes | None
    table_address: int | None
    table_offset: int | None
    width_cells: int
    height_cells: int

    @property
    def cpu_address(self) -> str | None:
        if self.table_address is None:
            return None
        return f"{TEXT_PRESENTATION_BANK:02X}:{self.table_address:04X}"

    @property
    def portrait_resource(self) -> int | None:
        """Graphics-resource selector used by an ordinary presentation pair."""

        if self.kind != "context_pair" or self.raw is None:
            return None
        return self.raw[0]

    @property
    def portrait_variant(self) -> int | None:
        """Variant within the selected portrait graphics resource."""

        if self.kind != "context_pair" or self.raw is None:
            return None
        return self.raw[1]


@dataclass(frozen=True)
class TextSelectorSlot:
    """One exact command-$08 selector slot, including null and aliased targets."""

    selector: int
    pointer_bank: int
    pointer_address: int
    pointer_offset: int
    target_address: int
    target_offset: int | None
    presentation: TextPresentation

    @property
    def is_null(self) -> bool:
        return self.target_address == 0

    @property
    def pointer_cpu_address(self) -> str:
        return f"{self.pointer_bank:02X}:{self.pointer_address:04X}"

    @property
    def target_cpu_address(self) -> str | None:
        if self.is_null:
            return None
        return f"{self.pointer_bank:02X}:{self.target_address:04X}"


@dataclass(frozen=True)
class TextStream:
    """One validated zero-terminated 16-bit text/glyph stream."""

    bank: int
    address: int
    offset: int
    end_offset: int
    data: bytes
    words: tuple[int, ...]
    line_lengths: tuple[int, ...]
    selectors: tuple[int, ...] = ()

    @property
    def cpu_address(self) -> str:
        return f"{self.bank:02X}:{self.address:04X}"

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()

    @property
    def glyph_codes(self) -> tuple[int, ...]:
        return tuple(word for word in self.words if word != TEXT_LINE_BREAK)


@dataclass(frozen=True)
class GlyphSource:
    """The four SNES 2bpp blocks used to construct one 16x16 glyph."""

    code: int
    bank: int
    address: int
    offset: int

    @property
    def cpu_address(self) -> str:
        return f"{self.bank:02X}:{self.address:04X}"

    @property
    def block_addresses(self) -> tuple[int, int, int, int]:
        return tuple(self.address + delta for delta in (0x000, 0x010, 0x100, 0x110))

    @property
    def block_offsets(self) -> tuple[int, int, int, int]:
        return tuple(self.offset + delta for delta in (0x000, 0x010, 0x100, 0x110))


def _require_range(data: bytes, start: int, size: int, description: str) -> None:
    if start < 0 or size < 0 or start + size > len(data):
        raise ValueError(f"{description} lies outside the ROM")


def decode_scenario_command(data: bytes, *, offset: int = 0) -> ScenarioCommand:
    """Decode one explicitly selected command without guessing later boundaries.

    Unknown opcodes return the complete remaining input as opaque ``raw`` data
    and have no ``next_offset``.  Callers therefore cannot accidentally continue
    at an invented instruction boundary.  Known commands reject truncated
    operands rather than reading beyond the supplied range.
    """

    _require_range(data, offset, 1, "scenario command")
    opcode = data[offset]
    schema = KNOWN_COMMAND_SCHEMAS.get(opcode)
    if schema is None:
        return ScenarioCommand(
            offset=offset,
            opcode=opcode,
            schema=None,
            raw=data[offset:],
            operand=None,
            next_offset=None,
        )

    size = 1 + schema.operand_size
    _require_range(data, offset, size, f"scenario command ${opcode:02X}")
    raw = data[offset : offset + size]
    operand = None
    if schema.operand_size:
        operand = int.from_bytes(raw[1:], "little")
    return ScenarioCommand(
        offset=offset,
        opcode=opcode,
        schema=schema,
        raw=raw,
        operand=operand,
        next_offset=offset + size,
    )


def decode_dispatch_table(
    rom: bytes,
    *,
    table_offset: int = DISPATCH_TABLE_OFFSET,
    opcode_count: int = DISPATCH_OPCODE_COUNT,
) -> tuple[DispatchEntry, ...]:
    """Decode handler words without assigning semantics to the handlers."""

    _require_range(rom, table_offset, opcode_count * 2, "dispatch table")
    entries = []
    for opcode in range(opcode_count):
        start = table_offset + opcode * 2
        value = int.from_bytes(rom[start : start + 2], "little")
        entries.append(DispatchEntry(opcode, value or None))
    return tuple(entries)


def decode_text_presentation(rom: bytes, selector: int) -> TextPresentation:
    """Decode only the confirmed structural behavior of the bank-$98 table."""

    if not 0 <= selector <= TEXT_SELECTOR_LAST:
        raise ValueError(f"text selector ${selector:04X} is outside the confirmed range")
    if selector < TEXT_PRESENTATION_FIRST_SELECTOR:
        return TextPresentation("default", None, None, None, 16, 8)

    address = TEXT_PRESENTATION_ADDRESS + (selector - TEXT_PRESENTATION_FIRST_SELECTOR) * 2
    if address + 1 > 0xFFFF:
        raise ValueError(f"text selector ${selector:04X} presentation address wraps")
    offset = cpu_to_offset(TEXT_PRESENTATION_BANK, address, "lorom")
    _require_range(rom, offset, 2, f"text selector ${selector:04X} presentation entry")
    raw = rom[offset : offset + 2]
    if raw[0] == 0xFF:
        return TextPresentation("wide_marker", raw, address, offset, 21, 8)
    if raw[0] == 0xFE:
        return TextPresentation("default_marker", raw, address, offset, 16, 8)
    return TextPresentation("context_pair", raw, address, offset, 16, 8)


def decode_text_slots(
    rom: bytes,
    *,
    table_ranges: tuple[TextTableRange, ...] = TEXT_TABLE_RANGES,
) -> tuple[TextSelectorSlot, ...]:
    """Decode the evidence-bounded command-$08 selector tables exactly."""

    slots = []
    expected_selector = 0
    for table in table_ranges:
        if table.selector_start != expected_selector or table.selector_end < table.selector_start:
            raise ValueError("text table ranges must be contiguous and ordered")
        table_offset = cpu_to_offset(table.bank, table.address, "lorom")
        _require_range(rom, table_offset, table.count * 2, "text selector table")
        for index, selector in enumerate(range(table.selector_start, table.selector_end + 1)):
            pointer_address = table.address + index * 2
            pointer_offset = table_offset + index * 2
            target_address = int.from_bytes(rom[pointer_offset : pointer_offset + 2], "little")
            target_offset = None
            if target_address:
                if target_address < 0x8000:
                    raise ValueError(
                        f"text selector ${selector:04X} has invalid target ${target_address:04X}"
                    )
                target_offset = cpu_to_offset(table.bank, target_address, "lorom")
                if target_offset >= len(rom):
                    raise ValueError(f"text selector ${selector:04X} points outside the ROM")
            slots.append(
                TextSelectorSlot(
                    selector=selector,
                    pointer_bank=table.bank,
                    pointer_address=pointer_address,
                    pointer_offset=pointer_offset,
                    target_address=target_address,
                    target_offset=target_offset,
                    presentation=decode_text_presentation(rom, selector),
                )
            )
        expected_selector = table.selector_end + 1
    return tuple(slots)


def decode_text_stream(
    rom: bytes,
    *,
    bank: int,
    address: int,
    selectors: tuple[int, ...] = (),
) -> TextStream:
    """Decode one stream while rejecting unconfirmed low control values."""

    if address < 0x8000:
        raise ValueError(f"text stream {bank:02X}:{address:04X} is not a LoROM address")
    offset = cpu_to_offset(bank, address, "lorom")
    bank_end = min(((bank & 0x7F) + 1) * 0x8000, len(rom))
    cursor = offset
    words = []
    line_lengths = [0]
    while cursor + 2 <= bank_end:
        word = int.from_bytes(rom[cursor : cursor + 2], "little")
        cursor += 2
        if word == TEXT_TERMINATOR:
            return TextStream(
                bank=bank,
                address=address,
                offset=offset,
                end_offset=cursor,
                data=rom[offset:cursor],
                words=tuple(words),
                line_lengths=tuple(line_lengths),
                selectors=selectors,
            )
        if word == TEXT_LINE_BREAK:
            words.append(word)
            line_lengths.append(0)
            continue
        if word < 0x0100:
            raise ValueError(
                f"text stream {bank:02X}:{address:04X} contains unknown low word ${word:04X}"
            )
        words.append(word)
        line_lengths[-1] += 1
    raise ValueError(f"text stream {bank:02X}:{address:04X} has no in-bank terminator")


def decode_unique_text_streams(
    rom: bytes,
    slots: tuple[TextSelectorSlot, ...] | None = None,
) -> tuple[TextStream, ...]:
    """Decode each unique non-null target and retain all selector aliases."""

    if slots is None:
        slots = decode_text_slots(rom)
    aliases: dict[tuple[int, int], list[int]] = {}
    for slot in slots:
        if slot.is_null:
            continue
        aliases.setdefault((slot.pointer_bank, slot.target_address), []).append(slot.selector)
    return tuple(
        decode_text_stream(rom, bank=bank, address=address, selectors=tuple(selectors))
        for (bank, address), selectors in aliases.items()
    )


def glyph_source(code: int) -> GlyphSource:
    """Resolve one renderer glyph code to its four-block FastROM source."""

    if 0x0100 <= code < 0x0500:
        bank = 0xB6
        address = 0x80A0 + (code - 0x0100) * 0x20
    elif 0x0500 <= code < 0x0900:
        bank = 0xB7
        address = 0x8000 + (code - 0x0500) * 0x20
    elif code >= 0x0900:
        bank = 0xB6
        address = 0xBCA0 + (code - 0x0900) * 0x20
    else:
        raise ValueError(f"${code:04X} is not an ordinary glyph code")
    if address + 0x11F > 0xFFFF:
        raise ValueError(f"glyph code ${code:04X} would wrap its four-block source")
    return GlyphSource(code, bank, address, cpu_to_offset(bank, address, "lorom"))


def decode_glyph(rom: bytes, code: int) -> tuple[tuple[int, ...], ...]:
    """Reconstruct a 16x16 glyph from blocks +$000, +$010, +$100, +$110."""

    source = glyph_source(code)
    tiles = []
    for block_offset in source.block_offsets:
        _require_range(rom, block_offset, 16, f"glyph ${code:04X} source block")
        tiles.append(decode_tiles(rom[block_offset : block_offset + 16], 2)[0])
    top_left, top_right, bottom_left, bottom_right = tiles
    rows = [tuple(top_left[y] + top_right[y]) for y in range(8)]
    rows.extend(tuple(bottom_left[y] + bottom_right[y]) for y in range(8))
    return tuple(rows)


def render_glyph_sheet(
    rom: bytes,
    codes: Iterable[int],
    *,
    columns: int = 16,
    scale: int = 2,
    gap: int = 1,
):
    """Render unique glyph codes in numeric order as a deterministic sheet."""

    ordered = tuple(sorted(set(codes)))
    if not ordered:
        raise ValueError("no glyph codes to render")
    if columns < 1 or scale < 1 or gap < 0:
        raise ValueError("columns and scale must be >= 1 and gap must be >= 0")
    row_count = (len(ordered) + columns - 1) // columns
    width = columns * 16 + (columns - 1) * gap
    height = row_count * 16 + (row_count - 1) * gap
    image = Image.new("L", (width, height), 255)
    pixels = image.load()
    for index, code in enumerate(ordered):
        origin_x = (index % columns) * (16 + gap)
        origin_y = (index // columns) * (16 + gap)
        for y, row in enumerate(decode_glyph(rom, code)):
            for x, value in enumerate(row):
                if value:
                    pixels[origin_x + x, origin_y + y] = 0
    if scale != 1:
        image = image.resize(
            (width * scale, height * scale),
            Image.Resampling.NEAREST,
        )
    return image


def decode_scenario_slots(
    rom: bytes,
    *,
    table_offset: int = ROOT_TABLE_OFFSET,
    count: int = ROOT_COUNT,
) -> tuple[ScenarioRootSlot, ...]:
    """Decode the exact selector table, preserving null and duplicate slots."""

    if count <= 0:
        raise ValueError("scenario root count must be positive")
    _require_range(rom, table_offset, count * 3, "scenario root table")

    slots = []
    previous_by_bank: dict[int, tuple[int, int]] = {}
    for index in range(count):
        start = table_offset + index * 3
        address = int.from_bytes(rom[start : start + 2], "little")
        bank = rom[start + 2]
        if bank == 0 and address == 0:
            slots.append(ScenarioRootSlot(index, bank, address, None))
            continue
        try:
            offset = cpu_to_offset(bank, address, "lorom")
        except ValueError as error:
            raise ValueError(f"scenario root {index} is not a LoROM address") from error
        if offset >= len(rom):
            raise ValueError(f"scenario root {index} points outside the ROM")
        if bank in previous_by_bank and offset < previous_by_bank[bank][1]:
            raise ValueError(f"scenario roots are not ordered at index {index}")
        previous_by_bank[bank] = (index, offset)
        slots.append(ScenarioRootSlot(index, bank, address, offset))
    return tuple(slots)


def decode_scenario_roots(
    rom: bytes,
    *,
    table_offset: int = ROOT_TABLE_OFFSET,
    count: int = ROOT_COUNT,
) -> tuple[ScenarioRoot, ...]:
    """Decode unique roots and retain their candidate bytes losslessly.

    A candidate range ends at the next root in the same CPU bank.  The final
    root in a bank ends at that LoROM bank's boundary.  This is a physical
    partition for analysis and round trips, not a claim that every trailing
    byte belongs to an executable script path.
    """

    slots = decode_scenario_slots(rom, table_offset=table_offset, count=count)
    pointers: list[tuple[int, int, int, int]] = []
    seen: set[tuple[int, int]] = set()
    for slot in slots:
        if slot.is_null or (slot.bank, slot.address) in seen:
            continue
        seen.add((slot.bank, slot.address))
        assert slot.offset is not None
        pointers.append((slot.index, slot.bank, slot.address, slot.offset))

    roots = []
    for position, (index, bank, address, offset) in enumerate(pointers):
        if position + 1 < len(pointers) and pointers[position + 1][1] == bank:
            end_offset = pointers[position + 1][3]
        else:
            end_offset = min(((bank & 0x7F) + 1) * 0x8000, len(rom))
        if end_offset <= offset:
            raise ValueError(f"scenario roots are not strictly ordered at index {index}")
        roots.append(
            ScenarioRoot(
                index=index,
                bank=bank,
                address=address,
                offset=offset,
                end_offset=end_offset,
                data=rom[offset:end_offset],
            )
        )
    return tuple(roots)


def encode_root_table(roots: tuple[ScenarioRoot, ...]) -> bytes:
    """Re-encode root pointers exactly as little-endian address plus bank."""

    encoded = bytearray()
    for root in roots:
        encoded.extend(root.address.to_bytes(2, "little"))
        encoded.append(root.bank)
    return bytes(encoded)


@dataclass(frozen=True)
class RootTextCommand:
    """One confirmed command-$08 instruction at a scenario root entry."""

    root_index: int
    rom_offset: int
    selector: int

    @property
    def cpu_address(self) -> str:
        bank = 0x80 + (self.rom_offset >> 15)
        address = 0x8000 + (self.rom_offset & 0x7FFF)
        return f"{bank:02X}:{address:04X}"


def decode_root_entry_text_commands(
    rom: bytes,
    *,
    table_offset: int = ROOT_TABLE_OFFSET,
    count: int = ROOT_COUNT,
) -> tuple[RootTextCommand, ...]:
    """Decode only roots whose pointer lands directly on command $08.

    The root table establishes the instruction boundary, and command $08's
    two-byte selector operand is confirmed from its handler.  No attempt is made
    to parse later commands or infer lengths for any other opcode.
    """

    results: list[RootTextCommand] = []
    for root in decode_scenario_roots(rom, table_offset=table_offset, count=count):
        if rom[root.offset] != 0x08:
            continue
        if root.offset + 3 > root.end_offset:
            raise ValueError(f"scenario root ${root.index:03X} has a truncated command $08")
        selector = int.from_bytes(rom[root.offset + 1 : root.offset + 3], "little")
        if selector > TEXT_SELECTOR_LAST:
            raise ValueError(
                f"scenario root ${root.index:03X} command $08 selector ${selector:04X} "
                "is outside the confirmed range"
            )
        results.append(RootTextCommand(root.index, root.offset, selector))
    return tuple(results)


def encode_root_slots(slots: tuple[ScenarioRootSlot, ...]) -> bytes:
    """Re-encode every selector slot exactly, including nulls and duplicates."""

    encoded = bytearray()
    for slot in slots:
        encoded.extend(slot.address.to_bytes(2, "little"))
        encoded.append(slot.bank)
    return bytes(encoded)


def restore_candidate_ranges(rom: bytes, roots: tuple[ScenarioRoot, ...]) -> bytes:
    """Restore opaque candidate ranges, rejecting resized or overlapping data."""

    restored = bytearray(rom)
    previous_end = -1
    for root in roots:
        if root.offset < previous_end:
            raise ValueError(f"scenario root {root.index} overlaps the previous range")
        if len(root.data) != root.size:
            raise ValueError(f"scenario root {root.index} data length changed")
        _require_range(restored, root.offset, root.size, f"scenario root {root.index}")
        restored[root.offset : root.end_offset] = root.data
        previous_end = root.end_offset
    return bytes(restored)
