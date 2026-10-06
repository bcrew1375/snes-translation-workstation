# Multi-Project SNES Translation Workstation

Source-only SNES/Super Famicom translation and reverse-engineering workstation modeled on the Game Boy translation repository. It separates reusable ROM mapping, bounded patching, text allocation, SNES graphics, project loading, analysis coverage, and auditing from game-specific formats and translations.

The repository does **not** distribute ROMs, extracted media, disassemblies, decoded dialogue, or generated ROM-derived assets.

## Environment

The devcontainer includes:

- **bsnes-plus** for SNES emulation and debugger-oriented analysis (VRAM/tilemap/sprite viewers, breakpoints, usage logging).
- **mesen-agent** for bounded, windowless automation with JSON Lines evidence,
  24-bit S-CPU breakpoints, physical/CPU-relative memory inspection, traces,
  state dumps, and screenshots. It supplements rather than replaces bsnes-plus.
- **Asar 1.91** for 65C816/SPC700/Super FX assembly and patch workflows.
- **A vendored Asar disassembler** from `Yoshifanatic1/SNES-ROM-Framework`
  (`tools/vendor/snes-rom-framework/`) that decodes 65816, SPC700 and Super FX.
  It is pinned, with provenance in that directory's `UPSTREAM.md`.
- **Noto CJK fonts.** Japanese text is unreadable without them; the original
  text cannot be reviewed or translated otherwise.
- Python/Pillow for project-specific analysis, text, graphics and bounded patch generation.
- Xvfb/Openbox/x11vnc/noVNC on port 6080 for a browser-accessible GUI.

## Projects

Each game owns its ROM:

```text
projects/<project-id>/
    project.toml
    rom/original.sfc        user input, git-ignored
    src/                    game-specific adapter
    analysis/               reviewed findings and region manifests
    translation/
    tests/
```

Tracked translation files contain repository-authored English plus non-expressive ROM
references such as stable IDs, 24-bit CPU addresses, file offsets, pointer locations,
stream lengths, and source hashes. Full decoded Japanese catalogs, raw source streams,
and text-layout dumps are generated locally from the user-supplied ROM and remain
git-ignored.

The intended separation is:

```text
original ROM -> local extractor -> ignored decoded-source working catalog

original ROM + tracked references/hashes + tracked English patches
    -> translated ROM
```

The original ROM is therefore authoritative for the Japanese source. A clean checkout
plus the supported ROM must be able to regenerate local analysis data and build the
translation without distributing decoded original dialogue.

## Core commands

```sh
make self-test                    # environment + synthetic-ROM checks, no ROM needed
make disassemble PROJECT=<id>     # readable 65816 disassembly -> disassembly/
make disassemble PROJECT=<id> BANK=3
make rebuild   PROJECT=<id>       # write and keep byte-faithful Asar sources
make verify    PROJECT=<id>       # prints MATCH or exits nonzero
make build     PROJECT=<id>       # verify, then build the translated ROM
make test      PROJECT=<id>
make analysis  PROJECT=<id>
make audit
```

Direct tool use:

```sh
snes-rom-info projects/<project>/rom/original.sfc
snes-offset --mapping lorom 02:8000
snes-offset --mapping hirom C1:2345
snes-hexdump ROM 80:8000 64
snes-tiles ROM 0x10000 --bpp 4 --count 256 -o build/tiles.png
snes-tile-scan ROM --bank 0x37 --bpp 4 --columns 32 --normalize
snes-disassemble ROM --outdir disassembly --bank 0
snes-fidelity ROM
snes-run ROM
snes-debug ROM
# Direct `bsnes-plus ROM` is shadowed by tools/bin and receives the same 60 Hz pacing.
# BSNES_UNTHROTTLED=1 disables pacing; BSNES_FRAME_HZ=50 selects a PAL cap.
snes-automate ROM --artifact-dir build/runtime/probe --frames 600 --timeout 30 \
  --breakpoint 'SnesMemory:0x008000:x' --pc --screenshot --state-json
snes-desktop status
```

## Headless runtime evidence

`snes-automate` wraps the pinned `mesen-agent` backend. Every run receives an
isolated emulator home plus finite frame and wall-clock limits. Standard output
is retained as `events.jsonl`; diagnostics go to `stderr.log`; and
`metadata.json` records the backend revision, exact command, source-ROM size and
SHA-256, script hashes, exit status, final summary, and whether the run met the
wrapper's trust conditions.

Repeatable `--input 'PORT:BUTTONS@START-END'` options provide deterministic
controller schedules. Repeatable `--script` options load sandboxed debugger Lua
for state-aware callbacks; filesystem and network access remain disabled.

Within the repository, runtime artifacts are accepted only under `build/` or
`projects/<id>/local/`, both of which are ignored. The wrapper refuses to reuse
an artifact directory containing an earlier managed run.

A run is marked trustworthy only when the backend exits successfully, emits a
final successful summary, does not hit the host timeout, and reports zero Lua
errors. This establishes reproducible emulator evidence; it does not by itself
prove that an inferred game-specific meaning is correct. Important findings
should still be cross-checked against static evidence and, where useful,
bsnes-plus.

Screenshots require a decoded video frame. An execute breakpoint reached during
reset may stop too early for capture; use a separate finite-frame run for the
screenshot rather than weakening the breakpoint evidence.

## Two assembly paths, kept separate

`make disassemble` produces **readable** 65816/SPC700/Super FX assembly using a
vendored Asar disassembler. It decodes real instructions and tracks the M/X
processor-size flags, but it is a linear sweep: it does not distinguish code from
data, does not resolve cross-bank references, and its labels are generated. Use
it to *read* a bank. Do not build a ROM from it.

`make verify` is the rebuild guarantee. `tools/bin/snes-fidelity` emits every
ROM byte verbatim — one `org` per bank plus an `incbin` of that bank's bytes —
and Asar reproduces the input exactly. This path makes no semantic claims, so
`MATCH` proves only that the assembly pipeline is lossless; it never implies the
disassembly is correct.

The four Asar behaviours this depends on were verified experimentally and are
encoded in `toolkit/snesworkbench/asmbuild.py`:

- an explicit `lorom`/`hirom` directive is required;
- `incbin` accepts no offset or length, so the ROM is chunked per bank;
- each bank needs its own explicit `org`; a repeated one silently resets;
- Asar prepends a 512-byte copier header that must be stripped.

## Repository policy

`make audit` rejects ROMs, generated binaries, extracted media, disassemblies,
decoded original-language catalogs, unreviewed Japanese/CJK content, and suspicious
embedded byte arrays. It permits validated English patch, ROM-reference, and allocation
manifests. Narrowly reviewed character/encoding tables may eventually allow isolated
CJK characters in a designated column, but never dialogue. Disassembly and decoded
source output are reproducible and remain local because they are ROM-derived. See
`.gitignore` and `tools/bin/snes-repo-audit`.

The audit is a technical safeguard and is not legal advice.

## Addressing

Never conflate 24-bit SNES CPU addresses with ROM file offsets. `snes-offset` currently provides strict standard LoROM and HiROM conversion. ExHiROM/ExLoROM and enhancement-chip mappings must be implemented/tested per project rather than guessed.

Copier headers (512-byte SMC headers) are detected by the ROM inspector. Projects should explicitly declare whether their canonical input includes one.

## Projects

Each game belongs under `projects/<project-id>/` with `project.toml`, a Python adapter under `src/`, translation manifests, reviewed analysis metadata, and ROM-independent tests. The generic toolkit must not import game projects.

The starter intentionally contains no copyrighted game project. Add one under `projects/<project-id>/` with `platform = "snes"` and `.sfc` paths.

## Reverse engineering

A generic SNES disassembler is deliberately not treated as authoritative. 65C816
decoding depends on M/X state and SNES ROMs freely mix code, data and compressed
assets.

The disassembly produced here is a **linear sweep**: it decodes instructions
correctly and tracks M/X flag state, but it cannot tell code from data, and a
cleanly decoding instruction stream is still not proof the bytes were code.
Treat its output as a starting point to be checked against evidence.

The rebuild guarantee is therefore independent of the disassembler. Rebuild from
byte-faithful sources, confirm `MATCH`, and only then progressively replace
opaque regions with reviewed source, re-verifying after each change. A change
that stops reproducing the original ROM byte-for-byte is a regression until
proven otherwise.
