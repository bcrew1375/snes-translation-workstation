# Translation source

This directory contains repository-authored English translation data and
non-expressive metadata that identifies source streams in the user-supplied ROM.

Tracked files must not contain decoded Japanese dialogue, substantial transliterations,
raw source streams, or long byte arrays capable of reconstructing original text.

## Tracked manifests

All tracked translation manifests are schema-versioned TOML. Record order is
authoritative and preserved by the loaders. ROM offsets, lengths, selectors,
banks, alignments, and indexes use native TOML integers; hexadecimal notation is
preferred where it reflects an address. CPU addresses remain explicit
`BANK:ADDRESS` strings. Arrays are used for structured values such as patch
English lines, menu character offsets, and glossary aliases; escaped `\\n`
sequences are not used to define patch line breaks.

- `patches/<arc>/*.toml` records stable IDs, selectors, pointer locations,
  source locations/lengths/hashes, English text, workflow status, and
  non-expressive notes. Each story record is self-contained; no parallel
  reference manifest has to remain synchronized with it. The `english` value is
  an array in which each string is one explicit displayed line. Arc directories
  and files use sparse three-digit story order prefixes; numbering restarts within
  each arc and leaves room for later discoveries without mass renaming.
  Files are loaded recursively in lexical relative-path order, and records retain
  their declared order within each file. The current layout is:
  - `patches/00_opening/` for the opening narration and recap.
  - `patches/01_23rd_world_tournament/` for the tournament story through the
    Junior battle branches.
  Future story content should receive the next ordered arc directory rather than
  extending one game-wide filename sequence. Stable record IDs are independent of
  this organizational path and must not be renumbered during moves.
- `ranges/**/*.toml` records reviewed allocation ranges by technical responsibility:
  core fields, HUD resources, menu/name/font resources, allocator pools, and story
  source ranges. The loader still validates and processes them as one ordered collection.
- `menu.toml` records the fixed title, New Game, sound-mode, and indexed BGM menu
  records, including record type and reviewed character-level alignment offsets.
- `name_entry.toml` records both 85-entry name-picker pages, their selection maps,
  the five localized default names, and the fixed English name-editor prompts.
- `choices.toml` records pointer-selected fixed labels and opening choices, source
  hashes, pointer locations, preserved native icon prefixes where applicable, and
  deterministic same-bank relocation destinations.
- `battle_text.toml` records the battle-script resources selected through bank-$B4's
  `$1000`-based pointer table. It preserves each source stream's native line count and
  cell allocation, records the runtime/control-flow-established path and speaker, and
  keeps all implemented Goku/Chi-Chi and Junior battle resources in place. The Junior
  battle (encounter `$0003`) includes opening, win, and loss resources plus scenario
  continuation patches for both result paths.
- `glossary.toml` records the project's canonical English terminology for names,
  terms, techniques, places, races, organizations, and story arcs. Each record
  contains a stable `id`, a `category`, the `canonical` English form, the
  `aliases` array for lookup, `usage_notes` on capitalization and context, and a `status`
  field. The glossary contains no decoded Japanese text, no raw ROM data, and no
  reconstructed dialogue. It uses the modern North American anime and game
  localization as the primary standard: Frieza, Krillin, Jeice, King Kai, Grand
  Elder Guru, World Tournament, Special Beam Cannon, Destructo Disc, Tri-Beam,
  Spirit Bomb, Kaio-ken, and related forms. Tournament-specific exceptions use
  `Shen` for Kami's contestant alias, `Kami` for his identity, and `Crane Hermit`
  for Tsuru-sen'nin; `Master Shen` is prohibited because it conflates two separate
  characters. The aliases array may contain manga-
  oriented or source-name alternatives (for example Freeza, Kuririn, Tenshinhan,
  Kaio, Kienzan, Makankosappo, Tenkaichi Budokai) for identification purposes,
  but the canonical field is the required output form.

The translation builder recursively concatenates the ordered
`patches/<arc>/*.toml` collection.
Only confirmed ranges whose names begin with `free_text_`, compact suffixes from fully
claimed in-place streams, and complete source allocations proven to be vacated by
mandatory relocation are eligible for relocated text allocation. Compact English
streams end immediately after their `$0000` terminator; unused Japanese-width line
cells are not emitted. After every record and alias is validated, the builder may reuse
the bytes between such a compact terminator and that record's hash-pinned source end.
If a fully claimed stream is too large to remain in place, its complete hash-pinned
source allocation becomes a lower-priority fallback only after every selector that
references it is scheduled to move. Sources with any unclaimed alias remain reserved.
The reviewed `free_text_bank_99_tail` remains the primary fallback production pool.
Relocation-required streams are allocated largest-first, with manifest order as the
stable tie-breaker, to avoid fragmenting reviewed space; returned build plans retain
manifest order.
Other structural gaps and streams lacking fully established ownership remain reserved.

The implemented automatic opening covers the four narration panels at command-`$08`
selectors `$07E1-$07E4` and all 22 text records shown in the following recap before
the title screen returns. Runtime tracing of scenario root `$0170` established the
post-fade selector order; the tracked reference manifest records every selector and
target without reproducing source dialogue.

The opening 23rd World Tournament scene is implemented for command-`$08`
selectors `$0200-$021A`. Seventeen records fit their original bank-$99
allocations; ten longer records relocate deterministically into safe compact-stream
suffixes or the reviewed all-`$FF` tail beginning at CPU `$99:F8EE` / ROM
`$0CF8EE`, with only their same-bank selector pointers updated.

Two opening location bars use a separate fixed bank-`$88` pointer table rather
than command-`$08` dialogue selectors. Table entry 12 is translated as
`World Tournament Arena`, and entry 35 as `Papaya Island`; both source streams
and pointers are hash-pinned and relocate into reviewed bank-`$88` tail space.

Packed-Latin dialogue is authored to the confirmed visible box widths rather
than the larger legacy-cell storage capacity: portrait-free `wide_marker`
records permit 28 characters per line, while portrait-bearing `context_pair`
records permit 21. Confirmed records declare that value as `max_line_length`;
the build checks it against the ROM presentation metadata and rejects longer
explicit lines before allocation so the game cannot split a word at the right
edge of a box. Explicit newlines, including blank lines used to reach the next
four-line box, are encoded as `$000A`; unused cells at the end of a line are not
padded. Four short opening-recap records use the unclassified `default`
presentation and intentionally omit `max_line_length` until their visible width
is confirmed; their encoded cell capacity and box height remain validated.

The following choice panel is also a fixed resource rather than a command-`$08`
text stream. Its heading is selected through table entry `$0173` at `$98:9E10`
and translated in place at `$98:C1A8` as `DBZ Trivia Quiz`. Its option pointers
at `$98:9B2A-$98:9B2E` retain X/Y/B order, and each option preserves the original
colored button-icon and spacer words. The localized rows are `You're bleeding!`,
`Are you sick?`, and `You look sexy.`
Command `$07` at CPU `$91:8179` / ROM `$088179` and its following scenario
branch bytes are unchanged. The bank-`$88` entry at `$88:8018` is the separate
`World Tournament Arena` location bar, not a quiz heading.

Runtime branch validation from the pre-choice continuation state confirms that
X and Y both reach scenario cursor `$91:8193` and Bulma response selector `$021B`
(`It's lipstick!`), while B reaches `$91:819A` and selector `$021C`
(`O-oh... Y-you think` / `so...?`). A does not dismiss or select the panel. Both
English streams exceed their compact original allocations by two bytes, so the
builder relocates them deterministically within the reviewed bank-`$99` pool:
`$021C` moves from `$99:906E` to the compact suffix at `$99:998A`, and `$021B`
moves from `$99:9060` to the compact suffix at `$99:9526`. Only pointer words
`$99:8438` and `$99:8436` are updated.

After either response, all three result values reconverge on the same Master
Roshi dialogue. Checkpoint 2 includes every intervening command-`$08` stream:
selectors `$021D-$0221` cover Roshi's surprise, the returning competitors'
greetings from Chiaotzu and Tien, Yamcha's observation, and Krillin's explanation
that their changed appearances left Roshi
stunned. Four streams fit in place; `$021F` relocates deterministically into a safe
compact suffix at `$99:AB6A-$99:AB8D`. Their consecutive pointer slots are
`$99:843A-$99:8443`, and their original source span is `$99:908A-$99:917D`.

The common route then reaches the second fully rendered quiz panel at frame 8420.
Scenario resource indices `$0003/$0004/$0005` select consecutive
fixed-resource pointers `$98:9B30-$98:9B34`. Their localized X/Y/B rows are
`You haven't changed!`, `I grew more than you!`, and `You look well, Krillin!`.
All three preserve their native button-icon prefixes and relocate consecutively
to `$98:F502-$98:F555`. X, Y, and B retain result values 0/1/2 but all branch to
scenario cursor `$91:8218` and shared Goku response selector `$0222`. Its English
line, `Now everyone's here!`, fits in place at `$99:917E` without a pointer change.
A fresh deterministic replay against translated ROM SHA-256 `4a26ab2e...` rendered
all five lead-in selectors, including `$0221` across two cleanly paginated boxes,
then reached the translated second panel. Independent X/Y/B reloads from that panel
all rendered the identical shared Goku response `Now everyone's here!`. The earlier
`dd21ac10...` frame-8420 run remains recorded as superseded-ROM evidence. Tracing the
exact selector set after `$0222` established checkpoint 3.

Checkpoint 3 translates the post-quiz reunion and the move to the preliminaries.
The reached command-`$08` sequence begins `$0223`, shared selector `$001B`, and
`$0225-$023D`; `$0224` is an
unexecuted pointer alias of `$0225`, so the shared source at `$99:91BA` has one
translation record and one pointer update. The remaining source streams span
`$99:919C-$99:95B3`. Records that exceed their original allocations relocate
deterministically within the reviewed bank-`$99` text pool; shorter records remain
in place.
The translated dialogue covers the group recognizing Goku, Bulma and Oolong's
reactions, the discussion of Goku's missing tail and Kami restoring the moon,
the group's reaction to Piccolo's arrival, Goku sensing his strength, and Chi-Chi
recognizing Goku immediately before the choice. Reused selector `$0003` remains
shared and does not receive a duplicate record. Runtime and static scenario evidence
place `$0237` and `$0238` consecutively before reconvergence at `$0239` on the reviewed
route.

The location header is fixed bank-`$88` entry `$01`: pointer `$88:8002` is
redirected from `$88:8058` to reviewed tail allocation `$88:FFDC`, which renders
`Preliminaries Venue`. The two-option panel uses generic heading table entry
`$0174` at `$98:9E12`, translated in place at `$98:C1BE` as `(Choice)`. Resource
indices `$0008/$0009` use pointers `$98:9B3A/$98:9B3C`; their in-place localized
rows are `You're Chi-Chi!?` and `Who are you?`, with the native X/Y icon and
spacer words preserved.

Final-ROM runtime replay confirms X/Y result values 0/1 and distinct branch
destinations. The Y route executes selectors `$023E-$0243`. The longer X route
executes `$0244-$0253`, with three portrait-only silent reactions between `$0251`
and `$0252`. Both routes converge at scenario cursor `$91:853D` on selector `$0260`.

The converged route translates selectors `$0260-$0263`: the announcer gathers the
contestants, Goku reads number 2 and the first Block 1 match, Krillin notes that the
group was separated into different blocks, and the announcer calls contestants 1 and
2. The next `DBZ Trivia Quiz` panel is reached at cursor `$91:8586`. Resource indices
`$000A/$000B/$000C` use fixed pointers `$98:9B3E/$98:9B40/$98:9B42`; their localized
X/Y/B rows are `Huh?`, `You again...`, and `King Chappa...`. X and Y fit in place.
The B row preserves its icon/spacer prefix and relocates from `$98:9F28` to the
reviewed tail at `$98:F556`.

All three quiz buttons reconverge immediately at `$91:85A0` and shared selector
`$0264`. Common selectors `$0264-$0266` carry the start-of-match narration,
announcer's signal, and Yamcha's reaction through cursor `$91:85B3`. Independent
X/Y/B replay produced byte-identical final screenshots for selector `$0266`.

Checkpoint 5 continues from `$91:85B3` through the first preliminary match and
Mercenary Tao confrontation. Runtime tracing confirms portrait selectors
`$0267-$0276`; shared low selectors `$0000/$0002` also execute inside the action
sequence but remain existing shared records rather than duplicate translations.
The new dialogue covers Goku's effortless win, Junior judging his hidden power,
Mercenary Tao injuring Chiaotzu, and his reunion with Tien and Goku. The reviewed
source span is `$99:9D76-$99:A0A7`; records that exceed their compact allocations
relocate deterministically into the existing bank-`$99` translation pool.

Command `$07` at CPU `$91:8718` opens the next `DBZ Trivia Quiz`. Resource indices
`$000D/$000E/$000F` use pointers `$98:9B44/$98:9B46/$98:9B48`. Their localized
X/Y/B rows are `He's an assassin.`, `I don't know him either.`, and
`I've seen him somewhere.` X fits in place at `$98:9F38`; Y/B preserve their
native icon/spacer prefixes and relocate to `$98:F56A/$98:F588`.

Final-ROM replay confirms that X/Y/B write result values 0/1/2 to WRAM `$021C`.
X takes the short extra command route `$91:8722->$91:8729->$91:872B->$91:872E`,
while Y and B go from `$91:8722` to `$91:8731`. All three reconverge at
`$91:8733` and execute common response selectors `$0277-$027B`: Mercenary Tao
reveals his cyborg body, threatens Goku and Tien, Tien rejects the Crane School's
teachings, and the two agree to fight. The shared final line renders as
`Ha ha ha...` / `I can't wait.` Independent revised X/Y/B runs enter the next
scene at selector `$027C`, cursor `$91:87A5`, with byte-identical captures.
The revised dialogue preserves the source's four-line box count with explicit
page-padding lines where required. Its translated ROM is SHA-256 `abf9222a...`;
final-ROM replay confirmed all page transitions and quiz rows without clipping.

Checkpoint 7 continues at selector `$027C`, cursor `$91:87A5`, and translates
selectors `$027C-$0280`. The scene covers contestant 51's win, another
contestant recognizing an unusually strong fighter, Krillin reacting to the
quality of this tournament's field, Goku identifying Piccolo's reincarnation
and judging his training, and contestant 2 qualifying for the World Tournament
finals. Source pagination remains exactly 1, 1, 2, 3, and 1 dialogue boxes.
Selectors `$027D/$027E` relocate deterministically to `$99:FB32/$99:FB60`;
the other three streams remain in place.

After `$0280`, command `$07` at CPU `$91:87EE` opens the next `DBZ Trivia Quiz`.
Resource indices `$0010/$0011/$0012` use pointers `$98:9B4A/$98:9B4C/$98:9B4E`.
Their localized X/Y/B rows are `Heh heh heh!`, `Peace!`, and `I did it!`.
Y fits in place at `$98:9F96`; X/B preserve their native icon/spacer prefixes
and relocate to the reviewed bank-`$98` tail at `$98:F5A6/$98:F5B8`.

Final-ROM SHA-256 `220b5030e5d32bc6ff5db77d6ee7431eeb2fbb1423336ba652f40fb9dc15fe4f`
was replayed from the retained pre-`$027C` state. The observed order is
`$027C->$027D->$027E->$027F->$0280->$91:87EE`; seven dialogue-page captures
and the quiz panel render without clipping. The final choice state, trace, and
screenshots are retained locally under
`local/runtime/second-prelim-final-220b5030-20261014/`.

Checkpoint 8 continues from command `$07` at `$91:87EE` through the finals draw and
stops at the next quiz. Independent original-ROM route tracing established the shared
executed dialogue set `$0281-$0292`, `$0F25`, and `$0294-$0299`. Separate recognition
evidence and source glyph review identify contiguous selector `$0293` as the alternate
recognized-route second-match card naming Chi-Chi. All three choice branches reconverge before selector `$0281`, so one
shared translation covers X/Y/B while preserving the distinct B route before
`$91:8809`.

The translated scene announces the remaining qualifiers, reactions from Goku and
Krillin, Yajirobe's disguised loss to Hero/Shen (Kami in disguise), the eight finalists,
and the four finals pairings. The unrecognized route selects bank-`$98` selector `$0F25`
and displays `Goku vs Anonymous`; the recognized route uses `$0293` and displays
`Goku vs Chi-Chi`. The final exchange
explains that Mercenary Tao survived in a partly mechanical body, intends to kill Goku
and Tien, and knows Tien's techniques inside and out. The prior `Saiya` interpretation
was an error: `$028D` calls it "a lousy match" and does not contain a character name.
Every dialogue record fits its original pinned allocation, so no additional bank-`$99`
free space is consumed.

After the bracket sequence, the existing bank-`$88` location entry `$0C` renders
`World Tournament Arena`. Command `$07` at CPU `$91:8AE9` opens the next quiz with
resource indices `$0013/$0014/$0015`. The localized X/Y/B rows are
`This could be bad.`, `No big deal.`, and `We'll manage.` The X row preserves its
native icon/spacer prefix and relocates to `$98:F5C8`; Y and B fit in place at
`$98:9FC4/$98:9FDC`.

Historical final-ROM X/Y/B replay on SHA-256
`861d5808911c132cf512c552d0ead3759f6502c4079aeacbee1f94f6c71819b1` preserves result
values 0/1/2 and executes the identical ordered
selector sequence through `$0299`, including repeated `$0287`, disjoint `$0F25`, and no
`$0293`. Every route reaches command `$07` at `$91:8AE9` and stops at cursor
`$91:8AEA`. The three byte-identical terminal screenshots visibly confirm
`World Tournament Arena` and the unclipped rows `This could be bad.`, `No big deal.`,
and `We'll manage.` Fresh branch-specific next-quiz states and traces are retained
locally under `local/runtime/finals-transition-final-861d5808-20261014/`.

The next checkpoint translates the quiz results and the entire Tien-versus-Tao
continuation. X writes result `0`, enters root `$000A` at CPU `$91:8B08`, and
renders selector `$029A`; Y and B write `1/2`, enter root `$000B` at
`$91:8B0F`, and render `$029B`. All three converge at root `$000C`, CPU
`$91:8B16`, and execute common selectors `$029C-$02C3`. The recognition test at
CPU `$91:8EB0` then controls the final two introduction lines: bit clear executes
`$02C4-$02C5`, while bit set skips them and terminates the root at `$91:8EDD`.

Recognition is not inferred from the later trivia answer. The earlier Chi-Chi X
branch sets WRAM `$0D98` bit 0 through command `$3D $0000` at CPU `$91:8366`;
an authentic retained X state contains `$0D98=$0001`, while the unrecognized Y
state contains `$0000`. Command `$3E` at CPU `$83:D516` tests this transient flag.
The finals checks at CPU `$91:8EB0` and root `$000D` entry `$91:8EDE` both use
operand `$0000` and therefore test the same recognition bit.

The recognized finals route uses selectors `$02C6-$02CA`: the announcer cancels
the second match because Goku and Chi-Chi's marriage has been settled, followed
by Goku, Chi-Chi, Master Roshi, and Bulma reactions. The unrecognized route in
root `$000E`, CPU `$91:8F5F`, uses `$02CB-$02D5` and disjoint selectors
`$0F1F-$0F22`, including the translated X/Y/B rows `When this is over.`,
`Sorry, forget it.`, and `Let's get married!` from fixed resources
`$0016-$0018`. The unrecognized sequence also interleaves shared selector
`$001D` (`Chi-Chi!!`) after `$02CB` and shared selector `$001F` (`Yeah!`) after
`$02D4`; these have independent pointer entries even where source content is
duplicated elsewhere. The checkpoint now contains 66 command-`$08` records.
Selector `$001D` relocates deterministically into a reviewed compact suffix;
the other newly restored shared selector remains in place.

The first actual battle-HUD audit extends beyond that checkpoint. The
unrecognized branch reaches Goku versus Chi-Chi first. The recognized branch
skips that fight, continues into root `$0013`, and executes additional dialogue
from `$02D6` through `$0309` before command `$47` at CPU `$91:9931` starts its
first later battle setup. Those intervening selectors are not part of the
implemented checkpoint above, so the repository does not claim complete
fresh-game translation coverage through the first HUD.

The battle HUD is also outside the command-`$08` text path. Its fighter name,
HP field, action, and status labels are generated as four 2bpp tile strips in
WRAM and uploaded independently. `src/dbz_kakusei_hen/battle_hud.py` implements
the confirmed base decompressor, deterministic recompressor, and post-decode
interleave with pinned resource tests. The remaining localization task is to
identify and replace the strip generator's source tables/compositor inputs; the
large `$B0:8000` battle setup resource must not be treated as the label source.

Root `$0018` is translated through the post-Goku-defeat Junior/Kami
confrontation. Its actual opening order is `$030A-$030D`, shared `$002A`
(`What!?`), then `$030E` onward. Selector `$0310` asks `Y-you!! Who are you!?`;
Junior's recognition of Kami belongs at `$0314`. The three technique lines use
allocation-safe localized terminology: `Evil Containment!!`,
`Evil Containment!!`, and `Containment Reversal!`. After selector `$0328`, root
`$0018` finishes its transition and routes to root `$0171` at CPU `$93:C163`.
That root displays selector `$0806`; command `$07` at CPU `$93:C187` / ROM
`$09C187` then opens the visible post-sealing Shenron prompt. The three
runtime-confirmed rows are rendered from CPU `$98:C16A`, `$98:C17E`, and
`$98:C194`: X `Save the game.`, Y `Boost power.`, and B `Boost health.` They fit
their original bank-$98 allocations in place. CPU `$91:A755` is the second
operand byte of the preceding command `$0E`, not a command boundary.

Separate final-ROM captures now confirm the full branch structure. X enters
selector `$0807` at CPU `$93:C197`; Y enters `$080A` at `$93:C1D7`; B enters
the same `$080A` stream at `$93:C1FE`. Completed X/Y/B wishes all continue
through `$0808` and then enter root `$001E`, whose Junior-battle lead-in begins
at selector `$0329`. Cancelling the X/save workflow with B instead selects
`$0809` at `$93:C1CC`; command `$1F $C187` at `$93:C1D4` loops back to the
wish menu. Selectors `$0806-$080A` are translated in place as `This is a save
point.` / `I'll grant you` / `one wish.`, `Choose your data...`, `Your wish` /
`is granted...` / `Farewell.`, `Hurry.` / `Make your wish...`, and
`Easily done.` All five use Shenron portrait resource `$67`, variant `$00`.

Root `$001E` continues with the translated selectors `$0329-$0331` immediately
after every successful Shenron X/Y/B branch converges. The tournament announcer
objects to Junior starting the fight and is silenced; Goku orders Piccolo to spit
out the bottle containing Kami, while Junior challenges him to take it by force
and warns that killing him would also kill Kami. Portrait resources pin the
speaker order as announcer (`$21`), Junior (`$03`), and Goku (`$00`). All nine
streams fit their original allocations at ROM `$0CCDBC-$0CCF1D`; selector `$032D`
retains its two native blank page-padding lines. After `$0331`, root `$001E`
executes only arena/battle setup commands before terminating. The resulting
deterministic translated ROM has SHA-256
`13577602d3bba92f796bf4f2d974373d19d6c109faf18aaa8597a6995239f974`.

The corrected checkpoint 6-8 wording was replayed again on the definitive translated
ROM SHA-256 `f64cca802e0d11230095fa611ae07fbc833ff0a78ccbb99f31fcf47bc4a51375`.
Bounded checkpoint-6 chunks execute `$0267-$027B`; checkpoint 7 executes
`$027C-$0280`; and final X/Y/B runs preserve values 0/1/2 while executing the same
checkpoint-8 selector sequence and reaching `$91:8AEA`. Runtime portraits confirm the
corrected speaker notes, including Tien at `$0267`, Yamcha at `$026B/$026F/$027D/$0298`,
Krillin at `$026E/$0297`, Yajirobe in disguise at `$0289/$028E/$028F`, and Master Roshi
at `$0296/$0299`. Final evidence paths and hashes are recorded separately in
`analysis/runtime-evidence.toml`; historical artifacts were not replaced.

Those retained finals captures also exposed an untranslated top banner on the matchup
announcement screens. Comparison with the reviewed fixed-resource strips identifies it
as bank-$88 table entry `$27`, whose pointer is at `$88:804E` (ROM `$04004E`) and whose
pinned source occupies `$88:8210-$88:822B` (ROM `$040210-$04022B`). It is translated in
place as `Matchup Announcement`. A final-ROM replay on SHA-256 `e4e53732...` followed the
retained X route through selectors `$028E-$0290`, continued across the bracket-transition
fade, and captured the stable Match 3 screen with the translated banner fully visible and
unclipped. Reproducibility paths and hashes are recorded in `analysis/runtime-evidence.toml`.

The nearby scenario command `$28 $000A` at CPU `$91:89A9` is unrelated to the banner.
Static handler analysis at `$83:CCDB` confirms that command `$28` treats its operand as
a bit index in the WRAM flag array beginning at `$0CCE`; `$000A` sets bit 10.

The actual fixed label meaning "behind the martial-arts stage" is bank-$88 table entry
`$02`, not entry `$0A`. Its pointer at `$88:8004` targets the 12-byte source allocation
at `$88:8064-$88:806F` (ROM `$040064-$04006F`). `Backstage` occupies that allocation
exactly, including its terminator, so the label is translated in place without changing
the pointer.

Final-ROM SHA-256 `cd6516bc...` was replayed from the second trivia response through
the choice. The observed order is `$0223`, `$001B`, `$0225-$0237`, `$0238`, and
`$0239-$023D`; `$0224` remains unexecuted. This corrects the earlier tentative
interpretation of `$0237/$0238`: both execute consecutively on the reviewed route.
Representative screenshots and per-step WRAM/cursor traces are retained locally under
`local/runtime/pre-chichi-final-cd6516bc-20261013/`, ending at choice cursor `$91:8355`.

A reusable state for the first post-naming gameplay screen is retained at
`local/runtime/gameplay-start-cd6516bc-20261013/gameplay-start.mss`. It was migrated
from the earlier verified gameplay checkpoint onto the final ROM, saved afresh, and
independently reloaded for one frame; the create and reload screenshots are
byte-identical. Exact hashes and the migration limitation are recorded in
`analysis/runtime-evidence.toml`.

The opening menu family is implemented separately because it bypasses command `$08`.
CPU `$81:85DF-$81:8629` copies one of two fixed title streams from `$84:A1D8` or
`$84:A1FA` to WRAM `$0A00`, and `$80:997B/$80:9B2C` renders them with the shared
glyph compositor. Both variants are translated and centered: `New Game / Options`
without a save and `Continue / New Game / Options` when a valid save is present.
The reachable New Game submenu at `$84:A22E` is `Start New Game / Enter Password`.
Options uses fixed records at `$84:A254/$84:A266` for `Sound Stereo / Sound Mono`
and twenty `$12`-byte records at `$84:A278-$84:A3DF` for `BGM 00-19`. The BGM
translation preserves each record's native numeral words and restores its label to
the original left field. Final runtime captures place the combined BGM row at visual
midpoint x=`124.5-125`, matching the original menu center.
The shared selector rows for the title, New Game, and Options menus are positioned
two pixels above their original Y coordinates.

Every translated stream or fixed record remains in its original allocation and
retains its original line-cell structure or record stride. Character-level offsets
allow odd-positioned English labels to remain centered within the original cells.
Packed words set bit 15 and contain two independent seven-bit character IDs; ID 0
is blank. The shared compositor renders each character from an ordinary 16x16 glyph
record and advances six pixels, so the existing 12-pixel cell allocation holds two
Latin characters without stream relocation or pointer changes. Words with bit 15
clear continue through the original Japanese compositor unchanged.
The recap is intentionally concise where the original allocations are small.
The 119 nonblank Latin IDs use mutually disjoint ordinary glyph records. The 50
extended records are selected only from zero-filled sources absent from every decoded
original text stream. Original source blocks are pinned by a cryptographic digest
before the translation builder overwrites them.

The five-name editor at CPU `$81:8739` keeps each field at five stored words but now
uses those words as ten independent character positions. Fresh name entry uses a
relocated first picker page at CPU `$84:F142` / ROM `$027142` and selection map at
`$84:F322` / `$027322`, providing 69 basic Latin characters. `X:Page` selects the
relocated second page at `$84:F232` / `$027232` and map at `$84:F3CC` / `$0273CC`,
with 50 accented letters, macron vowels, and name-friendly symbols. Insertion updates either half of the selected
packed word, and the cursor advances six pixels per position. B is navigation-only:
at cursor zero it is a no-op, while at every other position it moves back one character
without modifying any of the five fields. This includes moving from the first position
of rows 2-5 to the previous row's final position. Bit 15 selects packed Latin rendering.
Generated localized defaults already use that ordinary packed format, so the first and
later insertions overwrite only the selected character and preserve the other nine
positions. A legacy bit-15-clear field is blanked and converted before its first
packed-character insertion; other fields remain intact.

Save/load continues copying the original 50-byte `$0C00-$0C31` block verbatim. The
password editor uses a separate sparse one-character-per-word layout and requires its
original symbol values. WRAM `$0216` is the mode discriminator: zero selects the
relocated Latin pages, maps, insertion behavior, and six-pixel cursors; nonzero selects
the original pages at `$84:A3E0/$84:A4D0`, original maps at `$81:8D56/$81:8E00`, and
the original password cursor geometry. The password-owned records at `$84:A630`,
`$84:A660`, and `$84:A690` also remain byte-identical. `$84:A630` is confirmed as the
password control legend; the exact meanings of the latter two status records remain
to be classified before translation.

The compositor hook at CPU `$80:9B2C`, its `$80:EBCF-$80:EDB2` implementation, the
mode-aware insertion hook at `$81:8AD7`, shared page-loader hook at `$81:8B5E`, and the
picker/name cursor hooks at `$81:8BDD/$81:8C38` are assembled from
`asm/dual_format_text.asm`. WRAM `$0216` zero sends insertion through the packed-Latin
fresh-name editor; nonzero reproduces the hook's displaced comparison and rejoins the
original password map/store/redraw path at `$81:8ADD`. Fresh-name picker entries retain the original 12-pixel
navigation grid but use a six-pixel red selector;
the name-field character selector uses the same six-pixel width, while the wider DONE
selector remains unchanged. Both selector types are positioned two pixels above their
original Y coordinates. Fifth-field DONE preserves the original
routine-level `RTS`, blank packed IDs advance without invoking the legacy glyph
compositor, and edits redraw only their five-word field. The bounded redraw explicitly
restores the name surface to 8 tiles wide and 10 tiles high before rendering, then sets
DMA source offset `$EF`, exclusive end `$ED`, and name-surface VRAM base `$1120`. This
keeps both halves of each 16-pixel glyph inside the transferred `$0100`-byte row even
after a picker-page redraw changed the shared compositor dimensions.
Supporting editor code occupies reviewed all-`$FF` padding at `$81:DA50-$81:DD13`,
and relocated Latin resources occupy `$84:F142-$84:F475`. The original navigation-only
B handler at `$81:8B50-$81:8B5C`
is retained byte-for-byte. The original
bytes for every hook and padding allocation are pinned by an aggregate SHA-256 before
Asar applies the tracked patch.

Reviewed runtime conclusions, the exact historical ROM identities they apply to, and
remaining limitations are recorded in `analysis/runtime-evidence.toml`. Raw captures
remain local and ignored; documentation does not rely on ephemeral `/tmp` paths.

The current translated ROM SHA-256 is
`24821991630b6064111ce969fd36b6b688e3346e4d763ac1e3b5c0b9efd24163`.
Its mode-aware `$81:8AD7` dispatcher bypasses translated name-only insertion work in
password mode and rejoins the original path at `$81:8ADD`. Static binary tests pin the
unchanged original password continuation through `$81:8B4F`, including the original
selection maps, one-word store, `$81:8BAA` redraw call, and 25-position cursor limit.

The original role prompts are translated as `Player`, `Friend`, `Bully`, `Girl`, and
`Teacher`. Their joke defaults are localized as `Aiyah`, `Buddy`, `Meanie`, `Sally`,
and `Teach`; every default still occupies exactly five stored words. The four-cell
Y-button hint is `Y:Clr`, matching the routine that blanks all 25 cells across all
five fields.

## Translation style policy

Apply the following policy to all translations in this project, not only the
automatic opening:

- Aim for natural, idiomatic English while remaining faithful to the original
  meaning. Do not reproduce Japanese syntax mechanically when it would sound
  awkward in English.
- Preserve characterization, emotional force, humor, and level of formality or
  coarseness. A translation should create substantially the same impression as
  the source dialogue in its scene.
- Do not sanitize genuinely present swearing, vulgarity, insults, threats, or
  rough speech. Render them with comparably forceful, natural English.
- Do not add profanity or make a line harsher than the Japanese supports merely
  because the scene is intense.
- Prefer contextually natural wording over a formally literal but misleading or
  awkward rendering. For example, a character weirded out by an eccentric pose
  should sound weirded out, rather than as though they cannot intellectually
  understand it.
- Do not embellish dialogue with details inferred only from the visuals, wider
  story, or translator expectations. Add context only when English requires it
  to communicate meaning already present in the source.
- When ROM space requires concise wording, preserve the line's most important
  meaning, tone, and character voice rather than filling available space or
  retaining every source-language construction.
- Record genuine ambiguities and translation uncertainty in appropriate local
  working notes or non-expressive metadata instead of silently inventing a
  definitive interpretation.

## Local ignored material

Extraction tooling may generate these files locally:

```text
strings.tsv
text_layout.tsv
```

They may contain decoded Japanese, reversible unknown-byte tokens, and other ROM-derived
working data. They are git-ignored and must not be committed. The original ROM remains
the authoritative source for the Japanese text.