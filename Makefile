PROJECT ?=
ROM ?= $(if $(PROJECT),projects/$(PROJECT)/rom/original.sfc,)
OUTPUT ?= $(if $(PROJECT),build/$(PROJECT)/translated.sfc,)
DISASSEMBLY ?= disassembly
BANK ?=
BANKFLAG = $(if $(strip $(BANK)),--bank $(strip $(BANK)),)

.PHONY: self-test projects validate test test-toolkit test-project analysis translated audit clean info run debug gui disassemble rebuild verify build
self-test:
	tools/bin/snes-self-test
projects:
	python3 tools/bin/snes-workstation list
validate:
	@test -n "$(PROJECT)" || (echo 'Set PROJECT=<project-id>' >&2; exit 2)
	python3 tools/bin/snes-workstation validate $(PROJECT)
test: test-toolkit
	@if [ -n "$(PROJECT)" ]; then $(MAKE) test-project PROJECT=$(PROJECT); fi
test-toolkit:
	PYTHONPATH=toolkit python3 -m unittest discover -s tests/toolkit -v
test-project:
	python3 tools/bin/snes-workstation test $(PROJECT)
analysis:
	@test -n "$(PROJECT)" || (echo 'Set PROJECT=<project-id>' >&2; exit 2)
	python3 tools/bin/snes-workstation analyze $(PROJECT)
translated:
	@test -n "$(PROJECT)" || (echo 'Set PROJECT=<project-id>' >&2; exit 2)
	python3 tools/bin/snes-workstation build $(PROJECT) --rom $(ROM) --output $(OUTPUT)
audit:
	python3 tools/bin/snes-repo-audit
clean:
	rm -rf build $(DISASSEMBLY)
info:
	python3 tools/bin/snes-workstation info $(PROJECT)
run:
	snes-run $(OUTPUT)
debug:
	snes-debug $(OUTPUT)
gui:
	start-snes-desktop

# --- Disassembly and byte-identical rebuild --------------------------------
# The ROM is a user-supplied input. Disassembly output is ROM-derived, is
# git-ignored, and is regenerated on demand rather than committed.

# Readable 65816/SPC700/SuperFX disassembly for review. Pass BANK=<n> for a
# single bank. This output is a review aid, NOT a byte-exact rebuild source.
disassemble:
	@test -f "$(ROM)" || { echo 'ROM not found: $(ROM) -- set PROJECT=<project-id>' >&2; exit 1; }
	tools/bin/snes-disassemble "$(ROM)" --outdir "$(DISASSEMBLY)" $(BANKFLAG)
# Write the byte-faithful Asar sources and retain them for inspection.
rebuild:
	@test -f "$(ROM)" || { echo 'ROM not found: $(ROM) -- set PROJECT=<project-id>' >&2; exit 1; }
	tools/bin/snes-fidelity "$(ROM)" --keep --workdir build/fidelity
# The core safety invariant: rebuilding must reproduce the original ROM exactly.
# snes-fidelity round-trips the ROM through Asar and prints MATCH or MISMATCH,
# exiting nonzero on any difference.
verify:
	@test -f "$(ROM)" || { echo 'ROM not found: $(ROM) -- set PROJECT=<project-id>' >&2; exit 1; }
	tools/bin/snes-fidelity "$(ROM)"
# Never translate on top of a ROM that no longer rebuilds byte-for-byte.
build: verify translated
