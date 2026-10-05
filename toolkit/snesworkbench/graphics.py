from PIL import Image

def decode_tiles(data: bytes, bpp: int = 4):
    if bpp not in (2,4,8): raise ValueError('SNES tiles must be 2, 4, or 8 bpp')
    stride=8*bpp; tiles=[]
    for off in range(0,len(data)-stride+1,stride):
        c=data[off:off+stride]; tile=[]
        for y in range(8):
            row=[]
            for x in range(8):
                v=0
                for plane in range(bpp):
                    block=(plane//2)*16; byte=block+y*2+(plane&1)
                    v |= ((c[byte]>>(7-x))&1)<<plane
                row.append(v)
            tile.append(row)
        tiles.append(tile)
    return tiles

def encode_tiles(tiles,bpp:int=4)->bytes:
    if bpp not in (2,4,8): raise ValueError('SNES tiles must be 2, 4, or 8 bpp')
    out=bytearray()
    for tile in tiles:
        if len(tile)!=8 or any(len(r)!=8 for r in tile): raise ValueError('tiles must be 8x8')
        if any(p<0 or p >= (1<<bpp) for r in tile for p in r): raise ValueError('pixel outside palette range')
        c=bytearray(8*bpp)
        for y,row in enumerate(tile):
            for plane in range(bpp):
                c[(plane//2)*16+y*2+(plane&1)] = sum(((p>>plane)&1)<<(7-x) for x,p in enumerate(row))
        out.extend(c)
    return bytes(out)

def render_tiles(tiles,columns=16,scale=2,gap=1):
    if not tiles: raise ValueError('no complete tiles')
    rows=(len(tiles)+columns-1)//columns; w=columns*8+(columns-1)*gap; h=rows*8+(rows-1)*gap
    im=Image.new('L',(w,h),255); px=im.load(); maximum=max(max(r) for t in tiles for r in t) or 1
    for i,t in enumerate(tiles):
        ox=(i%columns)*(8+gap); oy=(i//columns)*(8+gap)
        for y,r in enumerate(t):
            for x,v in enumerate(r): px[ox+x,oy+y]=255-round(v*255/maximum)
    return im.resize((w*scale,h*scale),Image.Resampling.NEAREST) if scale!=1 else im


def decode_tile_stream(data: bytes, bpp: int) -> list[list[list[int]]]:
    """Decode as many whole tiles as ``data`` contains, ignoring a short tail."""
    stride = 8 * bpp
    whole = len(data) // stride
    return decode_tiles(data[: whole * stride], bpp)


def render_tile_sheet(
    data: bytes,
    *,
    bpp: int,
    columns: int = 16,
    scale: int = 2,
    gap: int = 1,
    normalize: bool = False,
):
    """Render raw tile data as a contact sheet.

    ``normalize=False`` maps colour index to gray using the full depth implied by
    ``bpp``, which preserves the real palette indices.

    ``normalize=True`` instead stretches the range actually present onto the full
    grayscale ramp. Fonts matter here: many Japanese titles store glyphs in a
    4bpp slot but only use indices 0 and 1, and a palette-faithful render draws
    index 1 as near-white, making the glyphs invisible. Normalizing is a
    hypothesis-testing aid for font work, not a view of the true palette.
    """
    if bpp not in (2, 4, 8):
        raise ValueError('SNES tiles must be 2, 4, or 8 bpp')
    if columns < 1 or scale < 1 or gap < 0:
        raise ValueError('columns and scale must be >= 1 and gap >= 0')
    tiles = decode_tile_stream(data, bpp)
    if not tiles:
        raise ValueError('no complete tile in the requested range')

    stride = 8 * bpp
    present = sorted({value for tile in tiles for row in tile for value in row})
    if normalize:
        low, high = present[0], present[-1]
        span = (high - low) or 1
        lookup = {v: 255 - round((v - low) * 255 / span) for v in present}
    else:
        top = (1 << bpp) - 1
        lookup = {v: 255 - round(v * 255 / top) for v in range(top + 1)}

    rows = (len(tiles) + columns - 1) // columns
    width = columns * 8 + (columns - 1) * gap
    height = rows * 8 + (rows - 1) * gap
    image = Image.new('L', (width, height), 255)
    pixels = image.load()
    for index, tile in enumerate(tiles):
        origin_x = (index % columns) * (8 + gap)
        origin_y = (index // columns) * (8 + gap)
        for y, row in enumerate(tile):
            for x, value in enumerate(row):
                pixels[origin_x + x, origin_y + y] = lookup[value]
    return image.resize((width * scale, height * scale), Image.Resampling.NEAREST)


def tile_stride(bpp: int) -> int:
    """Bytes per SNES tile at the given bit depth."""
    if bpp not in (2, 4, 8):
        raise ValueError('SNES tiles must be 2, 4, or 8 bpp')
    return 8 * bpp
