# Battle HUD text path

## Confirmed runtime findings

The finals battle UI containing the anonymous-fighter name, HP label, action
names, and status labels does **not** use the command-`$08` dialogue renderer at CPU `$80:9A0E`.
It is a separate BG3, 2bpp tile-text path.

The current translated-ROM replay from the retained finals state confirms:

- BG3 uses VRAM character base `$0000` and tilemap byte offset `$5800` during
  the Goku/anonymous-woman battle screen.
- The four visible fields use sequential generated tile ranges:
  - top-left fighter name: tiles `$020-$036`
  - bottom-left HP label/value: tiles `$038-$04E`
  - top-right action/status: tiles `$050-$072`
  - bottom-right status: tiles `$074-$096`
- Those tile strips are assembled in WRAM and uploaded to VRAM; they are not
  stored as an uncompressed contiguous tile strip in ROM.
- CPU `$80:9CFA` decompresses a source selected by a 16-bit address in A and a
  source bank in X into WRAM `$7E:8000`.
- CPU `$80:9DA7` calls that decompressor and performs a second conversion before
  the generated data is uploaded to VRAM.
- The first battle-setup resource is compressed ROM data at CPU `$B0:8000`, ROM
  offset `$180000`. Its two-byte header gives a decompressed length of `$4000`.
  This resource is part of the common battle setup, but it is **not** the source
  of the four visible Japanese text strips.
- The base compression format is confirmed from CPU `$80:9CFA`: groups of eight
  flag bits select literals or 16-bit backward references. A reference stores a
  12-bit distance in bits 4-15 and a run length of 3-18 bytes in bits 0-3.
- Nonzero writes during HUD construction execute at CPU `$80:9D47` and
  `$80:9D96`, inside the decompression/copy path.
- The ordinary 16x16 dialogue compositor at CPU `$80:9B2C` is not called while
  the battle HUD is initialized.
- The final visible text is generated into WRAM and uploaded as four independent
  2bpp strips from `$7E:8000`:
  - fighter name: `$0180` bytes to VRAM word `$0100` (tiles `$020-$037`)
  - HP label/value: `$0180` bytes to VRAM word `$01C0` (tiles `$038-$04F`)
  - action/status: `$0240` bytes to VRAM word `$0280` (tiles `$050-$073`)
  - lower status: `$0240` bytes to VRAM word `$03A0` (tiles `$074-$097`)
- CPU `$82:9159` is one confirmed writer in the strip workspace; CPU `$80:992A`
  initializes the bitmap, and CPU `$80:9CBE/$80:9CF0` converts it into the
  uploaded 2bpp layout. These generated strips therefore need to be translated
  through their source tables/compositor path rather than by editing `$B0:8000`.
- CPU `$82:EE8C-$82:EF28` constructs the fighter-name stream. Ordinary fighter
  records are fixed eight-word slots at CPU `$84:BF16`; record zero contains
  `匿名希望` (Anonymous) and is selected by the recognition-bit-clear Goku/Chi-Chi
  battle HUD. Special opponents use
  the separate fixed-slot table at CPU `$84:C096`.
- CPU `$82:9843` writes the three-word HP prefix, appends the dynamic value, and
  renders it to VRAM word `$01C0`. CPU `$82:9888` initially does the same for
  the three-word battle-power prefix and VRAM word `$03A0`; the action renderer
  at CPU `$82:98D4` later reuses that strip.
- CPU `$82:9931` copies the selected action/technique stream through pointer
  table CPU `$84:C550` and renders it to VRAM word `$0280`. Runtime records
  selector `$0091`, which resolves to CPU `$84:CBE2`; this is byte-identical to
  the Dash Punch source allocation at CPU `$84:CA10`, now identified as action
  index `$0038`. Their action records remain distinct: index `$38` selects
  `$84:D11A`, while index `$91` selects `$84:D1F3`; equal displayed names do not
  imply equal mechanics. CPU `$82:98D4` records
  selector `$0002`, which resolves to CPU `$84:C6EA` (Homing Ki source) for the
  bottom-right strip. The uninterrupted replay later changes the selectors to
  `$0084` at frame 1060 (CPU `$84:CB16`, body-check/rush source). At frame 1066,
  `$0E40` is `$FFFF`, so CPU `$82:98D4` selects the fallback stream at CPU
  `$82:F6FD`, rendered as an unguarded/open state.
- The translated build now uses the existing packed-Latin compositor for these
  sources: `Anonymous`, `HP`, `Power`, both `Dash Punch` allocations, `Homing Ki`,
  `Rush`, and `Open`. Numeric conversion calls, strip dimensions,
  terminators, and VRAM destinations remain unchanged.

The historical runtime verification used translated ROM SHA-256
`d7d0552999dde2c7480093968a6c86a070eb5c74d3dfcb974f3ff3c9a1d7faa7` and
the retained pre-HUD state. The initial capture at
`local/runtime/chichi-hud-english-initial-final-20261019/frame.png` displays
the superseded `Tien`, `Dash Punch`, `HP 1000`, and `Homing Ki` patch. Static
source-glyph review subsequently established that this record is `匿名希望`
(`Anonymous`), not Tien (PNG SHA-256
`8bf5631af54b4a4bd697bea9ddf95e6ba5aad93a139b39b1cf627465dfd93cea`).
The later capture at
`local/runtime/chichi-hud-english-later-verified-20261019/frame.png` shows
the same superseded `Tien`, `Rush`, `HP 920`, and `Open` patch (PNG SHA-256
`80f7b507523ed2609633dd0c09a3dc6a5f36f1d2a306a83cfdcf6c82e4788af2`).
Both runs exited successfully, and the changing HP value confirms that dynamic
numeric rendering remains active.

## Recognized-route first-HUD boundary

A bounded current-ROM replay beginning from the retained recognized Chi-Chi
state continued through scenario root `$0013`. It executed untranslated selectors
through `$0309`, then reached command `$47` at CPU `$91:9931`. The common battle
setup began with decompression of CPU `$B0:8000` at relative frame 10551. This is
the first established later battle-HUD boundary on the recognized route.

The intervening route is not translation-complete: the replay observed selectors
`$02E4-$0309` plus shared selectors `$0000`, `$0003`, and `$000B` after the
previously translated `$02C6-$02CA` branch. Earlier frames in the retained
continuation also include `$02D6-$02E3`. These resources must be audited and
translated before coverage through the recognized route's first HUD can be
claimed.

The ignored evidence is retained under:

```text
projects/dbz-kakusei-hen/local/runtime/chichi-recognized-continue-20261019-033430/
```

The deterministic codec in `src/dbz_kakusei_hen/battle_hud.py` now models the
base decompressor, the `$80:9DA7` interleave, bounded replacement, and greedy
recompression. Tests pin six observed battle resources by decompressed length,
compressed extent, and decompressed SHA-256. The two primary `$B0` resources
recompress to their exact original sizes; other observed streams currently vary
by at most seven bytes while decoding byte-identically.

The relevant ignored runtime captures are under:

```text
projects/dbz-kakusei-hen/local/runtime/chichi-hud-vram-current-887c675b-20261018/
projects/dbz-kakusei-hen/local/runtime/chichi-hud-decompress-887c675b-20261018/
projects/dbz-kakusei-hen/local/runtime/chichi-hud-nonzero-887c675b-20261018/
```

## Remaining work

Replay both recognized and unrecognized routes through uninterrupted first-HUD
captures and extend the source manifest to additional fighter and technique
records as those routes select them. Continue tracing CPU `$82:9159`,
`$80:9CBE`, and `$80:9CF0` for lower-level compositor documentation. The codec
is ready for any compressed resources that do need edits, but the generated
labels must not be misattributed to `$B0:8000`.

## Goku/Chi-Chi HP and battle-result dialogue

Runtime comparison of the retained Goku/Chi-Chi battle states establishes WRAM
`$0E66` as Goku's displayed current HP: it is `$03E8` when the HUD displays 1000
and `$0398` when the HUD displays 920. Battle initialization at CPU `$82:8D65`
loads `$0E66` from the selected player record and `$0E68` from the encounter
record; both begin at `$03E8` in this battle.

The damage routines establish the terminal flags without relying on dialogue
interpretation:

- CPU `$82:9E1F-$82:9E36` subtracts Goku's attack damage from `$0E68`; zero sets
  `$0E25 = $0002`.
- CPU `$82:9F10-$82:9F27` subtracts the opponent's damage from `$0E66`; zero sets
  `$0E25 = $0200`.
- CPU `$82:8156-$82:816C` tests `$0E25 & $0202` and exits the active battle loop.
- CPU `$82:D0C0-$82:D0F6` selects the result-script table. Bit `$0002` set uses
  CPU `$B5:C5AC` (opponent/Chi-Chi defeated); otherwise it uses CPU `$B5:CC74`
  (player/Goku defeated).

For encounter index `$0000`, the exact battle-script entries and text resources
are:

- opening: CPU `$B5:BB1E`, resources `$1000-$1001`;
- Chi-Chi at 0 HP: CPU `$B5:C64C`, resources `$1180-$1190`, then shared
  `$10B6-$10B7`;
- Goku at 0 HP: CPU `$B5:CD14`, resources `$10B8-$10B9`.

Battle-script text opcodes `$02` and `$03` use the two opposing on-field
presentations. The opening runtime capture visibly establishes opcode `$02` as
Goku, so opcode `$03` is Chi-Chi. Opcode `$01` uses the wider explanatory text
presentation. These battle resources are distinct from scenario command `$08`;

## Junior battle (encounter $0003)

Runtime comparison of the retained Junior battle states establishes the complete battle lifecycle:

- Encounter index: WRAM `$0E2B = $0003`
- Opening script: CPU `$B5:BB5A`, resources `$1006-$1007` and `$11AB-$11AC`
- Win script (opponent defeated): CPU `$B5:C718`, resources `$11A4-$11A9` and `$10BE-$10BF`
- Loss script (player defeated): CPU `$B5:CD44`, resources `$10C0-$10C4`

The result-script table at CPU `$82:D0C0` selects based on `$0E25 & $0002`:
- Bit set: win table CPU `$B5:C5AC` (opponent/Junior defeated)
- Bit clear: loss table CPU `$B5:CC74` (player/Goku defeated)

Battle-script text opcodes `$02` and `$03` use the two opposing on-field presentations.
The opening runtime capture visibly establishes opcode `$03` as Junior, so opcode `$02` is Goku.

The win path continues into root `$0019` with selectors `$03A2-$03AB` plus shared `$0011` and `$0002`.
The loss path continues into root `$001C` with selectors `$096C-$0976`, leading to game over via
King Piccolo's resurrection.

These battle resources are distinct from scenario command `$08`; the battle-script resources use
bank `$B4`'s `$1000`-based pointer table rather than the command-`$08` selector tables.
the earlier scenario-root `$000E` candidates are not the HP-zero dialogue path.