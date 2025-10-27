# qudi-core Architecture: Dependency Management

## Core Principle: Flake is the Source of Truth

This project uses **Nix flakes** as the **single source of truth** for all dependencies, tools, and build configuration.

## File Roles

### flake.nix - The ONLY Source of Truth

**Purpose**: Defines ALL dependencies, build configuration, checks, and development environments.

**What's in it**:
- ✅ ALL Python dependencies with exact versions (via flake.lock)
- ✅ All development tools (ruff, mypy, pytest, etc.)
- ✅ Build configuration for qudi-core package
- ✅ Entry points (console scripts)
- ✅ All CI checks
- ✅ Multi-platform support

**Key point**: When you run `nix develop`, `nix build`, or `nix run`, **ONLY flake.nix is used**.

### pyproject.toml - Tool Configuration ONLY

**Purpose**: Configuration for development tools (ruff, pytest, mypy, coverage).

**What's in it**:
- ✅ Ruff linting rules
- ✅ Pytest configuration
- ✅ Mypy type checking settings
- ✅ Coverage report settings

**What's NOT in it (for Nix users)**:
- ❌ NO dependency resolution
- ❌ NO version pinning
- ❌ NO build configuration used by Nix

**Note**: The `[project.dependencies]` section exists for non-Nix users but is **ignored by Nix**. If you modify dependencies in flake.nix, you must manually sync pyproject.toml if you want pip/uv users to have the same dependencies.

### Why This Architecture?

#### 1. Reproducibility
```bash
# Two developers, two machines, 6 months apart
nix develop  # Identical environment every time
```

flake.lock pins every dependency transitively. No "works on my machine" issues.

#### 2. CI/Local Parity
```bash
# Locally
just ci  # → nix flake check

# GitHub Actions
nix flake check  # Exact same command
```

#### 3. Multi-Platform Support
```nix
pkgs = import nixpkgs {
  inherit system;  # x86_64-linux, aarch64-linux, darwin, etc.
  config.allowBroken = true;
};
```

One flake.nix works on Linux, macOS (Intel & Apple Silicon).

#### 4. No Dependency Hell
All dependencies are isolated in `/nix/store`. No conflicts with system Python or other projects.

## Dependency Management Workflow

### Adding a New Python Dependency

1. **Edit flake.nix** (THE ONLY PLACE):
   ```nix
   pythonDeps = with pythonPackages; [
     # ... existing deps ...
     new-package  # Add here
   ];
   ```

2. **Update the lock file**:
   ```bash
   nix flake update
   ```

3. **Optional**: If supporting pip users, manually add to `pyproject.toml`:
   ```toml
   [project]
   dependencies = [
       # ... existing ...
       "new-package>=1.0.0",
   ]
   ```

4. **Test**:
   ```bash
   just test
   just ci
   ```

### Updating Dependencies

```bash
# Update all inputs (nixpkgs, etc.)
just update  # → nix flake update

# Update specific input
just update-input nixpkgs

# See what changed
git diff flake.lock
```

### Checking Dependency Versions

```bash
# Enter shell and check
nix develop --command python3 -c "import package; print(package.__version__)"

# Or
just info  # Shows key package versions
```

## Package Building

The qudi-core package is built **entirely from flake.nix**:

```nix
qudi-core-pkg = pythonPackages.buildPythonPackage rec {
  pname = "qudi-core";
  version = builtins.readFile ./VERSION;

  # All dependencies from pythonDeps (defined in flake.nix)
  propagatedBuildInputs = pythonDeps;

  # Dynamic setup.py generation (no pyproject.toml)
  preBuild = ''
    cat > setup.py << 'EOF'
    import setuptools
    setuptools.setup(
        name="${pname}",
        version="${version}",
        packages=setuptools.find_packages(where="src"),
        package_dir={"": "src"},
        entry_points={...},
    )
    EOF
  '';
};
```

**No pyproject.toml dependencies are read.**

## Tool Configuration (pyproject.toml)

Tools like ruff, pytest, mypy read their config from pyproject.toml:

```bash
# These commands read pyproject.toml for CONFIGURATION only
ruff check .        # Uses [tool.ruff] settings
pytest              # Uses [tool.pytest.ini_options]
mypy src/           # Uses [tool.mypy]
coverage report     # Uses [tool.coverage.run]
```

But the **tools themselves** come from flake.nix!

## For Non-Nix Users

If someone wants to use qudi-core **without Nix**:

```bash
# They would use pyproject.toml
pip install -e .
# or
uv pip install -e .
```

In this case, pyproject.toml's `[project.dependencies]` is used. **You must manually keep it in sync with flake.nix.**

## Comparison

| Aspect | Traditional Python | This Project (Nix) |
|--------|-------------------|-------------------|
| Dependency source | pyproject.toml | flake.nix |
| Version pinning | requirements.txt / poetry.lock | flake.lock |
| Tool versions | System / virtualenv | Nix store |
| Reproducibility | "Works on my machine" | Bit-for-bit identical |
| Multi-platform | Manual testing | Built into flake |
| CI/local parity | Often diverge | Guaranteed identical |

## Summary

```
┌─────────────────────────────────────┐
│         flake.nix                   │
│  (SINGLE SOURCE OF TRUTH)           │
│                                     │
│  • Python 3.13.7                    │
│  • NumPy 2.x                        │
│  • All 30+ dependencies             │
│  • Development tools                │
│  • Build configuration              │
│  • Entry points                     │
│  • CI checks                        │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│       flake.lock                    │
│  (Transitive dependency pins)       │
│  • SHA256 hashes                    │
│  • Exact commits                    │
│  • Complete closure                 │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│    /nix/store/*                     │
│  (Immutable packages)               │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│      pyproject.toml                 │
│  (Tool config only)                 │
│                                     │
│  • [tool.ruff] ← ruff reads this    │
│  • [tool.pytest] ← pytest reads     │
│  • [tool.mypy] ← mypy reads         │
│                                     │
│  [project.dependencies]             │
│  ← IGNORED by Nix                   │
│  ← Only for pip/uv users            │
└─────────────────────────────────────┘
```

**Remember**: When using Nix, dependencies flow from **flake.nix → flake.lock → /nix/store**, and pyproject.toml is consulted **only for tool configuration**, never for dependencies.
