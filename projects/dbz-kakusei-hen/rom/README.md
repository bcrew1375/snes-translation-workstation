# ROM input

This directory holds the user-supplied original ROM for this project. It is a
reference input and is never tracked by git.

Place a legally obtained dump at:

```text
projects/dbz-kakusei-hen/rom/original.sfc
```

Verify it matches the identity recorded in `project.toml` before doing any work:

```sh
make verify PROJECT=dbz-kakusei-hen     # prints MATCH
snes-rom-info projects/dbz-kakusei-hen/rom/original.sfc
```

Never modify, overwrite, or generate output into this file. Translated ROMs are
written to `build/dbz-kakusei-hen/translated.sfc`.

This ROM is 2 MiB, LoROM (slow), with no expansion chip. Record the expected
SHA-256 in `project.toml`; the build refuses an input that does not match.