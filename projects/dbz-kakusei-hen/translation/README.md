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

Every translated stream remains in its original allocation and retains its original
line-cell structure. Two narrow Latin characters are rendered in each existing
12-pixel cell, avoiding stream relocation, pointer changes, or renderer changes.
The recap is intentionally concise where the original allocations are small.
The paired Latin glyphs use both zero-filled records and nonblank orphan records
that are absent from all decoded original text streams. Their source blocks are
mutually disjoint and their original contents are pinned by a cryptographic digest
before the translation builder overwrites them.

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