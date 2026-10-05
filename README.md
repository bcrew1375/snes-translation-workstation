# Multi-Project SNES Translation Workstation

Source-only SNES/Super Famicom translation and reverse-engineering workstation modeled on the Game Boy translation repository. It separates reusable ROM mapping, bounded patching, text allocation, SNES graphics, project loading, analysis coverage, and auditing from game-specific formats and translations.

The repository does **not** distribute ROMs, extracted media, disassemblies, decoded dialogue, or generated ROM-derived assets.

## Environment

The devcontainer includes:

- **bsnes-plus** for SNES emulation and debugger-oriented analysis (VRAM/tilemap/sprite viewers, breakpoints, usage logging).
- **Asar 1.91** for 65C816/SPC700/Super FX assembly and patch workflows.
- Python/Pillow for project-specific analysis, text, graphics and bounded patch generation.
- Xvfb/Openbox/x11vnc/noVNC on port 6080 for a browser-accessible GUI.

## Core commands

```sh
make self-test
make projects
make test-toolkit
snes-rom-info roms/<project>/original.sfc
snes-offset --mapping lorom 02:8000
snes-offset --mapping hirom C1:2345
snes-hexdump ROM 80:8000 64
snes-tiles ROM 0x10000 --bpp 4 --count 256 -o build/tiles.png
snes-run ROM
snes-debug ROM
snes-desktop status
```

## Addressing

Never conflate 24-bit SNES CPU addresses with ROM file offsets. `snes-offset` currently provides strict standard LoROM and HiROM conversion. ExHiROM/ExLoROM and enhancement-chip mappings must be implemented/tested per project rather than guessed.

Copier headers (512-byte SMC headers) are detected by the ROM inspector. Projects should explicitly declare whether their canonical input includes one.

## Projects

Each game belongs under `projects/<project-id>/` with `project.toml`, a Python adapter under `src/`, translation manifests, reviewed analysis metadata, and ROM-independent tests. The generic toolkit must not import game projects.

The starter intentionally contains no copyrighted game project. Copy the project structure from the Game Boy workstation when adding the first SNES title, but use `platform = "snes"` and `.sfc` paths.

## Reverse engineering

A generic SNES disassembler is deliberately not treated as authoritative. 65C816 decoding depends on M/X state and SNES ROMs freely mix code, data and compressed assets. Prefer evidence-driven static analysis plus bsnes-plus usage logging/debugging. If a project develops a rebuildable disassembly, retain a byte-identical `MATCH` path and progressively replace opaque/raw regions with verified source.
