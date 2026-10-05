PROJECT ?=
ROM ?= $(if $(PROJECT),roms/$(PROJECT)/original.sfc,)
OUTPUT ?= $(if $(PROJECT),build/$(PROJECT)/translated.sfc,)

.PHONY: self-test projects validate test test-toolkit test-project analysis translated audit clean info run debug gui
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
	python3 tools/bin/snes-workstation analyze $(PROJECT)
translated:
	python3 tools/bin/snes-workstation build $(PROJECT) --rom $(ROM) --output $(OUTPUT)
audit:
	python3 tools/bin/snes-repo-audit
clean:
	rm -rf build
info:
	python3 tools/bin/snes-workstation info $(PROJECT)
run:
	snes-run $(OUTPUT)
debug:
	snes-debug $(OUTPUT)
gui:
	start-snes-desktop
