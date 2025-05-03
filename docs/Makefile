# Minimal makefile for Sphinx documentation

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?= --jobs=auto
SPHINXBUILD   ?= sphinx-build
SPHINXAUTOBUILD ?= sphinx-autobuild
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile html clean autobuild

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXAUTOBUILD) "$(SOURCEDIR)" "$(BUILDDIR)" --watch "$(SOURCEDIR)" --open-browser

html:
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

clean:
	@echo "Cleaning build directory..."
ifeq ($(OS),Windows_NT)
	@if exist "$(BUILDDIR)" rmdir /S /Q "$(BUILDDIR)"
	@echo "Cleaning autosummary directories..."
	@if exist core\_autosummary rmdir /S /Q core\_autosummary
	@if exist gui\_autosummary rmdir /S /Q gui\_autosummary
	@if exist logic\_autosummary rmdir /S /Q logic\_autosummary
	@if exist tasks\_autosummary rmdir /S /Q tasks\_autosummary
	@if exist tools\_autosummary rmdir /S /Q tools\_autosummary
	@if exist util\_autosummary rmdir /S /Q util\_autosummary
else
	@rm -rf "$(BUILDDIR)"
	@echo "Cleaning autosummary directories..."
	@rm -rf core/_autosummary gui/_autosummary logic/_autosummary tasks/_autosummary tools/_autosummary util/_autosummary
endif

