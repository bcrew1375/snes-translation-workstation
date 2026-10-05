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
