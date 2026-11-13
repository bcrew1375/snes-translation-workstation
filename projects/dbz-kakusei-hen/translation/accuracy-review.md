# English translation accuracy review

Reviewed October 21, 2026.

This review covered the 286 dialogue records implemented at the time of the full
accuracy audit. Checkpoint 11 subsequently added 10 source-reviewed Goku–Tien
dialogue records, bringing the current implemented dialogue total to 296.
The audit also covered 31 fixed labels/choices, 25 menu records, 7 name-entry records, and 8
battle-HUD records. It also checked all 121 approved glossary entries that govern
North American/Funimation-style names and terminology.

The review directly compared the supported original ROM's Japanese streams and
rendered glyph transcriptions with the current English, checked speaker and route
ownership against static/runtime evidence, and evaluated meaning, characterization,
tone, terminology, pagination, visible line limits, available reviewed storage, and
concise HUD constraints. English is required to preserve the source's number of
four-line text boxes, but it is not restricted to the source byte length when in-place
padding or reviewed relocation space safely permits a fuller rendering.
Substantial decoded Japanese, raw streams, glyph sheets, and the record-by-record
working ledger remain under the ignored `local/` directory.

The fresh dialogue pass classified 276 records as keep, 2 as optional polish, 2 as
requiring emulator-context checks, 2 as strong editorial improvements, and 2 as
required corrections. The four evidence-supported changes were implemented; optional
and context-dependent candidates were retained rather than changed speculatively.

## Localization standard and exceptions

The project consistently follows modern North American anime/game terminology,
including `Krillin`, `Tien`, `Chiaotzu`, `Master Roshi`, `Mercenary Tao`,
`World Tournament`, `Dodon Ray`, `Super Dodon Ray`, `Senzu`, and related
Funimation-recognizable forms. Source-specific exceptions remain intentional:

- `Kakarot` is retained when Vegeta addresses Goku by his Saiyan name.
- `Junior` is used for Piccolo Jr. during the 23rd World Tournament.
- `Shen` is Kami's contestant alias; `Kami` is his identity.
- `Crane Hermit` is Tien and Mercenary Tao's former master. `Master Shen` is
  prohibited because it conflates him with Kami's alias.
- Standalone `Senzu` is acceptable in natural dialogue even though the glossary's
  full item name is `Senzu Bean`.

## Review results

The previously reviewed opening, recap, tournament, preliminary, finals, menu,
choice, and name-entry translations were re-audited from the Japanese source rather
than accepted from the prior review ledger. Most remain accurate after the corrections
already incorporated on October 19. Those corrections include the Korin Tower account,
Crane Hermit terminology, Senzu explanation, Goku's objection to the announcer, and
Dodon Ray naming.

The newly added recognized-route dialogue from selectors `$02D6-$0308` and the
first battle HUD were reviewed in full. The second editorial pass corrected several
literal or selector-misaligned lines in the Krillin/Shen and Yamcha/Shen scenes and
restored exact source-box pagination across all 286 dialogue records. The concise HUD
renderings
`Power`, `Rush`, and `Open` are retained as constrained UI localizations: the source
concepts are battle power, a body-check/rush attack, and an unguarded state, while
the available packed fields and current font prevent the longer preferred forms
`Power Level`, `Tackle`/`Body Blow`, and `Unguarded` from fitting reliably.

## Corrections made in this pass

- `finals_transition_12` (`$028D`): corrected the subject of the fall. The old man
  wins as a consequence of tripping; the earlier English incorrectly said that his
  opponent fell over.
- `yamcha_shen_23` (`$02FA`): restored Yamcha's complaint that Kami is babbling
  incomprehensible nonsense, restored `I have no choice`, and replaced the overly
  formal voice with natural dialogue while retaining the source's three-box pacing.
- `chichi_x_10` (`$024E`): expanded the compressed `I really did promise / to take
  a bride` to `I sure did say I'd / come get a bride`. The revision preserves all
  three source details: Goku definitely remembers saying it, he said he would come,
  and he would get/take a bride. `Get a bride` also preserves the food-related
  misunderstanding in the next record.
- Added fixed bank-`$88` table entry `$04` as `Stands`, replacing the Japanese
  spectator-stands header that remains visible during the late Tien/Tao spectator
  dialogue, including the Crane Hermit's `You crushed him!!` threat.
- `goku_chichi_recognized_02` (`$02C8`): changed the abstract `Marriage works that
  way` to `That's how married couples are.` The source `夫婦ってこういうもんだべさ`
  describes what married couples are like and uses Chi-Chi's rustic sentence ending.
- `tien_tao_26` (`$02B6`): changed the literal `forget what you did` to the natural
  and contextually accurate offer to let what Tao did to Chiaotzu go.
- `tien_tao_06` (`$02A2`): replaced `Tien and your companions have only a slim
  chance` with the Crane Hermit's sarcastic `Let's hope Tien and you lot have even
  the slightest chance`. The source `天津飯や きさまらに わずかでも勝ちめが
  あればいいがな` addresses the group contemptuously and questions whether they
  have any chance at all rather than affirming that they have a small one.
- Removed `Demon King Piccolo` as an alias of `Junior`/Piccolo Jr.; that title belongs
  to King Piccolo and conflated two distinct characters.
- Removed `Evil Containment Wave` and `Mafuba` as aliases of `Four Witches Technique`;
  they are a separate technique rather than alternate names.
- `tien_tao_00`: retained the source title in Krillin's recognition: `The Crane Hermit!`.
- Added shared selector `$001C` as Goku's `Right!!` after Tao's challenge.
- Added recognized-route matchup selector `$0293` as `Goku vs Chi-Chi`; `$0F25`
  remains the unrecognized-route `Goku vs Anonymous` card.
- Standardized the remaining finals qualifier labels to full `Number` wording.
- `tien_tao_27`: corrected Tao's meaning to `That little victory made you cocky?`.
- `tien_tao_34`: restored the source meaning `with his ki alone!!`.
- `yamcha_shen_31` (`$0302`): changed `That old man really` to the equivalent
  `That old man truly`, allowing the authoritative line to remain in its pinned
  source allocation instead of requiring a fragmented 124-byte relocation.
- `yamcha_shen_28`: `G-God!!` → `K-Kami!!` to use the approved identity name.
- `yamcha_shen_31`: removed `God Shen` and preserved Yamcha's Japanese
  `Shen → Shenron → Kami` association using `Shen`, `Shenron`, and `Kami`.
- `krillin_match_end_07-$02E0`: replaced literal constructions such as `Nothing I
  can do`, `It seems even I`, and the split `martial / artist`; restored the source's
  meaning that taking over the world may not be easy and that Yamcha drew a favorable
  opponent.
- `yamcha_shen_00-$02FA`: realigned several English entries with their exact source
  selectors, restored the announcer's groin-hit gag and embarrassed follow-up, and
  rewrote Kami and Yamcha's exchange in natural English without losing the borrowed-
  body/possession explanation or martial-artist critique.
- `semifinals_00-$0307`: replaced stiff announcement prose and `Just as I thought`
  with natural English while retaining the original two-box pacing.
- Added explicit blank/page-padding lines to records that previously ended one or
  more boxes early. These are structural pagination changes, not invented dialogue.

Ambiguous short cries and highly constrained labels were retained rather than made
more specific than the Japanese supports.

Optional wording candidates were deliberately not changed where the current English
is defensible. In particular, `$020B` compresses Roshi's thought across box boundaries
but preserves the scene's inference, and `$026D` is accurate despite room for a more
aggressive Junior voice. The one-letter `$02C9`/`$02D4` stammer boxes remain pending
an emulator pacing check; their wording was not changed from static evidence alone.

## Validation status

The original byte-faithful rebuild still reports `MATCH`. Manifest/source hashes,
selector ownership, line-width checks, and exact source-box pagination remain covered
by the project tests. English lines now terminate after their final packed glyph cell;
only explicit newlines and blank lines emit `$000A`, so Japanese-width trailing cells
are no longer written as padding glyphs.

After all records and aliases are validated, compact in-place streams contribute only
their post-`$0000` suffixes as provenance-labeled allocation regions. Fully claimed
aliases may share the compact in-place target; any unclaimed selector that still owns
a source forces relocation. This supplies enough reviewed bank-$99 capacity for the
complete translated build without speculative free-space claims or cross-bank runtime
changes.
