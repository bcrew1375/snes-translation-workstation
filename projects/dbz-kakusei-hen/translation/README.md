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

- `patches/*.toml` records stable IDs, source locations/lengths/hashes, English text,
  workflow status, and non-expressive notes. The `english` value is an array in
  which each string is one explicit displayed line. Files are loaded in lexical
  filename order, and records retain their declared order within each file.
- `references.toml` records pointer-table or direct-reference metadata without source
  dialogue.
- `ranges.toml` records reviewed allocation ranges for translated streams and custom
  glyph storage.
- `menu.toml` records the fixed title, New Game, sound-mode, and indexed BGM menu
  records, including record type and reviewed character-level alignment offsets.
- `name_entry.toml` records both 85-entry name-picker pages, their selection maps,
  the five localized default names, and the fixed English name-editor prompts.
- `choices.toml` records pointer-selected fixed labels and opening choices, source
  hashes, pointer locations, preserved native icon prefixes where applicable, and
  deterministic same-bank relocation destinations.
- `glossary.toml` records the project's canonical English terminology for names,
  terms, techniques, places, races, organizations, and story arcs. Each record
  contains a stable `id`, a `category`, the `canonical` English form, the
  `aliases` array for lookup, `usage_notes` on capitalization and context, and a `status`
  field. The glossary contains no decoded Japanese text, no raw ROM data, and no
  reconstructed dialogue. It uses the modern North American anime and game
  localization as the primary standard: Frieza, Krillin, Jeice, King Kai, Grand
  Elder Guru, World Tournament, Special Beam Cannon, Destructo Disc, Tri-Beam,
  Spirit Bomb, Kaio-ken, and related forms. The aliases array may contain manga-
  oriented or source-name alternatives (for example Freeza, Kuririn, Tenshinhan,
  Kaio, Kienzan, Makankosappo, Tenkaichi Budokai) for identification purposes,
  but the canonical field is the required output form.

The translation builder concatenates the ordered `patches/*.toml` collection and
joins it to `references.toml` by stable `id`;
selectors are not inferred from patch-column positions. Only confirmed ranges whose
names begin with `free_text_` are eligible for relocated text allocation. The reviewed
`free_text_bank_99_tail` range is the production allocation used by longer tournament
records. Other structural gaps and streams lacking a known scenario-root reference
remain reserved until all reference paths are validated.

The implemented automatic opening covers the four narration panels at command-`$08`
selectors `$07E1-$07E4` and all 22 text records shown in the following recap before
the title screen returns. Runtime tracing of scenario root `$0170` established the
post-fade selector order; the tracked reference manifest records every selector and
target without reproducing source dialogue.

The opening 23rd World Tournament scene is implemented for command-`$08`
selectors `$0200-$021A`. Sixteen records fit their original bank-$99
allocations; eleven longer records relocate deterministically into the reviewed
all-`$FF` tail at CPU `$99:F8EE-$99:FAA1` / ROM `$0CF8EE-$0CFAA1`, with only
their same-bank selector pointers updated.

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
edge of a box. Four short opening-recap records use the unclassified `default`
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
`$021C` moves from `$99:906E` to `$99:FAA2`, and `$021B` moves from `$99:9060`
to `$99:FAC0`. Only pointer words `$99:8438` and `$99:8436` are updated.

After either response, all three result values reconverge on the same Master
Roshi dialogue. Checkpoint 2 includes every intervening command-`$08` stream:
selectors `$021D-$0221` cover Roshi's surprise, the returning competitors'
greetings from Chiaotzu and Tien, Yamcha's observation, and Krillin's explanation
that their changed appearances left Roshi
stunned. Four streams fit in place; `$021F` relocates deterministically within the
reviewed bank-`$99` text pool at `$99:FAD0-$99:FAF3`. Their consecutive pointer slots are
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
`9bdb3780349db284be6eefd3ad96351d4440548a6662bf37430d685f1b12afee`.
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