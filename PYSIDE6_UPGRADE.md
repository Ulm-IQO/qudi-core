# PySide6 Upgrade for Python 3.13 Compatibility

## Issue

PySide2 (Qt5 bindings) does not compile on Python 3.13 due to:
- `shiboken2` build failures with newer Python C API
- Deprecated libxml2 functions
- Compiler errors with modern GCC/Clang

## Solution

**Upgraded from PySide2 to PySide6** (Qt6 bindings).

## Changes Made

### flake.nix
```nix
# BEFORE (broken on Python 3.13):
pyside2

# AFTER (works on Python 3.13):
pyside6
```

Also upgraded Qt libraries from Qt5 to Qt6:
```nix
# Qt6 platform plugins
pkgs.qt6.qtbase
pkgs.qt6.qtsvg
```

### pyproject.toml
```toml
# BEFORE:
"PySide2==5.15.2.1",

# AFTER:
"PySide6>=6.0.0",  # UPGRADED for Python 3.13 compatibility
```

## API Changes

### Import Changes

```python
# OLD (PySide2):
from PySide2.QtCore import Qt, QObject
from PySide2.QtWidgets import QWidget
from PySide2.QtGui import QIcon

# NEW (PySide6):
from PySide6.QtCore import Qt, QObject
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QIcon
```

### QtPy Compatibility

qudi-core uses `qtpy` as an abstraction layer, which supports both PySide2 and PySide6:

```python
# This works with both:
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget
```

Set the backend:
```bash
export QT_API=pyside6  # Use PySide6
export QT_API=pyside2  # Use PySide2 (won't work on Python 3.13)
```

With the Nix environment, `QT_API` is automatically set based on available Qt bindings.

## Major API Changes in Qt6

### 1. Removed Qt.MidButton
```python
# OLD:
if event.button() == Qt.MidButton:

# NEW:
if event.button() == Qt.MiddleButton:
```

### 2. exec() renamed to exec()
```python
# Both work, but exec_() is deprecated:
app.exec_()  # Still works but deprecated
app.exec()   # Preferred in Qt6
```

### 3. Removed QDesktopWidget
```python
# OLD:
from PySide2.QtWidgets import QDesktopWidget
screen = QDesktopWidget().screenGeometry()

# NEW:
from PySide6.QtGui import QGuiApplication
screen = QGuiApplication.primaryScreen().geometry()
```

### 4. Signal/Slot connections unchanged
```python
# This still works the same:
self.button.clicked.connect(self.on_clicked)
```

## Testing

### Manual Test

```bash
nix develop --command python3 -c "from PySide6 import QtCore; print(f'Qt: {QtCore.qVersion()}')"
```

Expected output:
```
Qt: 6.10.0 (or similar)
```

### Smoke Test

The flake includes a smoke test:
```bash
nix build .#checks.x86_64-linux.qudi-smoke
```

Tests:
- qudi.core imports
- qudi.util imports
- PySide6.QtCore imports

### Full Test Suite

```bash
just test
```

## Backwards Compatibility

### For Users on Python <3.13

If you need Python 3.8-3.12 with PySide2, pin to an earlier version:
```bash
git checkout <commit-before-pyside6-upgrade>
```

### For GUI Code

Most qudi-core code uses `qtpy`, so changes should be minimal. Direct PySide2 imports need updating:

```python
# FIND:
from PySide2

# REPLACE:
from PySide6
```

## Benefits of Qt6

1. **Python 3.13 support** ✅
2. **Better performance** - Qt6 has numerous optimizations
3. **Modern features** - Updated graphics, better HiDPI support
4. **Long-term support** - Qt6 is actively maintained
5. **Wayland support** - Native Wayland compositor support

## Environment Variables

The Nix devShell sets:
```bash
export QT_QPA_PLATFORM=xcb
export QT_QPA_PLATFORM_PLUGIN_PATH="<qt6-path>/lib/qt-6/plugins"
export QT_PLUGIN_PATH="<qt6-path>/lib/qt-6/plugins"
export QT_XCB_GL_INTEGRATION=none
```

## Known Issues

1. **First-time download**: PySide6 is ~500MB, takes time on first `nix develop`
2. **QtWebEngine**: Not included by default (large dependency)
3. **API changes**: Some code may need updates (see above)

## Migration Checklist

For qudi-core developers:

- [x] flake.nix updated to pyside6
- [x] pyproject.toml updated to PySide6>=6.0.0
- [x] Qt6 libraries added to devShell
- [x] Smoke test updated to test PySide6
- [ ] Review all `from PySide2` imports in codebase
- [ ] Test GUI functionality
- [ ] Update any Qt5-specific code
- [ ] Document breaking changes for users

## References

- [Qt6 Porting Guide](https://doc.qt.io/qt-6/portingguide.html)
- [PySide6 Documentation](https://doc.qt.io/qtforpython-6/)
- [qtpy Documentation](https://github.com/spyder-ide/qtpy)
- [Nix PySide6 Package](https://search.nixos.org/packages?query=pyside6)

## Summary

**qudi-core now uses PySide6 (Qt6) instead of PySide2 (Qt5) for full Python 3.13 compatibility.**

This is a necessary upgrade - PySide2 is unmaintained and incompatible with Python 3.13.
