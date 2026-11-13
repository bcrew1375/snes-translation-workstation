# SPC700 bootstrap and audio-memory map

This note records structural facts established from the S-CPU uploader at CPU
`$83:8000-$828B` and its four bootstrap packages. It does not assign music,
sound-effect, instrument, or sample names.

## Bootstrap reconstruction

CPU `$83:8253` uploads the four package pointers at CPU `$83:828C-$8297` in
this order:

1. `$B8:8000`
2. `$BB:CE15`
3. `$B8:9135`
4. `$B9:8000`

Each package is a sequence of little-endian `length, destination, payload`
records followed by a zero length and the SPC execution address `$0800`.
Applying the records in loader order reconstructs five disjoint initialized
APU-RAM ranges:

| SPC range | Bytes | Confirmed structure |
| --- | ---: | --- |
| `$0800-$1920` | 4,385 | Main uploaded driver block; execution begins at `$0800` |
| `$1B00-$1D7F` | 640 | 64-entry sample directory followed by 64 six-byte instrument records |
| `$1E00-$1E5D` | 94 | Sequence metadata and pointer table |
| `$1F00-$2F26` | 4,135 | Pointer-selected sequence/event data |
| `$4000-$9F21` | 24,354 | Resident BRR sample corpus |

The ranges are APU addresses, not 65C816 CPU addresses or ROM offsets.

## Sample directory at SPC `$1B00`

The first `$0100` bytes form 64 four-byte sample-directory entries. Each entry
contains a BRR start address followed by a loop address.

This interpretation is independently established by CPU `$83:8105`: for each
selected ROM BRR record, the S-CPU constructs a four-byte entry at WRAM
`$1B00 + sample_id * 4`, containing the upload destination and that destination
plus the record's loop offset. It then uploads the directory entry and BRR
payload separately.

The bootstrap directory has 17 non-placeholder entries: `$00-$0D`, `$3C`,
`$3E`, and `$3F`. The remaining entries initially contain `$4000,$4000` and are
available for configuration-selected samples uploaded later.

For every non-placeholder entry:

- start and loop addresses lie within SPC `$4000-$9F21`;
- the loop address is aligned to a nine-byte BRR block relative to the start;
- walking BRR blocks from the start reaches exactly one final end block;
- the union of the records owns the complete resident corpus from `$4000`
  through `$9F21`.

## Instrument records at SPC `$1C00`

SPC `$1C00-$1D7F` contains exactly 64 records of six bytes each. The first byte
is a sample-directory index. Records `$00-$0D` select the bootstrap samples with
matching IDs, while later records select either dynamically uploaded sample IDs
or deliberate aliases such as sample `$0D`.

The driver routine at SPC `$11D4` computes `$1C00 + instrument_id * 6`, proving
that these are the records indexed by sequence events. Bytes 0-3 are copied to
per-voice state and later written to four consecutive DSP voice registers
`VxSRCN`, `VxADSR1`, `VxADSR2`, and `VxGAIN` by the flush loop at SPC `$0E8B`.
Thus the six fields are currently classified as:

1. sample-directory index / DSP `SRCN`;
2. DSP `ADSR1`;
3. DSP `ADSR2`;
4. DSP `GAIN`;
5. high byte of an unsigned Q8.8 pitch multiplier;
6. low byte of the pitch multiplier.

SPC `$1014-$1080` derives a 16-bit base pitch from the current note-class value,
multiplies it by the final two instrument bytes, shifts the 32-bit product right
by eight bits, and stores the result for DSP `VxPITCHL`/`VxPITCHH`. The byte order
is established by the multiplication: record byte 4 is the multiplier's high
byte and byte 5 is its low byte. Thus `02 00` represents `2.0` and `02 B0`
represents `2.6875` in unsigned Q8.8 form.

Commands `$FC-$FE` provide explicit per-voice overrides for this loading path:

- `$FC value` enables a mode that suppresses the record pitch multiplier and
  leaves the active multiplier zeroed;
- `$FD adsr1 adsr2` overrides the record's `ADSR1` and `ADSR2` bytes;
- `$FE srcn multiplier_high multiplier_low` overrides the record's sample index
  and Q8.8 pitch multiplier.

Selecting an instrument through `$E0` clears all three override modes before
loading the record.

## Sequence metadata at SPC `$1E00`

SPC `$1E02-$1E5B` contains 45 monotonically increasing little-endian pointers
from `$1F00` through `$2034`; SPC `$1E5C-$1E5D` is a zero terminator. The leading
word at `$1E00` is `$2000`, but its role is not yet established and it is kept
separate from the confirmed monotonic pointer array.

The pointer targets lie in the uploaded `$1F00-$2F26` range. Reachable parser
code establishes the following structural classes without yet assigning musical
meanings to every value:

- `$00-$7F` are one-byte values in the parser's nonnegative path;
- `$80-$C7` enter the note/rest-class path after a preceding duration byte;
- `$C8` and `$C9` are special note-class values;
- `$CA-$DF` are additional note-class values transformed relative to a global
  transpose-like state before pitch conversion;
- `$E0-$FF` select one of 32 handlers through the little-endian table at SPC
  `$1182-$11C1`;
- `$EF` is also recognized by the look-ahead scanner and carries a little-endian
  target address;
- `$F9` is recognized before the look-ahead pass and consumes three parameter
  bytes through SPC `$147E`.

The byte-count table at SPC `$0F6C-$0F8B` supplies total encoded lengths,
including the opcode itself, for all 32 `$E0-$FF` commands. Every handler calls
the byte reader at SPC `$0FB2` exactly `length - 1` times. The complete dispatch
schema is:

| Opcode | Length | Handler | Confirmed structural effect |
| --- | ---: | --- | --- |
| `$E0` | 2 | `$11C2` | Select instrument; clear record-field overrides |
| `$E1` | 2 | `$122E` | Set one per-voice value; cancel its active transition |
| `$E2` | 3 | `$123D` | Timed transition for the `$E1` value |
| `$E3` | 4 | `$125A` | Enable mode 1 of a three-parameter per-note modulation |
| `$E4` | 1 | `$1277` | Disable the `$E3`/`$EB` modulation |
| `$E5` | 2 | `$127D` | Set one global value; cancel its active transition |
| `$E6` | 3 | `$128C` | Timed transition for the `$E5` value |
| `$E7` | 2 | `$12A1` | Set one per-voice timing value; cancel its transition |
| `$E8` | 3 | `$12B7` | Timed transition for the `$E7` value |
| `$E9` | 2 | `$12D4` | Set global byte `$44` |
| `$EA` | 2 | `$12DA` | Set per-voice byte `$0400+x` |
| `$EB` | 4 | `$12E1` | Enable mode 2 of the `$E3` modulation |
| `$EC` | 1 | `$12FE` | Disable the `$E3`/`$EB` modulation |
| `$ED` | 2 | `$1304` | Set one per-voice value; cancel its transition |
| `$EE` | 3 | `$1312` | Timed transition for the `$ED` value |
| `$EF` | 4 | `$132E` | Set target address and repeat count; save return address |
| `$F0` | 2 | `$1377` | Set depth/target used by the `$E3`/`$EB` modulation |
| `$F1` | 4 | `$1390` | Enable mode 1 of a three-parameter pitch-state effect |
| `$F2` | 4 | `$13A8` | Enable mode 2 of that pitch-state effect |
| `$F3` | 1 | `$13C0` | Disable the `$F1`/`$F2` effect |
| `$F4` | 2 | `$13CA` | Set per-voice byte `$0340+x` |
| `$F5` | 4 | `$13D1` | Configure global echo state and invoke echo setup |
| `$F6` | 1 | `$13F5` | Clear global echo state |
| `$F7` | 4 | `$140D` | Configure echo state and load one of five 8-byte FIR tables |
| `$F8` | 4 | `$1466` | Configure a timed transition of global echo state |
| `$F9` | 4 | `$147E` | Configure delayed per-voice pitch-state transition |
| `$FA` | 2 | `$149F` | Set global note/instrument offset byte `$41` |
| `$FB` | 1 | `$14A6` | Set per-voice one-shot flag `$02A0+x` |
| `$FC` | 2 | `$14AC` | Set record pitch-multiplier suppression override |
| `$FD` | 3 | `$14B3` | Set per-voice `ADSR1`/`ADSR2` override |
| `$FE` | 4 | `$14C0` | Set per-voice sample and Q8.8 pitch override |
| `$FF` | 1 | `$14D8` | No state change; returns with carry clear |

Names remain structural where downstream DSP or musical meaning is not yet
proved. In particular, the transition and modulation families are not assigned
conventional music-engine command names merely from similarity to other drivers.

## S-CPU/APU command protocol

SPC `$168A` polls CPU ports `$F4-$F7`, snapshots them into direct-page bytes
`$10-$13`, acknowledges through the same ports, and divides command byte `$F4`
into these reachable classes:

- `$01-$1F` select an entry through the pointer table whose address is held in
  direct-page `$24-$25`;
- `$20-$3F` select the same structure after masking the command to five bits;
- `$40-$7F` subtract `$60` and store the result at SPC `$06A0`;
- `$80-$97` dispatch through the 24 little-endian entries at `$17EA-$1819`;
- `$F0` toggles the same primary-voice processing state changed by `$81/$82`;
- `$F1` toggles global byte `$0180`;
- `$FD` clears APU RAM from page supplied in port `$F7` through page `$FE`;
- `$FE` transfers control to the SPC IPL-ROM entry at `$FFC0`;
- `$FF` enters the standard upload receiver at `$1885`.

The `$80-$97` table is:

| Command | Handler | Confirmed structural effect |
| --- | --- | --- |
| `$80` | `$181A` | Stop/reset primary voices `$00-$07` through `$1553` |
| `$81` | `$181E` | Set primary-voice processing flag `$4A`; request key-state refresh |
| `$82` | `$1825` | Clear `$4A` and the `$51/$52` transition state |
| `$83` | `$182F` | Set `$52=2`, `$51=$FF` |
| `$84` | `$1836` | Set `$52=3`, `$51=$FF` |
| `$85` | `$183D` | Copy voice 1 selector to voice 0 and set `$52=1`, `$51=1` |
| `$86` | `$184D` | Clear output-mode byte `$49`; use per-voice positioning values |
| `$87` | `$1851` | Set output-mode byte `$49`; force the fixed centered-volume path |
| `$88` | `$1855` | No state change |
| `$89` | `$1856` | No state change |
| `$8A` | `$1857` | Copy port `$F7` to DSP sample-directory base register `DIR` |
| `$8B` | `$1862` | Set instrument-record base pointer `$22-$23` from `$F6-$F7` |
| `$8C` | `$186D` | Set primary sequence-structure pointer `$24-$25` from `$F6-$F7` |
| `$8D` | `$1878` | Set secondary sequence-pointer table `$26-$27` from `$F6-$F7` |
| `$8E` | `$1883` | No state change |
| `$8F` | `$1884` | No state change |
| `$90` | `$1884` | No state change; aliases `$8F` |
| `$91` | `$18C8` | Toggle global multiplier-enable byte `$0180` |
| `$92` | `$18D1` | Toggle one `$0630+x` multiplier flag, or clear all 16 flags |
| `$93` | `$18EF` | Configure global echo state from `$F6-$F7` and invoke echo setup |
| `$94` | `$18FA` | Configure echo state and load a selected FIR table |
| `$95` | `$190C` | Select and load a FIR table using `$F6` |
| `$96` | `$1913` | Clear global echo state |
| `$97` | `$1916` | Set voice 0 bytes `$0400` and `$0340` from `$F6-$F7` |

The labels “primary” and “secondary” describe the driver's two voice groups and
pointer paths, not narrative roles such as music versus sound effects. Runtime
or caller evidence is still required before assigning those higher-level names.

## Reachable main-driver structure

The `$0800-$1920` block is confirmed SPC700 driver content because every
bootstrap package terminates with execution address `$0800`. The repository
wrapper now expands the vendored decoder's obsolete dynamic opcode dispatch into
an explicit 256-way dispatch for Asar 1.91. Linear output is still treated only
as a review aid: embedded tables such as `$1182-$11C1`, `$143E-$1465`, and
`$17EA-$1819` must not be interpreted as instructions.

Confirmed reachable landmarks include:

| SPC address | Confirmed role |
| --- | --- |
| `$0800` | entry; initializes stack, clears direct page and `$0100-$07FF` |
| `$082D-$0847` | clears CPU ports `$F4-$F7`, configures control `$F1`, timer target `$FA`, and timer 0 |
| `$0893` | timer-driven main loop using counter `$FD` |
| `$0FA4` | DSP write helper: writes Y to `$F2`, A to `$F3` |
| `$0FAB` | DSP read helper: writes Y to `$F2`, reads A from `$F3` |
| `$1175` | dispatches `$E0-$FF` sequence commands through table `$1182-$11C1` |
| `$168A` | S-CPU/APU-port command polling and acknowledgement through `$F4-$F7` |
| `$17DD` | dispatches 24 port commands through table `$17EA-$1819` |
| `$1885` | standard `$AA/$BB/$CC` SPC upload handshake and byte receiver |

Initialization writes DSP `FLG`, `KOF`, `PMON`, `NON`, `DIR`, and echo-related
registers before entering the main loop. The port-command table contains 24
little-endian routine addresses from `$181A` through `$1916`; individual command
names remain unresolved unless their effects are explicit in the target routine.
