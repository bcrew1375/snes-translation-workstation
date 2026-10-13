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

The following X/Y/B choice is also a fixed resource rather than a command-`$08`
text stream. Its option pointers at `$98:9B2A-$98:9B2E` retain X/Y/B order, and
each option preserves the original colored button-icon and spacer words. The
localized rows are `You're bleeding!`, `Are you sick?`, and `You look sexy.`
Command `$07` at CPU `$91:8179` / ROM `$088179` and its following scenario
branch bytes are unchanged. The bank-`$88` entry at `$88:8018` is the separate
`World Tournament Arena` location bar, not a quiz heading.

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
`359ea57bd4bab983efcf527dba7a9e5465c3e27e1c0bce51e07487ed152bce80`.
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