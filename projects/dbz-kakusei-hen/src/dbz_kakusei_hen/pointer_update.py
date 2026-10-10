"""Validated updates for authoritative command-$08 selector slots."""

from __future__ import annotations

from dataclasses import dataclass

from snesworkbench.errors import WorkstationError
from snesworkbench.patching import bounded_write
from snesworkbench.rom import cpu_to_offset

from .scenario import TextSelectorSlot, decode_text_slots


@dataclass(frozen=True)
class PointerTableEntry:
    selector: int
    bank: int
    address: int
    offset: int
    target_address: int
    target_offset: int | None


def slot_for_selector(
    rom: bytes, selector: int, slots: tuple[TextSelectorSlot, ...] | None = None
) -> TextSelectorSlot:
    decoded = slots if slots is not None else decode_text_slots(rom)
    if len(decoded) == 1 and decoded[0].selector == selector:
        return decoded[0]
    if not 0 <= selector < len(decoded) or decoded[selector].selector != selector:
        raise WorkstationError(f"text selector ${selector:04X} is outside the authoritative tables")
    return decoded[selector]


def read_pointer(
    rom: bytes, selector: int, slots: tuple[TextSelectorSlot, ...] | None = None
) -> PointerTableEntry:
    slot = slot_for_selector(rom, selector, slots)
    return PointerTableEntry(
        slot.selector, slot.pointer_bank, slot.pointer_address, slot.pointer_offset,
        slot.target_address, slot.target_offset,
    )


def write_pointer(
    rom: bytearray,
    selector: int,
    new_target_address: int,
    *,
    slots: tuple[TextSelectorSlot, ...] | None = None,
    expected_target_address: int | None = None,
) -> PointerTableEntry:
    slot = slot_for_selector(bytes(rom), selector, slots)
    if slot.is_null:
        raise WorkstationError(f"text selector ${selector:04X} is null")
    if not 0x8000 <= new_target_address <= 0xFFFF:
        raise WorkstationError(
            f"selector ${selector:04X} target ${new_target_address:04X} is not LoROM ROM"
        )
    if expected_target_address is not None and slot.target_address != expected_target_address:
        raise WorkstationError(
            f"selector ${selector:04X} target changed from expected "
            f"${expected_target_address:04X} to ${slot.target_address:04X}"
        )
    target_offset = cpu_to_offset(slot.pointer_bank, new_target_address, "lorom")
    if target_offset >= len(rom):
        raise WorkstationError(f"selector ${selector:04X} target lies outside the ROM")
    bounded_write(
        rom, slot.pointer_offset, new_target_address.to_bytes(2, "little"),
        f"selector ${selector:04X} pointer",
    )
    written = int.from_bytes(rom[slot.pointer_offset : slot.pointer_offset + 2], "little")
    if written != new_target_address:
        raise WorkstationError(f"selector ${selector:04X} pointer write did not round-trip")
    return PointerTableEntry(
        selector, slot.pointer_bank, slot.pointer_address, slot.pointer_offset,
        written, target_offset,
    )


def validate_pointer(rom: bytes, selector: int, expected_target_address: int) -> bool:
    return read_pointer(rom, selector).target_address == expected_target_address


def get_all_pointers(rom: bytes) -> list[PointerTableEntry]:
    slots = decode_text_slots(rom)
    return [read_pointer(rom, slot.selector, slots) for slot in slots]