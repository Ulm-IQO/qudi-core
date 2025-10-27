#!/usr/bin/env -S just --justfile
# qudi-core development workflow - All commands use Nix for reproducibility
# This justfile is a thin convenience layer over flake.nix

set shell := ["bash", "-euo", "pipefail", "-c"]

# Show all available commands
_default:
    @just --list --unsorted

# CI/CD Commands (same as CI runs)

# Run ALL checks (same as CI) - This is the source of truth
ci:
    @just clean-all-notebooks
    nix flake check

# Run quick format and lint checks (fast feedback)
check:
    nix run .#check-fast

# Development Commands (via nix develop)

# Run Python tests with coverage
test *ARGS:
    nix develop --command pytest tests/ -v {{ ARGS }}

# Run tests with coverage report
test-cov:
    nix develop --command pytest tests/ -v --cov=src/qudi --cov-report=html --cov-report=term-missing

# Watch and re-run tests on file changes
test-watch:
    nix develop --command watchexec -e py -c pytest tests/ -v

# Format all code (Python + Nix)
fmt:
    nix develop --command ruff format .
    nix develop --command alejandra .

# Lint Python code
lint:
    nix develop --command ruff check .

# Fix auto-fixable linting issues
fix:
    nix develop --command ruff check --fix .

# Run type checking with mypy
typecheck:
    nix develop --command mypy src/qudi --ignore-missing-imports

# Run all individual checks one by one (for debugging)
check-all: check-fmt check-lint check-nixfmt check-types

# Check formatting without fixing
check-fmt:
    nix develop --command ruff format --check .

# Check linting
check-lint:
    nix develop --command ruff check .

# Check Nix formatting
check-nixfmt:
    nix develop --command alejandra --check .

# Check types
check-types:
    nix develop --command mypy src/qudi --ignore-missing-imports || true

# Running qudi-core (via nix run)

# Run qudi-core application
run *ARGS:
    nix run . -- {{ ARGS }}

# Run qudi configuration editor
config-editor:
    nix run .#config-editor

# Install qudi Jupyter kernel
install-kernel:
    nix run .#install-kernel

# Uninstall qudi Jupyter kernel
uninstall-kernel:
    nix run .#uninstall-kernel

# Maintenance Commands

# Build all packages
build:
    nix build

# Build qudi-core package
build-pkg:
    nix build .#qudi-core

# Build specific check
build-check CHECK:
    nix build .#checks.x86_64-linux.{{ CHECK }}

# Pre-commit Hooks

# Install pre-commit hooks (automatically done in nix develop)
pre-commit-install:
    nix develop --command pre-commit install

# Run pre-commit hooks manually on all files
pre-commit-run:
    nix develop --command pre-commit run --all-files

# Troubleshooting

# Verify all dependencies are available
doctor:
    @nix develop --command python3 -c "import qudi; print('✓ qudi module imports')"
    @nix develop --command python3 -c "import qudi.core; print('✓ qudi.core imports')"
    @nix develop --command python3 -c "import qudi.util; print('✓ qudi.util imports')"

# Jupyter/Notebook Utilities

# Clear all metadata from a Jupyter notebook
clean-notebook path:
    nix develop --command jupyter nbconvert --clear-output --ClearMetadataPreprocessor.enabled=True --ClearMetadataPreprocessor.clear_cell_metadata=True --inplace "{{ path }}"

# Clear all metadata from all Jupyter notebooks in the repository
clean-all-notebooks:
    #!/usr/bin/env bash
    set -euo pipefail
    find . -name "*.ipynb" -not -path "./.direnv/*" -not -path "./result*" -type f | while read -r nb; do
        nix develop --command jupyter nbconvert --clear-output --ClearMetadataPreprocessor.enabled=True --ClearMetadataPreprocessor.clear_cell_metadata=True --inplace "$nb"
    done

# Package Management

# Install qudi-core package in development mode
install-dev:
    nix develop --command pip install -e .

# Build distribution packages (wheel and sdist)
dist:
    nix develop --command python3 -m build

# Publish to PyPI (requires credentials)
publish:
    nix develop --command python3 -m twine upload dist/*
