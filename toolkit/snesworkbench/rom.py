from pathlib import Path
import hashlib

HEADER_SIZE = 0x200


def strip_copier_header(data: bytes) -> tuple[bytes, int]:
    if len(data) % 0x8000 == HEADER_SIZE:
        return data[HEADER_SIZE:], HEADER_SIZE
    return data, 0


def _score_header(data: bytes, offset: int, mapper: str) -> int:
    if offset + 0x40 > len(data): return -999
    h=data[offset:offset+0x40]; score=0
    title=h[:21]
    score += sum(2 for b in title if b in (0,32) or 0x21 <= b <= 0x7e)
    checksum=int.from_bytes(h[0x1e:0x20],'little')
    complement=int.from_bytes(h[0x1c:0x1e],'little')
    if (checksum ^ complement) == 0xffff: score += 24
    reset=int.from_bytes(h[0x3c:0x3e],'little')
    if reset >= 0x8000: score += 12
    mode=h[0x15] & 0x0f
    if mapper=='lorom' and mode in (0,2,3): score += 10
    if mapper=='hirom' and mode in (1,5): score += 10
    return score


def detect_mapping(data: bytes) -> tuple[str,int,int]:
    rom, copier = strip_copier_header(data)
    candidates=[('lorom',0x7fc0),('hirom',0xffc0)]
    if len(rom) > 0x400000: candidates.append(('exhirom',0x40ffc0))
    scored=[(_score_header(rom,o,m),m,o) for m,o in candidates if o+0x40 <= len(rom)]
    if not scored: raise ValueError('file too small for an SNES internal header')
    _,mapper,offset=max(scored)
    return mapper, offset+copier, copier


def parse_cpu_address(value: str) -> tuple[int,int]:
    if ':' not in value: raise ValueError('address must use bank:address notation, e.g. 80:8000')
    b,a=value.split(':',1); bank=int(b,16); address=int(a,16)
    if not 0 <= bank <= 0xff or not 0 <= address <= 0xffff: raise ValueError('SNES CPU address out of range')
    return bank,address


def cpu_to_offset(bank: int, address: int, mapping: str) -> int:
    mapping=mapping.lower()
    if mapping=='lorom':
        if bank in (0x7e,0x7f) or address < 0x8000:
            raise ValueError('address is not cartridge ROM in standard LoROM mapping')
        return (bank & 0x7f)*0x8000 + (address & 0x7fff)
    if mapping=='hirom':
        if bank in (0x7e,0x7f): raise ValueError('WRAM banks are not cartridge ROM')
        if (bank & 0x40) == 0 and address < 0x8000:
            raise ValueError('address is not cartridge ROM in standard HiROM mapping')
        return (bank & 0x3f)*0x10000 + address
    raise ValueError(f'{mapping} CPU mapping conversion is not implemented; use a file offset explicitly')


def parse_address(value: str, *, mapping: str) -> int:
    if ':' not in value: return int(value,0)
    return cpu_to_offset(*parse_cpu_address(value),mapping)


def header(path: str):
    raw=Path(path).read_bytes(); mapping, hoff, copier=detect_mapping(raw)
    h=raw[hoff:hoff+0x40]
    title=h[:21].rstrip(b'\0 ').decode('ascii','replace')
    return {'path':path,'size_bytes':len(raw),'rom_bytes':len(raw)-copier,'copier_header_bytes':copier,
            'mapping':mapping,'header_offset':f'0x{hoff:X}','title':title,'map_mode':f'0x{h[0x15]:02X}',
            'rom_type':f'0x{h[0x16]:02X}','rom_size_code':f'0x{h[0x17]:02X}','sram_size_code':f'0x{h[0x18]:02X}',
            'region_code':f'0x{h[0x19]:02X}','checksum_complement':f'0x{int.from_bytes(h[0x1c:0x1e],"little"):04X}',
            'checksum':f'0x{int.from_bytes(h[0x1e:0x20],"little"):04X}','reset_vector':f'0x{int.from_bytes(h[0x3c:0x3e],"little"):04X}',
            'sha256':hashlib.sha256(raw).hexdigest()}
