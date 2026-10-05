# Multi-Project SNES Translation Workstation

Source-only SNES/Super Famicom translation and reverse-engineering workstation modeled on the Game Boy translation repository. It separates reusable ROM mapping, bounded patching, text allocation, SNES graphics, project loading, analysis coverage, and auditing from game-specific formats and translations.

The repository does **not** distribute ROMs, extracted media, disassemblies, decoded dialogue, or generated ROM-derived assets.

## Environment

The devcontainer includes:

- **bsnes-plus** for SNES emulation and debugger-oriented analysis (VRAM/tilemap/sprite viewers, breakpoints, usage logging).
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
snes-desktop status
```

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
and decoded original-language catalogs. Disassembly output is reproducible via
`make disassemble` but is never committed, because it is ROM-derived. See
`.gitignore` and `tools/bin/snes-repo-audit`.

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
