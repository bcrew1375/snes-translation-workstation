# Translation source

This directory contains repository-authored English translation data and
non-expressive metadata that identifies source streams in the user-supplied ROM.

Tracked files must not contain decoded Japanese dialogue, substantial transliterations,
raw source streams, or long byte arrays capable of reconstructing original text.

## Tracked manifests

- `patches.tsv` records stable IDs, source locations/lengths/hashes, English text,
  workflow status, and non-expressive notes.
- `references.tsv` records pointer-table or direct-reference metadata without source
  dialogue.
- `ranges.tsv` records reviewed allocation ranges for translated streams and custom
  glyph storage.
- `menu.tsv` records the fixed title, New Game, sound-mode, and indexed BGM menu
  records, including record type and reviewed character-level alignment offsets.
- `name_entry.tsv` records both 85-entry name-picker pages, their selection maps,
  the five localized default names, and the fixed English name-editor prompts.
- `glossary.tsv` records the project's canonical English terminology for names,
  terms, techniques, places, races, organizations, and story arcs. Each record
  contains a stable `id`, a `category`, the `canonical` English form, pipe-separated
  `aliases` for lookup, `usage_notes` on capitalization and context, and a `status`
  field. The glossary contains no decoded Japanese text, no raw ROM data, and no
  reconstructed dialogue. It uses the modern North American anime and game
  localization as the primary standard: Frieza, Krillin, Jeice, King Kai, Grand
  Elder Guru, World Tournament, Special Beam Cannon, Destructo Disc, Tri-Beam,
  Spirit Bomb, Kaio-ken, and related forms. Aliases column may contain manga-
  oriented or source-name alternatives (for example Freeza, Kuririn, Tenshinhan,
  Kaio, Kienzan, Makankosappo, Tenkaichi Budokai) for identification purposes,
  but the canonical column is the required output form.

The translation builder joins `patches.tsv` and `references.tsv` by stable `id`;
selectors are not inferred from patch-column positions. Only confirmed ranges whose
names begin with `free_text_` are eligible for relocated text allocation. No such
production range is currently declared. Structural gaps and streams lacking a known
scenario-root reference remain reserved until all reference paths are validated.

The implemented automatic opening covers the four narration panels at command-`$08`
selectors `$07E1-$07E4` and all 22 text records shown in the following recap before
the title screen returns. Runtime tracing of scenario root `$0170` established the
post-fade selector order; the tracked reference manifest records every selector and
target without reproducing source dialogue.

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
uses those words as ten independent character positions. The first picker page and
CPU `$81:8D56` selection map provide 69 basic Latin characters. `X:Page` selects a
distinct second page and `$81:8E00` map with 50 accented letters, macron vowels, and
name-friendly symbols. Insertion updates either half of the selected
packed word, and the cursor advances six pixels per position. B is navigation-only:
at cursor zero it is a no-op, while at every other position it moves back one character
without modifying any of the five fields. This includes moving from the first position
of rows 2-5 to the previous row's final position. Bit 15 selects packed Latin rendering.
Generated localized defaults already use that ordinary packed format, so the first and
later insertions overwrite only the selected character and preserve the other nine
positions. A legacy bit-15-clear field is blanked and converted before its first
packed-character insertion; other fields remain intact.

Save/load continues copying the original 50-byte `$0C00-$0C31` block verbatim. The
password editor uses a separate sparse one-character-per-word layout, so its existing
position logic is not changed; its picker selections remain compatible because each
picker entry stores a packed word whose first ID is the selected character and whose
second ID is blank.

The compositor hook at CPU `$80:9B2C`, its `$80:EBCF-$80:EDB2` implementation, the fresh
name insertion hook at `$81:8AD7`, and the picker/name cursor hooks
at `$81:8BDD/$81:8C38` are assembled from `asm/dual_format_text.asm`. Ordinary picker
entries retain the original 12-pixel navigation grid but use a six-pixel red selector;
the name-field character selector uses the same six-pixel width, while the wider DONE
selector remains unchanged. Both selector types are positioned two pixels above their
original Y coordinates. Fifth-field DONE preserves the original
routine-level `RTS`, blank packed IDs advance without invoking the legacy glyph
compositor, and edits redraw only their five-word field. The bounded redraw explicitly
restores the name surface to 8 tiles wide and 10 tiles high before rendering, then sets
DMA source offset `$EF`, exclusive end `$ED`, and name-surface VRAM base `$1120`. This
keeps both halves of each 16-pixel glyph inside the transferred `$0100`-byte row even
after a picker-page redraw changed the shared compositor dimensions.
Supporting editor code occupies reviewed trailing all-`$FF` padding at
`$81:FE00-$81:FFA0`. The original navigation-only B handler at `$81:8B50-$81:8B5C`
is retained byte-for-byte. The original
bytes for every hook and padding allocation are pinned by an aggregate SHA-256 before
Asar applies the tracked patch.

Earlier trusted October 11, 2026 Mesen captures against translated ROM SHA-256
`f60cb9d4c6c1b01d70c9275526bdad1e88b86eba494339145b0fb39f40ea8ce6` exercised
ordinary B navigation after inserted characters in all five rows. The cursor
transitions were `3 -> 2`, `11 -> 10`, `21 -> 20`, `31 -> 30`, and `41 -> 40`.
Paired before/after captures confirmed that WRAM `$0C00-$0C31` remained
byte-identical in every case. The local evidence and comparison report are under
`/tmp/dbz-name-navigation-only-trusted-20261011`.

The current translated ROM SHA-256 is
`1091629245703d49d2b447ddde511559b84db12ba9847a44dfececb32890e73f`.
Trusted October 11, 2026 Mesen captures against that ROM confirmed the two corrected
paths. Selecting page-one `B` at the first position changed `Aiyah` to `Biyah` while
preserving the remaining nine positions and all four other fields. Switching to page
two and selecting `Á` changed it to `Áiyah`; captured WRAM showed page `$0001`, restored
compositor dimensions `$020E=$0008` and `$0210=$000A`, and nonblank data in both halves
of the complete `$0100`-byte staged name row. The screenshots and comparison report are
under `/tmp/dbz-name-overwrite-fix-20261011`.

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