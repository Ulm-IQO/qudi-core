# qudi-core Development Guide

This document describes the modern development tooling setup for qudi-core with Python 3.13 support.

## Philosophy: Everything Through Nix

This project follows a **"everything from the flake, conveniences in justfile"** architecture:

- **flake.nix** is the single source of truth for ALL tools, dependencies, and checks
- **pyproject.toml** is ONLY for tool configuration (ruff, pytest, mypy, coverage)
  - Dependencies are NOT read from pyproject.toml when using Nix
  - All dependencies are defined in flake.nix for reproducibility
- **justfile** provides convenient shortcuts that call into Nix
- **CI and local development** run the exact same commands (`nix flake check`)
- **Reproducibility** across machines, platforms, and time
- **Python 3.13** as the target version with full NumPy 2.x support

## Prerequisites

- **Nix** with flakes enabled ([Installation Guide](https://nixos.org/download.html))
- **direnv** (optional but highly recommended)
- All other tools (just, ruff, alejandra, etc.) are provided by the flake

### Enable Nix Flakes

Add to `~/.config/nix/nix.conf` or `/etc/nix/nix.conf`:
```
experimental-features = nix-command flakes
```

## Quick Start

### Option 1: Using Nix + direnv (Recommended)

1. Install direnv for your shell ([direnv setup](https://direnv.net/docs/hook.html))

2. Enable direnv for the project:
   ```bash
   direnv allow
   ```

3. The development environment will automatically load when you `cd` into the project directory.

4. View available commands:
   ```bash
   just
   ```

### Option 2: Using Nix Directly

1. Enter the development shell:
   ```bash
   nix develop
   ```

2. View available commands:
   ```bash
   just
   ```

### Option 3: Run Commands Without Entering Shell

You can run any command through Nix without entering the shell:
```bash
nix develop --command just test
nix develop --command pytest tests/
```

## Available Commands

The project uses `just` as a task runner. All commands are thin wrappers around Nix:

### Essential Commands

```bash
just                    # Show all commands
just ci                 # Run ALL checks (same as CI) ⭐
just check              # Run quick checks (format, lint)
just test               # Run tests
just fmt                # Format all code (Python + Nix)
just lint               # Lint Python code
just fix                # Auto-fix linting issues
just run                # Run qudi-core
just config-editor      # Run qudi configuration editor
```

### CI/CD Commands

```bash
just ci                 # Full CI checks (nix flake check) - SOURCE OF TRUTH
just check              # Quick checks (fast feedback)
just check-all          # Run all checks individually (debugging)
```

### Development Commands

```bash
just test               # Run tests
just test-cov           # Run tests with coverage report
just test-watch         # Watch files and re-run tests
just typecheck          # Run mypy type checking
just fmt                # Format Python + Nix code
just lint               # Check Python linting
just fix                # Auto-fix linting issues
```

### Running qudi-core

```bash
just run [ARGS]         # Run qudi-core
just config-editor      # Run configuration editor
just install-kernel     # Install Jupyter kernel
just uninstall-kernel   # Uninstall Jupyter kernel
```

### Development Shells

```bash
just dev                # Enter full dev shell
just dev-ci             # Enter minimal CI shell
just dev-headless       # Enter headless shell (no Qt)
```

### Information & Diagnostics

```bash
just info               # Show environment info
just doctor             # Verify dependencies
just outputs            # Show Nix flake outputs
just show               # Show flake metadata
```

### Package Management

```bash
just build              # Build qudi-core package
just build-pkg          # Build qudi-core package (explicit)
just install-dev        # Install in development mode
just dist               # Build distribution packages
```

### Maintenance

```bash
just update             # Update flake inputs
just clean              # Clean build artifacts
just clean-all          # Deep clean + Nix garbage collection
```

## Development Workflow

### Standard Workflow

1. **Make changes** to code

2. **Format code:**
   ```bash
   just fmt
   ```

3. **Run tests:**
   ```bash
   just test
   ```

4. **Run all checks (same as CI):**
   ```bash
   just ci
   ```

5. **Commit and push**

### Quick Iteration

For fast feedback during development:

```bash
# Terminal 1: Watch and re-run tests
just test-watch

# Terminal 2: Make changes
# Tests automatically re-run on file save
```

### Pre-commit Hooks

Pre-commit hooks are automatically configured when you enter the Nix shell. They run:
- Ruff formatting
- Ruff linting
- Alejandra (Nix formatting)

The hooks are managed by Nix and guaranteed to be consistent across all developers.

## GitHub Actions CI

The CI pipeline is configured in `.github/workflows/ci.yml`:

### Pipeline Jobs

1. **quick-checks**: Fast format/lint checks for immediate feedback
2. **full-checks**: Runs `nix flake check` (all checks in parallel)
3. **build**: Builds the qudi-core package and smoke-tests imports

### CI/Local Parity

The CI runs **exactly the same command** as you run locally:
```bash
nix flake check
```

This ensures perfect parity between CI and local development.

## Project Structure

```
qudi-core/
├── .github/workflows/   # GitHub Actions CI/CD
├── src/qudi/           # Source code
│   ├── core/           # Core framework
│   ├── util/           # Utilities
│   ├── tools/          # Tools (config editor, etc.)
│   └── runnable.py     # Main entry point
├── tests/              # Test suite
├── docs/               # Documentation
├── justfile            # Task runner commands
├── flake.nix           # Nix development environment
├── pyproject.toml      # Python project metadata
├── .envrc              # direnv configuration
└── VERSION             # Version file
```

## Architecture: Nix Flake Structure

### Flake Outputs

The `flake.nix` provides:

- **packages**: Python environment and qudi-core package
- **apps**: Direct runners (qudi, config-editor, install-kernel, uninstall-kernel, check-fast)
- **devShells**: Development environments (default, ci, headless)
- **checks**: All CI checks (pytest, ruff-lint, ruff-format, mypy, nixfmt, pre-commit, qudi-smoke, build)
- **formatter**: Alejandra for Nix code

### Flake Checks

All checks run via `nix flake check`:

| Check | Description |
|-------|-------------|
| `pytest` | Run tests with coverage |
| `ruff-lint` | Python linting |
| `ruff-format` | Python formatting check |
| `mypy` | Type checking |
| `nixfmt` | Nix formatting check |
| `pre-commit` | Pre-commit hooks |
| `qudi-smoke` | Basic qudi import test (Linux only) |
| `build` | Package build verification |

### Multi-Platform Support

The flake supports:
- `x86_64-linux`
- `aarch64-linux`
- `x86_64-darwin` (macOS Intel)
- `aarch64-darwin` (macOS Apple Silicon)

Qt dependencies (PySide2) are Linux-only for now.

## Python Environment

### Dependencies (All via Nix)

- Python 3.13.7
- NumPy 2.x (latest)
- SciPy
- Matplotlib
- PySide2 (Linux only)
- QtPy
- Jupyter ecosystem
- lmfit, pyqtgraph
- fysom (custom build)
- Development tools: ruff, mypy, pytest, coverage

Everything is pinned and reproducible via `flake.lock`.

### Python 3.13 Compatibility

This project is upgraded to Python 3.13 with:
- NumPy 2.x support (no version cap)
- Updated type hints
- Modern Python features
- Ruff for linting and formatting (replaces black, isort, flake8)

## Running qudi-core

### Using just

```bash
just run                # Run qudi-core
just config-editor      # Configuration editor
```

### Using Nix apps

```bash
nix run                        # Run qudi-core
nix run .#config-editor        # Config editor
nix run .#install-kernel       # Install Jupyter kernel
```

### Direct Python

```bash
python3 -m qudi.runnable
python3 -m qudi.tools.config_editor.config_editor
```

## Code Quality Tools

### Ruff

Modern, fast Python linter and formatter (replaces black, isort, flake8, etc.):

```bash
ruff check .            # Check for issues
ruff check --fix .      # Fix automatically
ruff format .           # Format code
```

Configuration in `pyproject.toml` under `[tool.ruff]`.

### MyPy

Type checking:

```bash
just typecheck
# or
mypy src/qudi --ignore-missing-imports
```

## Troubleshooting

### Qt Display Issues

If you get Qt/X11 errors:

```bash
export QT_QPA_PLATFORM=xcb
export QT_XCB_GL_INTEGRATION=none
```

These are set automatically in the Nix shell.

### Import Errors

Make sure you're in the Nix development shell:

```bash
nix develop
```

Or using direnv:

```bash
direnv allow
```

### Missing Dependencies

Check which packages are installed:

```bash
nix develop --command pip list
```

## Contributing

1. Create a feature branch
2. Make changes
3. Run `just ci` to verify all checks pass
4. Commit (pre-commit hooks will run automatically)
5. Push and create a pull request

GitHub Actions will automatically run all checks on your PR.

## Resources

- [qudi-core Documentation](https://ulm-iqo.github.io/qudi-core/)
- [qudi-core Repository](https://github.com/Ulm-IQO/qudi-core)
- [Just Command Runner](https://github.com/casey/just)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Nix Flakes](https://nixos.wiki/wiki/Flakes)
- [direnv](https://direnv.net/)

## Differences from Original qudi-core

This fork includes:

- **Python 3.13 support** (upgraded from 3.8-3.10)
- **NumPy 2.x support** (removed version cap)
- **Nix flake** for reproducible development environment
- **Multi-platform support** (Linux, macOS)
- **Modern tooling** (ruff instead of multiple tools)
- **CI/local parity** via `nix flake check`
- **Pre-commit hooks** managed by Nix
- **Comprehensive checks** (tests, linting, formatting, types, build)
