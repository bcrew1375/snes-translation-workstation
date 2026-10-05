# SNES-ROM-Framework (vendored)

These files are vendored from an upstream project and are **not** covered by this
repository's own authorship. Do not hand-edit them; upgrade by re-vendoring.

## Upstream

- **Project:** `Yoshifanatic1/SNES-ROM-Framework` — "SNES ROM Framework"
- **Source:** <https://github.com/Yoshifanatic1/SNES-ROM-Framework>
- **Pinned commit:** `7f0fec12bf21551727f80bf7ec261162f40e68f9`
- **Upstream version:** Framework V1.4.0 (committed 2025-02-14)
- **License:** GPL-3.0 (`LICENSE` in this directory)

## What was vendored and why

Only the parts that are useful as *analysis* input for SNES reverse engineering:

| Path | Purpose |
| --- | --- |
| `Extras/SNESASMDis.asm` | 65816 disassembler written as an Asar macro script. Tracks the `!16BitA` / `!16BitXY` processor-size flags so operand widths decode correctly, and emits `CODE_XXXXXX` labels. |
| `Extras/SPC700ASMDis.asm` | SPC700 disassembler. Kept separate from the 65816 decoder so APU code is never misread as main-CPU code. |
| `Extras/SuperFXASMDis.asm` | Super FX disassembler. |
| `Global/MemoryMap/*.asm` | Memory-map definitions for LoROM, HiROM, Fast variants, ExLoROM, ExHiROM, SA-1, SDD1, SPC7110, Super FX, Satelliview, and no-ROM layouts. |
| `Global/HardwareRegisters/*.asm` | Hardware register definitions (SNES, SA-1, DSP1-4, SDD1, SPC700, SPC7110, Super FX, ST010/011/018, MSU1, CX4, OBC1, Satelliview, Super Game Boy, SRTC). |

Deliberately **not** vendored:

- `Global/asar.exe` and the other Windows `.exe`/`.dll` helpers. The container
  builds and uses its own Asar (see `.devcontainer/Dockerfile`); shipping a
  second Windows binary would create two sources of truth.
- `Extras/*.bat`, `Extras/NESASMDis.asm`, and the Game Boy homebrew sample ROM.
  These are Game Boy or Windows-specific and out of scope for an SNES-only
  workstation.

## License note (GPL-3.0)

GPL-3.0 permits use of these files as a tool. It does not grant a right to
sublicense them under a different license, so:

- Vendored files stay under GPL-3.0 and keep their `LICENSE` beside them.
- They are **not** copied into, imported by, or linked against the Python code in
  `toolkit/snesworkbench/`. The Python toolkit and this vendored tree are
  independent.
- Anything generated *by* running these scripts (disassembly output) is ROM-derived
  working data and is git-ignored; see `.gitignore`.

This is a technical safeguard for repository hygiene, not legal advice.

## Known upstream quirks (verified locally)

- The scripts are driven by `print` output, so the disassembly is captured from
  stdout (`asar ... > bank.asm`), not written by the script itself.
- `!ROMOffset` is an **Asar/ROM address**, not a raw CPU address. Under the
  `lorom` mapping, disassembly of the bank containing ROM offset `N` starts at
  `!ROMOffset = $8000 + N`, not at `N`. `tools/bin/snes-disassemble` handles this.
- **A `.smc` target silently shifts every read.** Asar assumes a `.smc` has a
  512-byte copier header, so `read1($008000)` returns the byte at file offset
  `$008200` instead of `$008000`. The failure is silent: Asar exits 0 and emits
  plausible-looking but wrong mnemonics. Stage the ROM under its real suffix
  (`.sfc` for a headerless dump) before disassembling. This was observed directly:
  a `.smc` staging of this project's LoROM ROM decoded ROM offset `$000200`
  (`f6 a2 00 00 ...` -> `INC.b $A2,x` / `BRK`) instead of the true reset vector
  (`78 d8 18 fb ...` -> `SEI` / `CLD`).
- On start, A and X/Y default to 8-bit. That matches 65816 reset state, but a
  bank reached from a native-mode entry point will decode wrongly until the real
  entry state is supplied. Treat early bytes of a bank as provisional.
- Labels are emitted as `CODE_XXXXXX` with the label bank taken from `!Bank`.
  Cross-bank references are not resolved automatically, so this output is a
  review aid and is **not** a byte-exact rebuild source. See
  `tools/bin/snes-fidelity` for the path that produces a verified `MATCH`.