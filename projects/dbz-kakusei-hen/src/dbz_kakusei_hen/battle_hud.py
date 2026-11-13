"""Battle-HUD compression and tile-layout helpers.

CPU $80:9CFA decodes this LZ-style format into WRAM $7E:8000.  CPU
$80:9DA7 optionally follows it by interleaving each 16-byte block as
0,8,1,9,...,7,15 before the data is uploaded to VRAM.
"""

from __future__ import annotations

from dataclasses import dataclass

from snesworkbench.errors import WorkstationError


MAX_DISTANCE = 0x0FFF
MIN_MATCH = 3
MAX_MATCH = 18


@dataclass(frozen=True)
class DecompressedResource:
    data: bytes
    consumed: int


def decompress_resource(source: bytes, offset: int = 0) -> DecompressedResource:
    """Decode one length-prefixed resource and report its compressed extent."""

    if offset < 0 or offset + 2 > len(source):
        raise WorkstationError("compressed resource header is outside the input")
    output_length = int.from_bytes(source[offset : offset + 2], "little")
    position = offset + 2
    output = bytearray()
    while len(output) < output_length:
        if position >= len(source):
            raise WorkstationError("compressed resource ends before its flag byte")
        flags = source[position]
        position += 1
        for _ in range(8):
            if len(output) >= output_length:
                break
            if flags & 1:
                if position >= len(source):
                    raise WorkstationError("compressed resource ends inside a literal")
                output.append(source[position])
                position += 1
            else:
                if position + 2 > len(source):
                    raise WorkstationError("compressed resource ends inside a reference")
                token = int.from_bytes(source[position : position + 2], "little")
                position += 2
                distance = token >> 4
                count = (token & 0x0F) + MIN_MATCH
                if distance == 0:
                    raise WorkstationError("compressed resource contains a zero-distance reference")
                for _ in range(count):
                    source_index = len(output) - distance
                    # The original routine emits zero until an initial reference reaches
                    # the beginning of its $7E:8000 output window.
                    output.append(output[source_index] if source_index >= 0 else 0)
                    if len(output) >= output_length:
                        break
            flags >>= 1
    return DecompressedResource(bytes(output), position - offset)


def compress_resource(data: bytes) -> bytes:
    """Encode a resource deterministically with longest, nearest matches."""

    if len(data) > 0xFFFF:
        raise WorkstationError("compressed resource output length exceeds 16 bits")
    encoded = bytearray(len(data).to_bytes(2, "little"))
    positions: dict[bytes, list[int]] = {}
    cursor = 0
    while cursor < len(data):
        flag_offset = len(encoded)
        encoded.append(0)
        flags = 0
        tokens = bytearray()
        for bit in range(8):
            if cursor >= len(data):
                break
            best_length = 0
            best_distance = 0
            key = data[cursor : cursor + MIN_MATCH]
            if len(key) == MIN_MATCH:
                for candidate in reversed(positions.get(key, ())):
                    distance = cursor - candidate
                    if distance > MAX_DISTANCE:
                        break
                    length = 0
                    while (
                        length < MAX_MATCH
                        and cursor + length < len(data)
                        and data[candidate + length] == data[cursor + length]
                    ):
                        length += 1
                    if length > best_length:
                        best_length = length
                        best_distance = distance
                    if length == MAX_MATCH:
                        break
            if best_length >= MIN_MATCH:
                token = (best_distance << 4) | (best_length - MIN_MATCH)
                tokens.extend(token.to_bytes(2, "little"))
                consumed = best_length
            else:
                flags |= 1 << bit
                tokens.append(data[cursor])
                consumed = 1
            for index in range(consumed):
                position = cursor + index
                if position + MIN_MATCH <= len(data):
                    positions.setdefault(data[position : position + MIN_MATCH], []).append(position)
            cursor += consumed
        encoded[flag_offset] = flags
        encoded.extend(tokens)
    return bytes(encoded)


def interleave_2bpp_blocks(data: bytes) -> bytes:
    """Model the post-decompression block transform at CPU $80:9DA7."""

    if len(data) % 16:
        raise WorkstationError("$80:9DA7 input is not a whole number of 16-byte blocks")
    output = bytearray()
    for offset in range(0, len(data), 16):
        block = data[offset : offset + 16]
        for index in range(8):
            output.extend((block[index], block[index + 8]))
    return bytes(output)


def replace_resource(source: bytes, offset: int, data: bytes, *, maximum_size: int) -> bytes:
    """Recompress and replace one resource without crossing its reviewed extent."""

    encoded = compress_resource(data)
    if len(encoded) > maximum_size:
        raise WorkstationError(
            f"recompressed resource needs {len(encoded)} bytes but only {maximum_size} are available"
        )
    patched = bytearray(source)
    end = offset + maximum_size
    if offset < 0 or end > len(patched):
        raise WorkstationError("compressed resource replacement range exceeds the ROM")
    patched[offset : offset + len(encoded)] = encoded
    return bytes(patched)