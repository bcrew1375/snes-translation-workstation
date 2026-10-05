import unittest

from snesworkbench.graphics import (
    decode_tile_stream,
    decode_tiles,
    encode_tiles,
    render_tile_sheet,
    tile_stride,
)


class GraphicsTest(unittest.TestCase):
    def test_roundtrip(self):
        tile = [[((x + y) & 15) for x in range(8)] for y in range(8)]
        self.assertEqual(decode_tiles(encode_tiles([tile], 4), 4), [tile])

    def test_tile_stride_per_depth(self):
        self.assertEqual(tile_stride(2), 16)
        self.assertEqual(tile_stride(4), 32)
        self.assertEqual(tile_stride(8), 64)
        for bad in (0, 1, 3, 16):
            with self.assertRaises(ValueError):
                tile_stride(bad)


class TileStreamTest(unittest.TestCase):
    def test_partial_trailing_tile_is_ignored(self):
        tile = [[1] * 8 for _ in range(8)]
        data = encode_tiles([tile], 4) + b"\xAA" * 7
        self.assertEqual(len(decode_tile_stream(data, 4)), 1)

    def test_sheet_geometry(self):
        tiles = [[[((x + y) & 3) for x in range(8)] for y in range(8)] for _ in range(6)]
        data = encode_tiles(tiles, 4)
        image = render_tile_sheet(data, bpp=4, columns=4, scale=1, gap=1)
        # 4 columns, 2 rows, 8px cells, 1px gaps
        self.assertEqual(image.size, (4 * 8 + 3, 2 * 8 + 1))

    def test_scale_is_nearest_neighbour(self):
        tiles = [[[0] * 8 for _ in range(8)] for _ in range(4)]
        data = encode_tiles(tiles, 4)
        image = render_tile_sheet(data, bpp=4, columns=2, scale=3, gap=0)
        self.assertEqual(image.size, (2 * 8 * 3, 2 * 8 * 3))

    def test_normalize_makes_low_indices_visible(self):
        """A glyph using only indices 0 and 1 must be visible when normalized."""
        # 2bpp tile with a single index-1 pixel at (0,0), rest index 0.
        tile = [[0] * 8 for _ in range(8)]
        tile[0][0] = 1
        data = encode_tiles([tile], 2)

        faithful = render_tile_sheet(data, bpp=2, columns=1, scale=1, gap=0)
        normalized = render_tile_sheet(data, bpp=2, columns=1, scale=1, gap=0,
                                      normalize=True)
        # Faithful: index 1 of 3 maps to a mid gray. Normalized: full black.
        self.assertGreater(faithful.getpixel((0, 0)), normalized.getpixel((0, 0)))
        self.assertEqual(normalized.getpixel((0, 0)), 0)
        # Background is untouched either way.
        self.assertEqual(faithful.getpixel((1, 1)), 255)
        self.assertEqual(normalized.getpixel((1, 1)), 255)

    def test_single_colour_stream_does_not_divide_by_zero(self):
        data = encode_tiles([[[0] * 8 for _ in range(8)]], 4)
        image = render_tile_sheet(data, bpp=4, columns=1, scale=1, gap=0,
                                  normalize=True)
        self.assertEqual(image.getpixel((0, 0)), 255)

    def test_empty_input_is_rejected(self):
        with self.assertRaises(ValueError):
            render_tile_sheet(b"\x00" * 8, bpp=4, columns=1)

    def test_invalid_bpp_is_rejected(self):
        with self.assertRaises(ValueError):
            render_tile_sheet(bytes(64), bpp=3, columns=1)


if __name__ == "__main__":
    unittest.main()
