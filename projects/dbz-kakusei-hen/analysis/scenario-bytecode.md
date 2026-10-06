# Scenario bytecode investigation

This note records evidence for the scenario interpreter without claiming that its
commands or text encoding are fully understood.

## Confirmed interpreter state

The interpreter entry at CPU `$83:B24F` / ROM `$01B24F` uses `$029C * 3` to select
one of 370 three-byte slots from CPU `$83:EA41-$83:EE96` / ROM
`$01EA41-$01EE96`. Each non-null slot is a little-endian 16-bit CPU address
followed by a bank byte. Slots `$0161-$016E` are zero; slot `$015A` duplicates
slot `$0159`'s target `$93:BA88`.

The selected stream state is stored in WRAM:

| WRAM | Confirmed use |
| --- | --- |
| `$0C39` | 16-bit current stream cursor |
| `$0C3B` | current stream data bank |
| `$0C37` | current one-byte command value |

The loop at CPU `$83:B26B` / ROM `$01B26B` reads one byte through DBR and Y. It
ends when that value is `$49`; otherwise it doubles the value and reads a 16-bit
handler address from CPU `$83:B2A7` / ROM `$01B2A7`, then performs an indirect
jump.

The dispatch table contains 73 words for values `$00-$48`. Entry `$00` is the
null word `$0000`; entries `$01-$48` point into CPU bank `$83`, ending with the
`$48` handler at `$83:D9BA`. The null entry is recorded as an unresolved anomaly,
not as a valid executable handler.

## Root table layout

The table contains 356 non-null pointers to 355 unique targets:

| Root indexes | CPU target bank | Target range | ROM range |
| --- | --- | --- | --- |
| `$0000-$008F` | `$91` | `$91:8000-$91:FED0` | `$088000-$08FED0` |
| `$0090-$0121` | `$92` | `$92:8000-$92:FD7B` | `$090000-$097D7B` |
| `$0122-$0160`, `$016F-$0171` | `$93` | `$93:8000-$93:C163` | `$098000-$09C163` |

The first root in each bank begins at the bank boundary. For lossless local
analysis, each unique root's candidate range can conservatively end at the next
unique root in the same bank, with the final root extending to that bank's end.
This partitions ROM `$088000-$09FFFF`, but it does **not** prove that every
trailing byte is reachable scenario code.

Run the local analyzer with:

```text
tools/bin/dbz-kakusei-scenario \
  projects/dbz-kakusei-hen/rom/original.sfc
```

To write opaque ROM-derived streams, use an ignored directory:

```text
tools/bin/dbz-kakusei-scenario \
  projects/dbz-kakusei-hen/rom/original.sfc \
  --extract-dir projects/dbz-kakusei-hen/local/scenario
```

The tool verifies pointer-table encoding and candidate-range byte identity. It
does not split complete streams because most command parameter lengths and
branch semantics remain unknown. It can decode one explicitly selected command
without scanning forward:

```text
tools/bin/dbz-kakusei-scenario \
  projects/dbz-kakusei-hen/rom/original.sfc \
  --command-offset '<confirmed ROM instruction offset>'
```

The offset must be an established scenario instruction boundary, not a handler
address or an arbitrary matching byte. Unknown command values retain the rest
of the supplied range as opaque data and have no inferred next offset; the CLI
reports only its length, digest, and a short preview.

## Command `$08`

The handler at CPU `$83:B9EC` / ROM `$01B9EC` advances the cursor and reads a
little-endian 16-bit parameter. It uses parameter thresholds to select word
tables across CPU banks `$98-$9F`; the selected word is stored in WRAM `$0214`.
After optional metadata handling through bank `$98`, it calls CPU `$80:9A0E`
with the selected value and then advances the cursor by the two parameter bytes.

The structurally bounded selector tables are:

| Text selectors | Pointer table | Entries |
| --- | --- | ---: |
| `$0000-$03DF` | `$99:8000` | 992 |
| `$03E0-$05B6` | `$9A:8000` | 471 |
| `$05B7-$07AE` | `$9B:8000` | 504 |
| `$07AF-$097C` | `$9C:8000` | 462 |
| `$097D-$0B44` | `$9D:8000` | 456 |
| `$0B45-$0D15` | `$9E:8000` | 465 |
| `$0D16-$0ED3` | `$9F:8000` | 446 |
| `$0ED4-$0F94` | `$98:C1C8` | 193 |

Selector `$0F95` reads `$0120`, which is not a valid same-bank LoROM text
pointer and marks the evidence boundary. Within the bounded tables there are
3,989 slots, 3,558 non-null slots, 431 null slots, and 3,553 unique targets.
Unique zero-terminated stream ranges do not overlap.

For selectors `$0200+`, the handler separately indexes two bytes at
`$98:8000 + (selector - $0200) * 2`. Selectors below `$0200` bypass this table
and use a 16x8 rendering area. An entry beginning with `$FF` selects a 21x8
area. Ordinary pairs are copied to WRAM and invoke additional setup before a
16x8 area is used; their semantic meaning remains unknown. No `$FE` entry occurs
within the bounded selector corpus.

CPU `$80:9A0E` walks a zero-terminated stream of 16-bit words. Word `$000A`
advances line state, while ordinary values are passed to CPU `$80:9B2C`. The
latter maps three value ranges to graphics sources:

| Stream values | FastROM source formula | Distinct corpus codes |
| --- | --- | ---: |
| `$0100-$04FF` | `$B6:80A0 + (value-$0100)*$20` | 185, observed through `$02D0` |
| `$0500-$08FF` | `$B7:8000 + (value-$0500)*$20` | 403, observed through `$08F7` |
| `$0900+` | `$B6:BCA0 + (value-$0900)*$20` | 128, observed through `$0A30` |

All 716 distinct glyph codes in the bounded corpus have complete, non-wrapping
sources. No stream word below `$0100` occurs except `$000A` and `$0000`.

One displayed glyph is a 16x16 bitmap assembled from four 16-byte SNES 2bpp
blocks at source offsets `+$000`, `+$010`, `+$100`, and `+$110`. The compositor
ORs shifted source bytes into the WRAM staging buffer and places glyph origins
on a 12-pixel horizontal pitch. This explains why treating a contiguous 32-byte
record as two independent 8x8 tiles produced incomplete or apparently blank
characters.

This confirms that `$08` selects a text/glyph stream and reaches the renderer.
A clean, no-input runtime run additionally confirmed one visible use: scenario
selector `$0170` resolves to `$93:BF38`; its command `$08` at `$93:BF45` uses
text selector `$07E1`, whose pointer entry at `$9C:8064` selects `$9C:9358` /
ROM `$0E1358`. The command reached
`$83:B9EC`, `$80:9A0E`, and `$80:9B2C` at frame 436. The glyph routine ran 56
times. The stream contains four 14-cell lines, three `$000A` words, and one
`$0000` terminator. Reconstructing its 40 distinct glyphs directly from ROM
matches the completed runtime screenshot. The decoded passage and provisional
character map remain under ignored local working data.

In the same interval, writes began in the staging buffer at `$7E:8000` and DMA
channel 7 was enabled in mode 1 for B-bus destination `$18` (`$2118/$2119`).
From frame 437 onward it repeatedly uploaded `$0800` bytes from `$7E:8000` to
VRAM word `$0148` and `$0280` bytes from `$7E:8800` to VRAM word `$0548`.
This confirms WRAM-to-VRAM transfer for the rendered text and corrects the
earlier untested channel-0 assumption.

Inspect one text selector without decoding it to Japanese:

```text
tools/bin/dbz-kakusei-scenario \
  projects/dbz-kakusei-hen/rom/original.sfc \
  --text-selector '$07E1'
```

To extract raw streams or render the corresponding glyphs, use ignored paths:

```text
tools/bin/dbz-kakusei-scenario \
  projects/dbz-kakusei-hen/rom/original.sfc \
  --text-selector '$07E1' \
  --extract-text-dir projects/dbz-kakusei-hen/local/text \
  --glyph-sheet projects/dbz-kakusei-hen/local/text/startup-glyphs.png
```

## Command `$48`

The handler at CPU `$83:D9BA` / ROM `$01D9BA` advances the cursor, reads one
parameter byte, and compares it with `$0A`. Other values call `$83:8537`; `$0A`
calls `$83:847E`. Both paths then advance the cursor again. This confirms a
one-byte parameter but does not establish that it is a character, message ID, or
control code.

## Reproducible runtime protocol

The preferred first pass is the pinned headless backend through
`snes-automate`. Store all output under the ignored project-local tree. For
example, an initial bounded breakpoint probe is:

```sh
snes-automate projects/dbz-kakusei-hen/rom/original.sfc \
  --artifact-dir projects/dbz-kakusei-hen/local/runtime/command-08-entry \
  --frames 3600 --timeout 60 \
  --breakpoint 'SnesMemory:0x83B9EC:x' \
  --read-memory 'SnesWorkRam:0x029C:2' \
  --read-memory 'SnesWorkRam:0x0C37:5' \
  --pc --state-json --trace
```

Normal boot reaches this breakpoint around frame 436 in the pinned backend.
Inspect `metadata.json`, require `trustworthy: true`, and confirm that the final
summary reason is `debugger_break` before interpreting a new capture. Capture
screenshots in separate bounded frame runs because the breakpoint stops before
the newly rendered glyphs are presented on screen.

### Automatic opening sequence

A trusted 7,200-frame no-input trace of scenario root `$0170` confirmed the
complete command-`$08` chronology for the automatic opening. The four narration
panels use selectors `$07E1-$07E4`. The post-fade recap then uses these 22
selectors, in order:

```text
$0026 $07E5 $07E6 $002E $07E7 $076B $07E8 $07E9 $07EA $07EB $07EC
$07ED $07EE $07EF $0000 $0800 $0801 $0802 $0003 $0803 $0804 $0805
```

The first cycle reached `$07E1` at frame 436, the first post-fade record `$0026`
at frame 1233, and the final record `$0805` at frame 3336. Desktop capture showed
the title screen returning at approximately 60 seconds. A second cycle began at
frame 5733, confirming that the long title-screen interval separates repeated
attract-mode cycles rather than extending the recap.

All 26 selected streams were correlated with visible scenes. Their exact selector,
pointer, CPU-address, ROM-offset, length, digest, and repository-authored English
replacement are recorded in `translation/references.tsv` and
`translation/patches.tsv`. Decoded Japanese source dialogue remains local and
untracked.

The desktop services are managed with `snes-desktop`; do not start duplicate
X11 or noVNC processes. Use bsnes-plus to cross-check the first automated hit
and for its interactive VRAM/tilemap/sprite viewers. Load the immutable original
ROM and add execution breakpoints at:

- `$83:B9EC` — command `$08` entry
- `$80:9A0E` — selected 16-bit text/glyph stream renderer
- `$80:9B2C` — ordinary stream-unit/glyph processing
- `$83:D9BA` — command `$48` entry
- `$83:8537` and `$83:847E` — `$48` branch targets

For each hit, record the scenario selector slot in `$029C`, stream bank `$0C3B`,
cursor `$0C39`, current command `$0C37`, A/X/Y, DBR, and the visible screen
effect. For `$08`, also record `$0214`, the word read by `$80:9A0E`, the selected
source bank/base in `$80:9B2C`, writes to `$7E:8000-$7E:9FFF`, and subsequent
DMA/VRAM activity. Keep screenshots, traces, and memory dumps under the ignored
project-local analysis area; persist only reviewed conclusions here.

## Current evidence boundary

- Scenario control flow is confirmed.
- Selector-slot storage, null slots, duplicate target, and target banks are confirmed.
- `$49` is confirmed as the interpreter's end condition.
- Command-specific parameter lengths are incomplete; only `$08`, `$48`, and the
  `$49` terminator are currently structured by the analyzer.
- Scenario root `$0170` is confirmed to drive the complete automatic opening:
  four narration selectors and 22 post-fade recap selectors are visually
  correlated through the title-screen return.
- The 16x16 four-block glyph format, 12-pixel pitch, three source ranges, and
  716-code corpus usage are confirmed.
- A conflict-free 40-code startup mapping is confirmed locally from the
  reconstructed image, but comprehensive character mapping is incomplete and
  decoded original text remains untracked.
- The complete automatic opening is implemented with fixed-size replacement
  streams and paired Latin glyphs; no stream relocation, pointer changes, or
  renderer changes are required. General relocation constraints and the semantic
  meaning of ordinary presentation pairs remain unresolved.
