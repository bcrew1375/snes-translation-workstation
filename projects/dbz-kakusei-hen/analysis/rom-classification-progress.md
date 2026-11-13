# ROM classification progress

This note records the evidence-backed expansion of `analysis/project.json`
through complete physical-byte classification. The immutable original ROM
remains the source of truth, and every batch retained a byte-identical
`make verify PROJECT=dbz-kakusei-hen` result.

The detailed structure list below is chronological investigation history. A
few bullets preserve wording such as “unknown” or “unresolved” from earlier
checkpoints; those statements describe the evidence state at that checkpoint,
not the final coverage state. Every physical byte now has a classification,
while some classified data/resource regions intentionally retain a partial or
unknown internal schema.

## Current coverage

- ROM size: 2,097,152 bytes
- Classified: 2,097,152 bytes (100.000000%)
- Unknown: 0 bytes

Current effective categories (smaller nested regions override broad
containers in coverage statistics):

| Category | Bytes |
| --- | ---: |
| audio | 169,559 |
| battle_script_data | 53,184 |
| code | 110,837 |
| compressed_resource | 554,239 |
| fill | 288,284 |
| graphics | 431,403 |
| padding | 34,554 |
| pointer-table | 34,326 |
| data | 53,221 |
| text | 281,456 |

The initial baseline was 300,750 classified bytes (14.3409%). The current work
has therefore classified 1,796,402 additional bytes without changing the ROM.
The descriptor-matrix and associated configuration hierarchy added 255,488
classified bytes beyond the prior 1,421,244-byte checkpoint.

The latest bank-`$83` pass added 18,025 evidence-backed bytes: exact external
entries and closed local call families, all scenario command handlers selected
by the 73-word `$83:B2A7` dispatch table, the `$83:D3F7-$D427` terminated HDMA
radius sequence, and consumer-bounded configuration tables/patterns from
`$83:A60E-$B20B`. Apparent call-like operands were not accepted unless their
instruction context or independently proven target ownership was established.

## Classification distinctions

- `padding` means the range has stronger evidence for unused/reviewed storage,
  such as a bounded text-corpus tail, explicitly reviewed translation space,
  or an exact separator excluded from both neighboring codec/stream extents.
- `fill` means the bytes are structurally homogeneous (`$FF` or `$00`) and the
  recorded checks found no exact 24-bit pointer to the range start. It is **not**
  a free-space or allocatability claim.
- `scenario_data` means the scenario root table gives lossless ownership of the
  bytes. The command schema is still partial, so the range is not called CPU
  code or fully decoded bytecode.
- `battle_script_data` similarly records table-owned battle-script blocks while
  leaving the incomplete opcode schema explicit.
- `compressed_resource` means the `$80:9CFA` codec decodes an exact consumed
  extent to a pinned output size/digest. It does not claim that every decoded
  payload is graphics.
- `audio` means an S-CPU upload stream or BRR record is losslessly bounded by
  the confirmed `$83:8000-$828B` uploader. SPC700 payload bytes remain distinct
  from 65C816 code even where the payload itself contains executable APU code.

## Confirmed structures added

- Bank `$80` reset, NMI, and controller core:
  - reset continuation `$80:8012-$82A3`, the NMI-vector module
    `$80:82A4-$8627`, interrupt/controller initializer `$80:8628-$864F`, and
    five independently entered interrupt/input helpers through `$80:86F5` are
    bounded by decoded entries, vector ownership, local control flow, and
    terminal `RTS`/`RTL` instructions;
  - the unentered bytes `$80:8650-$865D` remain unknown rather than being swept
    into the adjacent helpers.
  - ten additional independently entered PPU, input, synchronization, and fade
    routines are bounded through `$80:897B`; sibling-shaped but unentered
    helpers `$80:86F6-$8720` and `$80:88E8-$8905` remain unknown.
  - palette transition helpers `$80:8A31-$8B81` and WRAM transition helpers
    `$80:8C37-$8CF5` are bounded by decoded entries and terminal returns. The
    latter two consumers prove exact seven-word forward/reverse mask tables at
    `$80:8CB0-$8CBD` and `$80:8CF6-$8D03`.
  - multiplication/division and decimal/nibble rendering routines are exactly
    partitioned across `$80:8EDE-$918E`, including the sixteen-word glyph table
    `$80:9137-$9156`. The unentered `$80:90B1-$90DA` routine and random-state
    data beginning at `$80:918F` remain unknown.
  - threshold search `$80:92A1-$9352` proves the complete 257-word monotonic
    table `$80:9353-$9554`; renderer initialization and glyph-rendering code is
    bounded through `$80:97F8`, followed by exact text-buffer helpers at
    `$80:9839-$98B1` and `$80:98E3-$997A`.
  - the text-stream renderer and glyph compositor are bounded across
    `$80:997B-$9CF9`, preserving the nested translation hook at `$80:9B2C`, and
    the separately entered back-reference codec is bounded at `$80:9CFA-$9DA6`.
  - decoded-output transfer `$80:9DA7-$9E2E` and the reset-time diagnostic
    workflow `$80:9F2B-$A5DA` are partitioned into code, bounded code-pointer
    and text-pointer tables, renderer streams, fixed graphics/palette sources,
    and seven selector-owned coordinate records. The exact 16-byte timestamp
    consumed by `$80:A259` is classified at `$80:FF80-$FF8F`.
  - compact decoded helpers `$80:ABEA-$AC23` and `$80:AF73-$AFDF` are bounded
    by explicit returns. The setup workflow `$80:B548-$B681` proves a seven-way
    local code-pointer table at `$80:B682-$B68F`; its distant targets remain to
    be partitioned individually.
  - the bank-`$89` control-stream dispatcher at `$80:CAFB-$CB89` proves an exact
    47-word opcode table at `$80:CB8A-$CBE7` for values `$00-$2E`. Entry `$00`
    is null; entries `$01-$04` target the bounded handler family
    `$80:CBE8-$CEF9`, and entries `$05-$2E` target `$80:CFBD-$D8AB`. The first
    handler begins immediately at `$80:CBE8` with `PHP; SEP #$20`, which proves
    that those bytes are code rather than a speculative `$2F` table entry.
    Separately entered helpers `$80:CEFA-$CFBC` and `$80:D8AC+` remain excluded
    from dispatch-handler ownership.
  - opcode handler `$01` installs callback entry `$80:DA9A` into the vector at
    `$0379-$037B`. From that entry, all 25 local `JSR` targets and all local
    branch paths remain inside the contiguous callback family
    `$80:DA9A-$E190`, which ends at an explicit `RTS`. The following byte
    `$80:E191` begins callback animation tables rather than code. Exact consumer
    domains classify six fully consumed blocks at `$80:E191-$E23A`,
    `$80:E3A3-$E506`, `$80:E59F-$E5FE`, `$80:E617-$E632`,
    `$80:E6DB-$E716`, and `$80:E7D7-$E8D6`. Padded record families between and
    after these blocks are now bounded as ten complete fixed-stride tables from
    `$80:E23B-$EA56`; their record counts and strides come directly from index
    multiplication and explicit counter wraps, and their zero-valued trailing
    fields are owned record padding. The unrelated gaps `$80:E39B-$E3A2` and
    `$80:E507-$E51E` remain unknown. The `$80:EA57` selector table remains
    blocked by the unresolved global `$029C` domain.
  - the uniform `$FF` continuation `$80:EDB3-$FF7F` follows the reviewed
    translated allocation ending at `$80:EDB2` and has no exact 24-bit pointer
    to its start. It is classified conservatively as `fill`, not approved free
    space; the diagnostic timestamp begins separately at `$80:FF80`.
  - the separate uniform `$FF` gap `$80:FF90-$FFAF` lies between that exact
    timestamp and the extended-header lead-in. All three apparent 24-bit
    references to `$80:FF90` occur inside confirmed compressed payloads, so the
    gap is recorded conservatively as `fill`.
  - the first five targets of `$80:B682` are now closed mechanically at
    `$80:B690-$B6E6`, `$80:B6E7-$B722`, `$80:B723-$B7D8`, `$80:B7D9-$BAFF`,
    and `$80:BB00-$BCA1`. The sixth target retains an unresolved inline dispatch
    table whose `$3B` index domain has not yet been proved.
  - the sixth target is safely bounded only through its pre-dispatch code at
    `$80:BCA2-$BDEA`; the seventh target is closed at `$80:C1B1-$C2D2`.
    Seven direct renderer helpers occupy `$80:C2D3-$C538`, owning the continuous
    stream `$80:C96B-$CA50`, source `$80:CA51-$CA72`, and the five reachable
    `$80:CA73` text-fragment records. Unread separator words remain unknown.
  - the wrapped `$0272` domain proves all 128 words of pointer table
    `$80:C539-$C638`. Its target-list corpus remains unresolved because heavily
    used odd pointer `$C679` does not encounter a nearby low-byte `$FF` sentinel
    under the consumer's two-byte traversal, so no target extent is inferred.
  - decoded entries `$80:CAFB-$CB89`, `$80:CEFA-$CFBC`, `$80:D8AC-$D96D`,
    `$80:D96E-$D98B`, and `$80:D98C-$D9DF` are bounded at explicit returns.
    `$80:CAFB` also proves direct helper `$80:DA80-$DA99`; the four preceding
    bytes at `$80:DA7C-$DA7F` remain unknown.
- Bank `$B6` fixed palette sources:
  - `$B6:8020-$805F` and `$B6:8060-$809F` are each copied by a decoded fixed
    `$40`-byte MVN helper at `$80:97C5` and `$80:97DF` respectively;
  - only `$B6:8014-$801F` remains unknown between the established glyph-code
    table and these palette blocks.
- Bank `$82` encounter numeric-adjustment table:
  - `$82:F793-$F992` is exactly 64 stride-`$08` records selected through
    `$0E2B * 8` by CPU `$82:E797`;
  - the consumer reads words at `+$00`, `+$02`, and `+$04`, while every record's
    `+$06` word is zero;
  - the 64-record extent ends exactly at the independently classified
    `$82:F993` side-selection table. The individual field semantics remain only
    partially understood, so the region is recorded as
    `confirmed_structure_partial_schema`.
- Bank `$AE` fixed CGRAM palette:
  - `$AE:A2EC-$A30B` is copied word-for-word to WRAM `$04C0-$04DF` by the
    explicitly bounded loop at CPU `$82:B3F0` (`CPX #$0020`);
  - the exact 32-byte block follows the codec stream ending at `$AE:A2EA` with
    one unread byte at `$AE:A2EB`, and ends immediately before the confirmed
    `$FF` bank tail at `$AE:A30C`.

- Bank `$82` encounter and display lookup tail:
  - `$82:F705-$F749` is the exact sliding 16-bit lookup span indexed directly by
    the closed encounter domain `$0E2B = $00-$43`; the final index consumes the
    overlapping word at `$F748-$F749`, while `$F74A-$F74C` remains unread;
  - `$82:F74D-$F761` and `$82:F762-$F77A` are sequential byte search lists whose
    consumers stop at their terminal `$FF` bytes;
  - `$82:F77B-$F792` is a 24-byte lookup with an explicit `CPX #$0018` bound;
  - `$82:F993-$FA1A` contains 68 words indexed by `$0E2B << 1`, exactly covering
    the proven `$00-$43` encounter domain, and `$82:FA1B-$FA36` is the following
    zero-terminated display stream. The guard-dependent numeric table at
    `$82:F793-$F992` remains unresolved.
- Bank `$84` battle display and coordinate hierarchy:
  - `$84:BF16-$C105` contains 31 fixed `$10`-byte zero-terminated records: 24
    selected by fighter/configuration IDs `$00-$17`, plus seven special records
    selected at offsets `$00,$10,...,$60` from `$84:C096`;
  - `$84:C106-$C225` is three consecutive 24-record coordinate-delta arrays,
    four bytes per record. All 68 encounter descriptors selected through
    `$AD:A080` use the exact fighter index set `$00-$17`;
  - `$84:C226-$C22B` is a three-entry pointer table selected by menu state
    `0..2`; targets `$C22C/$C374/$C4BE` losslessly partition three
    zero-terminated display streams through `$84:C54F`, immediately before the
    independently indexed action-name table at `$84:C550`.

- Bank `$81` name/password entry continuation:
  - `$81:8EAA-$939E` is the unique same-bank `JSR`-entered setup and interactive
    entry routine reached from the already bounded menu workflow. Its only
    absolute local calls target `$81:9334` and `$81:936C`, all absolute local
    jumps remain inside the interval, and the routine ends at the `RTS` at
    `$81:939E`;
  - `$81:939F-$9426` contains 68 two-byte cursor-coordinate records. The
    `$81:9334` consumer indexes them with `$022B * 2`; insertion caps `$022B` at
    `$43`, so the final valid lookup consumes exactly `$81:9425-$9426`;
  - `$81:9427` remains the independently entered next routine, preserving the
    exact code/data/code boundary.

- Bank `$82` battle-controller prefix:
  - `$82:8000-$8BD7` is the complete externally entered controller module rooted
    at seven exact `JSL $82:8000` call sites. It contains the closed local
    state-machine routines through the `RTS` immediately before `$82:8BD8`;
  - `$82:8BD8-$8BDF` contains four local handler words
    `$8BE0/$8C4A/$8C71/$8C7E`. The three dispatch sites index this table with
    `$0E23 * 2`, while its handlers and initializer assign only states `0..3`;
  - `$82:8BE0-$8F1F` contains those handlers and the shared initializer ending
    in `RTL`. `$82:8F20-$8F4F` is a separate 24-word `$08F0` lookup indexed by
    the established entity selector domain `$00-$17`;
  - `$82:8F50-$9286` contains the independently called PPU/setup, frame-rendering,
    palette, and resource helpers. The final `RTL` at `$82:9286` preserves the
    existing boundary before the nine-entry palette-source table at `$82:9287`.
  - `$82:92A2-$9842` is the adjacent closed battle helper family entered by
    exact `JSL` targets `$82:92A2/$92BE/$92D8/$9313/$93FE/$9465`. All local
    `JSR`/`JMP` targets stay within the interval, whose final `RTS` at `$82:9842`
    preserves the exact boundary before the independently classified HUD routine
    at `$82:9843`.
  - `$82:D6C3-$E20A` contains four adjacent externally entered visual-transition
    routines with exact `RTL` boundaries, and `$82:E20B-$E695` contains the fifth
    transition routine through its own terminal `RTL`. The unrelated routine at
    `$82:E696` remains unknown rather than being absorbed into the entry extent;
  - `$82:EDFB-$EE29` is the 47-byte bitset helper reached by 65 exact long calls.
    Its input selects a word and bit in WRAM `$0D2E`, and its terminal `RTL`
    establishes the exact end without classifying the following helper family.
  - the classified controller and transition routines also own the closed local
    helper partitions `$82:E696-$E77B`, `$E77C-$E7DA`, `$E7DB-$EDFA`,
    `$EE2A-$EE7A`, `$EE7B-$EE8B`, `$EE8C-$EF2B`, and `$EF2C-$F01B` through exact
    local `JSR` references and terminal `RTS` boundaries. The unreferenced
    `RTL` routine beginning at `$82:F01C` remains unknown rather than being
    inferred solely from linear decoding.

- Command-`$08` text-bank tails in banks `$98-$9F`.
- Scenario bank tails and the complete root-owned ranges in banks `$91-$93`.
- Reviewed HUD, menu, name-entry, fixed-label, choice, and battle-text records.
- Six runtime-observed LZ resources with exact compressed extents.
- Two CPU `$94` three-byte source descriptor arrays and 67 unique resources
  selected through them.
- Two 80-record CPU `$81` loader tables at `$81:D6C6` and `$81:D8BF`, plus 100
  newly classified unique resources selected by those tables. Each five-byte
  record contains a source address, source bank, and transfer length. All
  non-null records decode successfully through the confirmed codec; two
  interleaving-table transfer lengths differ from the codec header and are
  pinned explicitly in regression tests.
- Complete portrait-resource hierarchy rooted at CPU `$83:EE97`:
  - 128 root pointer slots and 125 unique descriptor targets;
  - a lossless variable-length descriptor partition at `$83:EF97-$F392`;
  - 340 three-byte source address/bank records;
  - 219 unique codec-valid compressed streams totaling 168,414 compressed
    bytes, with decoded lengths from `$00A0` through `$0400`.
- Complete paired battle-presentation script banks:
  - CPU `$AB:8000-$84FF` and `$AC:8000-$84FF` are parallel 640-slot monotonic
    same-bank pointer tables selected through CPU `$82:A053`;
  - bank `$AB` has 342 unique real streams partitioning `$AB:8500-$DBA7`, while
    bank `$AC` has 364 partitioning `$AC:8500-$E848`;
  - every unique stream terminates with opcode `$00`, and 192 slots in each table
    repeat the exact first address of the already classified all-`$FF` bank tail;
  - CPU `$82:A100` and `$82:B459` are the respective side-specific interpreters.
    Ownership and boundaries are confirmed even though the full opcode schemas
    remain partial.
- Complete battle-presentation selection hierarchy in bank `$AF`:
  - `$AF:8000-$838F` is a 19x48 byte group lookup indexed from the two current
    action-record lookup values;
  - `$AF:8390-$83F5` contains three 34-byte outcome-specific fallback tables;
  - `$AF:83F6-$BBF5` is exactly 448 fixed 32-byte group records, each containing
    eight bank-`$AB` and eight bank-`$AC` script IDs with `$FFFF` unused slots;
  - the confirmed byte selector reaches groups `$00-$FE`. Records `$100-$1BF`
    remain structurally valid but unreachable from that path. The final record's
    trailing 14 `$FF` fields refine the start of the formerly broad bank-tail fill.
- Two additional exact loader-owned codec resources:
  - CPU `$81:D86F` selects `$B1:8000`; 11,422 compressed bytes decode to its
    exact `$3A00` transfer length;
  - CPU `$81:D879` selects `$B2:8000`; 10,473 compressed bytes decode to its
    exact `$3000` transfer length. Byte `$B2:A8E9` immediately after the codec
    extent is not consumed and remains unknown rather than being absorbed into
    either adjacent resource.
- CPU `$82:9287-$92A1` is a nine-entry 24-bit battle-palette source table.
  CPU `$82:922F` indexes it with `3 * $0E29` and copies exactly 64 words from
  the selected source into WRAM `$0440-$04BF`. The nine exact `$80`-byte source
  blocks are now classified as palette graphics. This closes the complete
  `$18E952-$18EA51` and `$1978C0-$19793F` gaps while preserving unowned bytes
  immediately before sources `$B0:BCF2` and `$B2:D7DA`.
- Six further CPU `$81:D8BF`-family loader records own codec streams in physical
  banks `$30-$32`. Each stream decodes to its record's exact transfer length and
  has a pinned output digest. Three streams end exactly at the next classified
  resource; the streams ending at `$18688E`, `$1959F2`, and `$197180` each leave
  one following byte unconsumed and explicitly unknown.
- Complete bank `$B3` object-layout hierarchy:
  - `$B3:8000-$851F` is a 656-slot same-bank pointer table used by CPU `$80:9650`
    for global object-layout indexes `$06B0-$093F`;
  - 360 unique targets partition `$B3:8520-$DD03` without gaps;
  - `$B3:8520` is the shared one-byte empty stream and every stream ends in the
    renderer's `$80` terminator;
  - each object entry contains one control byte followed by four bytes that the
    renderer writes into a WRAM `$7E:2000` OAM staging record. The detailed control schema remains
    partial, but ownership, boundaries, records, and termination are confirmed.
- The same CPU `$80:95F0` renderer establishes the two preceding object-layout
  banks:
  - `$85:8000-$86DF` contains 880 slots for global indexes `$0000-$036F`; 82
    slots are null and 798 are active. Referenced streams cover `$85:86E0-$F546`
    exactly, with several intentional interior aliases near the first stream;
  - `$86:8000-$867F` contains 832 active slots for indexes `$0370-$06AF` and
    425 unique streams partition `$86:8681-$F5D4` exactly;
  - every active target reaches `$80` on the interpreter's five-byte object-entry
    stride. Standalone `$86:8680` is not selected and remains unknown.
- Complete bank-`$89` control-stream selector hierarchy:
  - CPU `$80:DA7C` indexes 370 same-bank words at `$89:8000-$82E3` with the full
    established WRAM `$029C` domain `$0000-$0171`;
  - slots `$0161-$016E` are null; 356 active slots resolve monotonically to 355
    unique entry points in `$89:82E4-$930A`;
  - entries can target shared/interior control-flow positions and therefore do
    not define independent terminated streams. The final selected entry occupies
    `$89:930A-$930F` and ends in `$FF`; `$89:9310` begins a separately
    `JSL`-referenced routine.
- CPU bank `$A0` battle graphics and animation data:
  - `$A0:8000-$83DF` contains three fixed, 24 selector-indexed, and four special
    32-byte SNES palette records copied in exact 16-word loops;
  - `$A0:879E-$AE5D` contains four exact `$0800`-byte tile blocks plus fixed and
    selector-indexed 32-byte palette families. All 68 bank-`$AD` configuration
    records establish the complete entity-selector domain `$00-$17`;
  - `$A0:AE5E-$B684` contains several bounded timing/frame arrays with modulo
    counts 16, 8, 32, and 5. Only bytes reached by their explicit stride and copy
    bounds are classified;
  - five alignment gaps totaling 38 bytes remain unknown rather than being
    absorbed into adjacent animation records.
- Complete bank-`$98` choice-resource hierarchy:
  - `$98:9B2A-$9E29` contains 384 monotonic same-bank pointer slots;
  - the first 373 slots are unique targets that partition `$98:9E2A-$C1C7` into
    gap-free even-sized streams, each ending in word `$0000`;
  - the final 11 slots contain sentinel `$C1C8`, exactly the start of the separate
    command-`$08` selector table. Existing reviewed quiz, Chi-Chi, finals, and
    Shenron option records are nested within the complete corpus;
  - this closes physical bank `$18` completely without changing any existing
    reviewed stream boundary.
- Bank-`$94` palette-source hierarchy:
  - `$94:8180-$81FF` contains 64 same-bank source words selected by menu and
    scenario value `$0270`;
  - 44 active slots resolve to 40 unique `$40`-byte records and 20 slots are
    null. The active target set is exactly every `$40`-byte boundary from
    `$94:8200` through `$94:8BC0`;
  - `$94:8200-$8BFF` is therefore a complete contiguous 40-record SNES palette
    corpus copied by bounded `MVN` operations. Independently decompressed source
    `$94:8C00` establishes the following format boundary.
- Bank-`$94` descriptor and fixed-resource completion:
  - the primary `$94:8000` and secondary `$94:80C0` arrays are each complete
    64-record, three-byte descriptor tables. Both contain 44 active slots and 20
    null slots; populated slots `$30/$31` and null tail `$32-$3F` match the
    selector domain established for the companion palette table;
  - hard-coded source `$94:8C00-$8D12` is a separate 275-byte compressed
    resource used by four `$80:9DA7` callers. It decodes to `$03C0` bytes before
    the confirmed 16-byte block interleave. Byte `$94:8D13` is not consumed and
    remains unknown;
  - physical bank `$14` is now 32,761 / 32,768 bytes classified. Its seven
    remaining isolated bytes are deliberately outside exact codec extents.
- Bank-`$B6` reachable glyph-code lookup prefix:
  - `$B6:8000-$8013` contains ten 16-bit renderer codes `$0260-$0267` and
    `$0270-$0271`;
  - battle status writers prove indexes `$00-$07`, while the fixed diagnostic
    timestamp at `$80:FF80` proves decimal indexes `$00-$09`;
  - following words `$B6:8014-$809F` remain unknown because no consumer bound
    currently proves entries `$0A` or above.
- Deliberately unresolved bank-`$B4` pointer-looking tail:
  - `$B4:8704-$87FF` contains 126 repeated words `$F526`, completing a visual
    1,024-slot layout after the 898 confirmed battle-text pointers;
  - `$B4:F526` begins uniform `$FF` fill rather than a valid zero-terminated
    stream, and no valid selector domain for IDs `$1382-$13FF` is established,
    so these words remain unclassified.
- Bank-`$AE` animated CGRAM arrays:
  - `$AE:8D88-$8F07`, `$AE:8F08-$9087`, and `$AE:9088-$9207` are three
    contiguous arrays of 12 records each, with an exact `$20`-byte record stride;
  - each selected record is copied word-for-word into CGRAM staging at `$04C0`
    or `$04E0`. Selector `$0F1B` is explicitly incremented and wrapped at 12;
  - the third array's first record is also used by a fixed setup path, providing
    an independent base and destination confirmation;
  - this classifies all 1,152 bytes between exact codec resources and raises
    physical bank `$2E` to 32,732 / 32,768 bytes classified.
- Deliberately unresolved bank-`$A2` prefix:
  - `$A2:8000-$857F` is visually compatible with planar graphics, but no direct
    or split-bank consumer was found;
  - the adjacent loader table explicitly selects compressed source `$A2:8580`
    with decoded length `$1A00`, not `$A2:8000`;
  - the 1,408-byte prefix therefore remains unknown rather than being merged
    with the following compressed resource based on appearance or adjacency.
- Bank-`$89` post-control-stream routine and presentation resources:
  - `$89:9310-$9988` is executable code entered by two exact `JSL $89:9310`
    call sites and ending in valid local return paths. The prior control-stream
    corpus ends independently at `$89:930F`;
  - `$89:9989-$999C` is a separately referenced ten-word zero-terminated display
    stream;
  - `$89:999D-$9A9C` and `$89:9A9D-$9B9C` are exact `$100`-byte presentation
    graphics blocks copied to `$0400`. Their `$C0`-byte suffixes are also copied
    independently from `$99DD/$9ADD` to `$0440`;
  - compressed source `$89:9B9D` establishes the following boundary. Physical
    bank `$09` is now 32,766 / 32,768 bytes classified.
- Bank-`$88` selector-owned graphics hierarchy:
  - the separate fixed-label consumer at `$83:CA1C` doubles WRAM `$6B`, reads a
    word from `$88:8000,X`, and copies the selected word stream through its first
    zero. The caller at `$90:A572` writes the exact value `$0003` to `$6B`
    immediately before `JSL $83:C7DC`, proving pointer slot `$88:8006-$8007`;
    that slot resolves to the independently classified zero-terminated stream at
    `$88:8070-$8077`. Other still-unclassified slots at `$88:8000-$8053` remain
    unresolved because the scenario command `$1E` selector domain is incomplete;
  - `$88:824C-$8277` contains 22 same-bank pointers indexed by selector `$02A0`
    values `$00-$15`;
  - aliases resolve to exactly 18 unique targets at every `$60`-byte boundary
    from `$88:8278` through `$88:88D8`, partitioning `$88:8278-$8937` without
    gaps. Consumers copy each selected record exactly to staging `$04A0/$06A0`;
  - `$88:8938-$894D` and `$88:894E-$8963` are companion 22-byte selector arrays
    passed to the two confirmed resource loaders;
  - compressed source `$88:8964` establishes the terminal boundary. The
    preceding 32 bytes at `$88:822C-$824B` remain unknown because no consumer
    currently owns them.
- Physical bank-`$0E` tail:
  - `$8E:FF8A-$FFFF` is a complete 118-byte uniform `$FF` bank tail immediately
    after the exact portrait codec extent ending at `$8E:FF89`;
  - no exact 24-bit pointer to `$8E:FF8A` exists. It is classified conservatively
    as `fill`, not as allocatable free space, raising physical bank `$0E` to
    32,740 / 32,768 bytes classified.
- Physical bank-`$0F` tail and unresolved bank-`$90` code module:
  - `$8F:FFFA-$FFFF` is a complete six-byte uniform `$FF` bank tail immediately
    after the exact portrait codec extent ending at `$8F:FFF9`;
  - no exact 24-bit pointer to `$8F:FFFA` exists. It is classified conservatively
    as `fill`, not as allocatable free space, raising physical bank `$0F` to
    32,278 / 32,768 bytes classified;
  - `$90:8000-$C328` contains real 65C816 code, including externally entered
    routines at `$90:8223` and `$90:B800`, and ends immediately before the
    existing `$90:C329-$FFFF` fill tail. The bank also contains internal tables
    and indirect-control-flow data whose complete ownership boundaries are not
    yet mechanically proven, so the 17,193-byte prefix remains unknown rather
    than being classified from a linear sweep.
- Bank-`$83` presentation code between companion portrait tables:
  - exact `JSL` call sites at `$83:BF87/$83:BFEA` enter `$83:E600`, while the
    scenario animation handler at `$83:BF25` enters `$83:E819`;
  - `$83:E600-$E818` is a coherent menu/choice presentation routine with
    terminal `RTL` paths at `$83:E7E0` and `$83:E818`;
  - `$83:E819-$E8FF` updates object coordinates through four local `JSR`
    helpers, renders through the independently classified `$83:E900` placement
    table, and terminates with `RTL` at `$83:E8FF`;
  - the exact 768-byte code extent has pinned SHA-256 digest
    `2beb935fbbd986875341201690555a25a378800ded348407f4bf1504386b076b`.
- Bank-`$83` post-placement presentation setup:
  - the sole exact `JSL $83:E918` call at CPU `$80:CE9F` enters a coherent
    76-byte setup routine at `$83:E918-$E963`;
  - it configures five object records, marks the tile work area dirty, waits one
    frame, restores processor status, and ends with `RTL` at `$83:E963`;
  - the following `$83:E964-$EA20` bytes decode as several code-shaped routines,
    but no exact far or same-bank call/reference currently reaches their starts.
    The final `$83:EA21-$EA40` bytes are a separate constant-looking structure
    with no identified consumer. Both ranges remain unknown rather than being
    classified from appearance;
  - the exact setup-routine extent has pinned SHA-256 digest
    `124cb8bead6e754c3d4b68e02094e93fbddeddd154a74cb0597f4b575c9134f7`.
- Bank-`$84` raw WRAM-to-VRAM graphics source:
  - CPU `$81:8071` copies exactly `$0200` bytes from `$84:8000-$81FF` into
    WRAM `$7E:8000-$81FF` using `LDX #$8000`, `LDY #$8000`, `LDA #$01FF`, and
    `MVN $7E,$84`; the accumulator-plus-one block-move rule proves the extent;
  - the same routine sets VRAM destination `$0000`, transfer length `$0200`, and
    request bit `$0001`. VBlank handler `$80:8523` performs mode-1 DMA from
    WRAM `$7E:8000` through `$2118/$2119`;
  - the independently loader-owned compressed resource at `$84:8200` proves the
    following boundary. The exact raw source has pinned SHA-256 digest
    `43c12e7be15d3a323b050d3af9db0d8abe362615bf887887ddfa62a099acd3a2`.
- Bank-`$81` name/password presentation module and companion bank-`$84` data:
  - six externally or locally entered code intervals at `$81:8000-$8684`,
    `$81:868B-$8AD6`, `$81:8ADB-$8B5D`, `$81:8B63-$8BDC`,
    `$81:8BE2-$8C37`, and `$81:D883-$D8BE` are now classified around the
    existing selector table and translation hook sites. Every terminal boundary
    is an exact return or an independently classified table/hook boundary;
  - the field-cursor continuation at `$81:8C3D-$8C6F` ends in `RTS`, followed by
    exact indexed tables at `$81:8C70-$8D23`, `$81:8D24-$8D55`,
    `$81:8D56-$8DFF`, and `$81:8E00-$8EA9`;
  - `$84:83E2-$8441` is copied exactly as `$60` bytes to WRAM `$0440-$049F` and
    reaches CGRAM through the `$DC` bit-`$0010` VBlank DMA path;
  - `$84:A3E0-$A5BF` is exactly two `$F0`-byte zero-terminated picker-page
    display slots selected by offsets `$0000/$00F0`. The independently
    classified editor-hint stream at `$84:A5C0` proves the terminal boundary;
  - `$81:D856-$D882` remains unknown despite containing nine structurally valid
    five-byte resource descriptors because no direct consumer has been found;
  - three exact JSL-entered bitmap-popcount routines at `$81:D315-$D3DA`, the
    locally JSR-entered setup/configuration routine `$81:D3DB-$D653`, the
    literal-rendered zero-terminated stream `$81:D654-$D689`, and the heavily
    reused resource-loader routine `$81:D68A-$D6C5` now form a complete exact
    partition of this module.
  - decoded JSL `$81:9427` owns an interactive setup/configuration workflow
    through `$81:9C88`, partitioned around a five-slot local jump table, four
    three-byte source records plus terminator, and a teardown helper. The same
    proven selector domain `$00-$04` owns the five coordinate words at
    `$81:9C89-$9C92`;
  - local JSR `$81:D2C1` proves the exact setup helper `$81:D2C1-$D314`, whose
    terminal RTS immediately precedes the independently entered `$81:D315`.
- Additional bank-`$84` consumer-owned presentation structures:
  - fixed and variable display-stream reads from `$84:86BE/$84:86CE` prove
    `$84:86BE-$87CF`, `$84:87D2-$88E3`, and `$84:88F8-$8C0B`. The exact unread
    gaps `$84:87D0-$87D1` and `$84:88E4-$88F7` remain unknown;
  - the final range includes eight padded `$30`-byte streams selected by a
    proven `$00-$07` domain, the independently entered `$84:8AFE` stream, and
    eight padded `$20`-byte streams selected by another proven `$00-$07` domain;
  - `$84:8C96-$8CB5` and `$84:9E88-$9EC7` are exact `$20`- and `$40`-byte
    palette blocks copied to WRAM `$0500/$0520` and transferred through the
    confirmed `$DC` bit-`$0010` CGRAM DMA path. The preceding byte `$84:8C95`
    remains unresolved;
  - the threshold consumers multiply WRAM `$0C5F` by eight and read only words
    `+0/+2/+4`. Direct initialization paths prove selector values `$0000`,
    `$000A`, and `$001C`, classifying six bytes at each of `$84:9EC8`,
    `$84:9F18`, and `$84:9FA8`. Their `+6` words and all other selector records
    remain unresolved because scenario opcode `$47` has an incomplete domain;
  - `$84:A6C0-$A70F` contains four exact `$14`-byte battle-menu label rows.
    Consumers reduce the selector to `$00-$03`, multiply by `$14`, and consume
    one complete row through five two-word copies;
  - `$84:A710-$A73B` contains 22 strictly increasing same-bank pointers indexed
    by the proven `$00-$15` menu domain. Their 22 unique zero-terminated streams
    losslessly partition `$84:A73C-$BECD`; the final terminator immediately
    precedes the independently classified `$84:BECE` initializer;
  - literal offsets `$0250/$0280/$02B0` from `$84:A3E0` select password-mode
    display streams at `$84:A630/$A660/$A690`. Three independent CPU `$81`
    loops copy complete 16-bit words through the first `$0000`, proving exact
    extents `$84:A630-$A655`, `$84:A660-$A683`, and `$84:A690-$A6B3`;
  - `$84:A62C-$A62F`, the zero-filled gaps between those streams,
    and `$84:A6B4-$A6BF` remain unknown because no consumer owns those bytes;
  - three 64-slot pointer tables at `$84:D2DA`, `$84:DB44`, and `$84:E3C8`
    are selected by candidate IDs `$00-$0F` multiplied by four and a proven
    random subselector `$00-$03`. Their 31, 31, and 30 unique targets exactly
    partition zero-terminated corpora through `$84:EAFF`;
  - `$84:EB00-$EB21` is a 17-slot pointer table indexed by the explicit closed
    candidate domain `$00-$10`. Its 17 unique zero-terminated targets partition
    `$84:EB22-$F141`, ending immediately before the translated allocation at
    `$84:F142`.
- Deliberately unresolved bank-`$88` and `$8F` candidates:
  - `$88:CFF1-$E537` and `$88:FBAF-$FFB3` do not decode with the confirmed LZ
    codec, have no validated root pointer, and contain mixed structured data;
    the explicit loader table proves only the next source boundaries at
    `$88:E538` and the previously reviewed tail at `$88:FFB4`;
  - `$8F:8000-$81DF` contains 480 palette-looking bytes before compressed source
    `$8F:81E0`, but the apparent `$8F:8000` far pointer is an incidental byte
    sequence inside the unresolved `$A2:8000-$857F` block. Appearance and
    adjacency are not sufficient to classify it.
- Companion portrait metadata:
  - 128 palette pointers at CPU `$8A:8000`;
  - 102 contiguous 32-byte SNES CGRAM records at `$8A:8100-$8DBF`;
  - 128 object-frame base IDs at CPU `$83:E500`;
  - six four-byte display-slot placement records at CPU `$83:E900`.
- Complete top-level SPC700 upload structure rooted at CPU `$83:8200`:
  - confirmed S-CPU/APU handshake and upload code at `$83:8000-$828B`;
  - four bootstrap package pointers, 20 terminated sample-selector streams,
    55 four-byte BRR descriptors, and 20 eight-byte configuration records;
  - 24 length/destination-delimited SPC upload packages totaling 66,114 bytes;
  - 35 referenced BRR records totaling 102,947 bytes, each with a valid
    nine-byte block count and its sole end flag on the final block.
- Reconstructed bootstrap APU-RAM map:
  - executable driver block at SPC `$0800-$1920` with entry `$0800`;
  - 64 four-byte sample-directory entries at `$1B00-$1BFF`;
  - 64 six-byte instrument records at `$1C00-$1D7F`;
  - sequence-pointer metadata at `$1E00-$1E5D` targeting `$1F00-$2F26`;
  - 17 directory-owned resident BRR records spanning `$4000-$9F21` exactly.
- SPC700 command structure:
  - all 32 sequence-command dispatch targets at `$1182-$11C1`, with total
    encoded lengths matched to parameter-reader calls;
  - all 24 table-dispatched S-CPU/APU commands at `$17EA-$1819`;
  - instrument bytes 4-5 established as a big-endian unsigned Q8.8 pitch
    multiplier consumed by the DSP pitch calculation.
- A raw-graphics descriptor matrix at ROM `$168000-$16A07F`:
  - 26 consecutive tables contain 64 five-byte records each;
  - 977 populated records contain a valid 24-bit LoROM source pointer and a
    nonzero `$20`-aligned byte count; the other 687 records are all zero;
  - 211 unique, non-overlapping source extents total 267,936 bytes / 16,746
    complete SNES 2bpp tiles in 23 gap-free groups;
  - the 80-slot pointer table at CPU `$AD:A080-$A11F` has 68 nonempty record
    pointers in slots `$00-$43`, followed by 12 copies of end sentinel `$B68A`;
    the pointed records partition `$AD:A120-$B689` exactly, totaling 5,482
    bytes, and CPU `$83:8520/$83:8585` explicitly select final records `$42`
    and `$43`;
  - configuration-record byte 4 supplies the table-0/1 record index, byte 9
    supplies the table-2-25 record index, and byte 0 supplies a selector whose
    observed range is exactly `$00-$17`;
  - configuration-record byte `+$00` is a battle-fighter/entity resource
    selector rather than an action selector: the same value indexes ordinary
    fighter-name slots at CPU `$84:BF16`, two 16-color palette blocks in bank
    `$A0`, sprite tile-number bases, per-fighter placement-adjustment tables, and
    physical raw-2bpp descriptor tables 2-25. Descriptor tables 2 and 8
    (selectors `$00/$06`) are all zero; tables 4 and 6 (selectors `$02/$04`) are
    byte-identical even though their entity metadata remains distinct elsewhere;
  - every configuration record begins with a fixed 32-byte header consumed at
    CPU `$82:8D65-$82:8E30`: selector bytes at `+$00/+$01`, a word at `+$02`,
    graphics indexes and coordinate words at `+$04-$0D`, and nine parameter
    words at `+$0E-$1F`;
  - byte `+$20` selects the trailing candidate-word layout consumed by CPU
    `$82:8AE6` and `$82:8BDC`: 33 mode-0 records use a count byte at `+$21`
    followed by that many words at `+$22`; 11 mode-1 records contain two
    16-word lists at `+$21` and `+$41`; and 24 mode-2 records contain the first
    16-word list plus six four-word subgroups beginning at `+$41`, selected
    from byte 0 of the current action record;
  - CPU `$84:C550-$C6CF` is the parallel 192-slot action-name pointer table.
    Its 121 distinct active targets partition word-aligned, zero-terminated
    streams at `$84:C6D0-$CDD7` exactly. Slots `$46-$7F` select the blank stream
    at `$84:CAD6`; opponent names begin at slot `$80` / `$84:CAD8`; and slots
    `$B2-$BF` select the blank end stream at `$84:CDD8`;
  - CPU `$84:CE12-$CF91` is the complete 192-slot action-record pointer table.
    Its two active index ranges resolve to 120 unique contiguous seven-byte
    records at `$84:CF92-$D2D9`; player boundary slot `$46`, blank-name slots
    `$47-$7F`, and opponent slot `$80` share the real record at `$84:D17C`, while
    slots `$B2-$BF` repeat end sentinel `$D2DA`;
  - battle initialization copies two consecutive `$24`-byte side records from
    CPU `$84:BECE-$BF15` to WRAM `$0C86-$0CCD`. CPU `$80:9555` returns side
    offset `$0000` for `$025A=0-1` and `$0024` for `$025A>=2`; each record's
    `+$10-$14` bytes initialize its five player-selectable action slots. The
    default rows are five copies of index `$02` and five copies of index `$25`;
  - CPU `$82:D4CF-$D57C` maps directional/button input to one of those five
    slots, while two-button cases directly select `$40-$44`. Menu code may
    reorder or replace individual row entries. Standard configuration-record
    candidate words, by contrast, are all bounded to `$80-$B1`, exactly the
    pointer table's second active range. Encounter/configuration `$00` uses
    mode 0 candidates `$84/$8F/$91`; encounter/configuration `$03` uses mode 2
    and candidates bounded to `$80-$A3`;
  - player actions `$00-$3F` also form a flat 64-bit unlock space in WRAM
    `$0D2E-$0D34`. The action menu computes `category * 8 + row`, tests that
    exact bit, and writes the same flat action ID directly into one of the five
    equipped slots. CPU `$82:E7DB-$82:EDFB` dispatches progression by selected
    action class and sets immediate unlock indexes whose complete domain is
    `$00-$3F`; no family or variant-grade lookup participates in unlocking or
    equipment;
  - action-record byte `+$00` has the complete domain `0-5`, exactly matching
    the six physical mode-2 subgroups. Renderer-reconstructed names support the
    broad class categories physical strike/attack, throw/counter, rush/evasive
    attack, ki/energy technique, high-cost special technique, and state/control
    action for values `$00-$05`, respectively. Other confirmed fields are lookup byte
    `+$01`, player variant-grade byte `+$02`, 16-bit combat coefficient
    `+$03/+$04`, action-menu
    value/resource-cost scaling byte `+$05`, and probability byte `+$06`. All 24
    direct CPU `$84:CE12` consumers in banks `$81/$82` read only `+$00`, `+$01`,
    `+$03/+$04`, `+$05`, or `+$06`; none reads `+$02`. No absolute-indexed,
    unindexed-long, or immediate reference form for `$84:CE12` exists. Within
    every repeated player family keyed by `+$00/$01`, `+$02` is a grade in
    `$00-$02`, follows visibly escalating named variants in the reconstructed
    action-name sheet, and is ordered with the `+$03/$04` coefficient; the same
    grade sequences recur across duplicated player families even where
    coefficients differ. The shared boundary and every opponent record use
    `$FF`, establishing it as a non-player marker. Because unlock, equipment,
    selection, and battle consumers all operate on the flat action ID without
    reading `+$02`, it has no independent effect in any confirmed runtime path;
    redundant authoring or vestigial metadata remains the conservative inference;
  - all 70 player action names at flat IDs `$00-$45` have now been visually
    reconstructed and recorded as English-only identity metadata in
    `analysis/action-records.md`. IDs `$00-$1F` and `$20-$3F` are parallel
    32-action banks with the same broad class progression but distinct advanced
    identities and coefficients. IDs `$40-$45` are six exceptional state or
    clash-capable special actions outside the proven 64-bit progression-unlock
    space. The table structure does not establish fighter or route ownership for
    either 32-action bank;
  - renderer reconstruction independently confirms action index `$38` and
    opponent index `$91` display the same Dash Punch stream bytes, while their
    name pointers (`$84:CA10` / `$84:CBE2`) and seven-byte records
    (`$84:D11A` / `$84:D1F3`) are distinct. Visible-name equality therefore does
    not establish action-record identity. Higher-level identities remain partial;
  - CPU `$84:CDDA-$CE11` is a 56-byte, seven-row by eight-column class-matchup
    matrix. Its exact table consumer computes `player class * 8 + opponent class`
    from action-record byte `+$00` and stores the result in WRAM `$0E48`.
    Active records use classes `$00-$05` on both sides, so exactly the upper-left
    6x6 entries are reachable; row 6 and columns 6-7 remain structurally present
    but unreachable. Result `$00` means player/first-side success and subtracts
    calculated action damage from opponent HP `$0E68`; `$01` means
    opponent/second-side success and damages player HP `$0E66`; `$02` is neutral
    and applies no action damage. The sole `$03` entry is special technique versus
    special technique; CPU `$82:9D0E` compares derived side-strength values and
    resolves it to `$00/$01` when their difference is at least five, otherwise
    `$02`. `$FF` is the sentinel result. Outcome palettes, animation-script
    selection, damage branching, and opponent-success bookkeeping all consume
    the resolved value consistently;
  - mode-0 records `$12`, `$17`, and `$1E` append 81-, 81-, and 65-byte blocks
    after their count-bounded lists. The blocks are structurally identical to
    complete mode-2, mode-2, and mode-1 selector layouts, respectively. All four
    exact CPU `$AD:A080` consumers are pointer-table-rooted: fixed-header reads
    stop at `+$1F`, mode-0 candidate selection is count-bounded through `+$27`,
    mode-1/2 selectors use their standard layouts, and the battle-script
    condition reads only `+$0E`. The appendages begin at `+$28`, and no exact
    banked pointer targets them, so they remain unreachable appendages rather
    than asserted second subrecords;
  - CPU `$82:93FE` selects physical table 0 or 1 from battle side `$025A`, while
    CPU `$82:9465` computes `(fighter/entity selector * 64 + record) * 5` from
    base `$AD:8280`, thereby selecting physical tables 2-25;
  - both consumers load the source into `$EA:$E8`, the byte count into `$ED`,
    set VRAM destination `$4000` or `$4B00` in `$EB`, and request transfer bit
    `$0040`; the VBlank path at CPU `$80:859F` performs channel-7 mode-1 DMA
    directly from ROM to `$2118/$2119` in chunks of at most `$0800` bytes;
  - representative direct 2bpp decoding from every group confirms structured
    tile/glyph fragments, while higher-level semantic ownership of the groups
    remains unresolved.
- Complete bank-`$B4` battle-text structure:
  - 898 resource pointer slots (`$1000-$1381`);
  - 729 unique contiguous zero-terminated word streams;
  - text corpus ROM `$1A0800-$1A7525`.
- Complete bank-`$B5` opening/win/loss table and script-block partition from
  CPU `$B5:BA7E` through `$B5:D22C`.
- Large physical-bank fill tails, recorded conservatively as `fill` rather than
  approved padding. This now includes `$88:FFF2-$FFFF`, `$8B:FFE0-$FFFF`, and
  `$8D:FF94-$FFFF`; the apparent `$88:FFF2` far-pointer bytes occur only inside
  a confirmed BRR sample, while `$8D:FF93` remains an isolated unknown byte.
  Translation-adjacent uniform tails `$81:DD14-$FFFF` and `$84:F476-$FFFF`
  begin exactly after reviewed allocations and have no exact pointer or decoded
  target; they are likewise `fill`, not approved free space.
- Unreferenced bank-`$B6` renderer-source blocks beyond the confirmed glyph
  corpus.

## Classification completion and remaining semantic work

There are no unclassified physical ROM bytes. Completion was achieved without
extending exact compressed-resource extents: one-byte and short inter-resource
separators are classified independently as `padding`, and fixed table/stream
gaps are represented with their own `data`, `pointer_table`, `text`, or
`graphics` regions.

Several classifications intentionally stop short of claiming a fully decoded
schema. In particular, `confirmed_structure_partial_schema` records preserve
lossless ownership and broad role while leaving field semantics, subrecord
formats, or runtime selection details open. The bank `$A2:8000-$857F` planar
tile corpus remains a `strong_inference` graphics classification because its
static tile structure is coherent but a runtime consumer has not been traced.

The CPU `$8A:FF42` / ROM `$057F42` `$FF` tail is now classified as confirmed
fill. Its sole apparent 24-bit reference occurs at ROM `$038821`, inside the
table-selected compressed resource at CPU `$87:8000`; it is compressed payload,
not a pointer operand.

The CPU `$8C:FF08` / ROM `$067F08` tail is also confirmed fill. Both apparent
references are compressed payload: ROM `$18B390` is inside a CPU `$81:D883`
table-selected stream, while ROM `$06C1F9` is inside the portrait descriptor
`$F24F` stream at CPU `$8D:BFEA`.

The next high-value semantic tasks are:

1. Decode the complete battle-script opcode schema and split script records.
2. Decode the internal schemas of packed resource corpora that are now bounded
   but not yet attributable to a specific renderer or decompressor table.
3. Correlate the now-bounded player/opponent action-index ranges, configuration
   modes, named player-action banks, and direct ROM-to-VRAM DMA path with runtime
   states to establish bank ownership, exceptional-ID selection, opponent-action
   identities, semantic ownership of the 23 source groups, and the three
   unreferenced appendages.
4. Trace the runtime consumer of the bank `$A2:8000-$857F` planar tile corpus.
5. Refine broad code/data containers into more semantically named routines,
   tables, and fields without changing their complete byte ownership.