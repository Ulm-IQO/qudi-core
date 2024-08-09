# Minimal makefile for Sphinx documentation
#

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

.PHONY: help Makefile clean autobuild

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXAUTOBUILD) "$(SOURCEDIR)" "$(BUILDDIR)" --watch "$(SOURCEDIR)" --open-browser


clean:
	@echo "Cleaning up build directories..."
	rm -rf $(BUILDDIR) _autosummary

