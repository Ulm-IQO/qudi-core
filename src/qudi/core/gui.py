# -*- coding: utf-8 -*-
"""
Contains utility functions to configure the GUI environment of qudi.

Copyright (c) 2024, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-core/>.

This file is part of qudi.

Qudi is free software: you can redistribute it and/or modify it under the terms of
the GNU Lesser General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with qudi.
If not, see <https://www.gnu.org/licenses/>.
"""

__all__ = ['set_theme', 'set_stylesheet', 'close_windows', 'initialize_app_icon',
           'configure_pyqtgraph']

import os
import platform
from PySide2 import QtGui, QtWidgets
from typing import Optional

from qudi.util.paths import get_artwork_dir


def set_theme(theme: Optional[str] = 'qudiTheme') -> None:
    """
    Sets icon theme for qudi.

    Parameters
    ----------
    theme : str, optional
        Icons subdirectory name to use (defaults to "qudiTheme").
    """
    # Make icons work on non-X11 platforms, set custom theme
    # if not sys.platform.startswith('linux') and not sys.platform.startswith('freebsd'):
    #
    # To enable the use of custom action icons, for now the above if statement has been
    # removed and the QT theme is being set to our artwork/icons folder for
    # all OSs.
    themepaths = QtGui.QIcon.themeSearchPaths()
    themepaths.append(os.path.join(get_artwork_dir(), 'icons'))
    QtGui.QIcon.setThemeSearchPaths(themepaths)
    QtGui.QIcon.setThemeName(theme)


def set_stylesheet(stylesheet_path: Optional[str] = 'qdark.qss') -> None:
    """
    Sets qss stylesheet for qudi.

    Parameters
    ----------
    stylesheet_path : str, optional
        Full file path to Qt-compatible css stylesheet to use. If only a filename is given, search
        for it in the default stylesheet path (default is "qdark.qss").
    """
    if not os.path.exists(stylesheet_path):
        stylesheet_path = os.path.join(get_artwork_dir(), 'styles', stylesheet_path)

    with open(stylesheet_path, 'r') as stylesheetfile:
        stylesheet = stylesheetfile.read()

    if stylesheet_path.endswith('qdark.qss'):
        path = os.path.join(os.path.dirname(stylesheet_path), 'qdark').replace('\\', '/')
        stylesheet = stylesheet.replace('{qdark}', path)

    # see issue #12 on qdarkstyle github
    if platform.system().lower() == 'darwin' and stylesheet_path.endswith('qdark.qss'):
        mac_fix = '''
        QDockWidget::title
        {
            background-color: #31363b;
            text-align: center;
            height: 12px;
        }
        '''
        stylesheet += mac_fix
    QtWidgets.QApplication.instance().setStyleSheet(stylesheet)


def close_windows() -> None:
    """Closes all Qt application windows."""
    QtWidgets.QApplication.instance().closeAllWindows()


def initialize_app_icon(icon: Optional[QtGui.QIcon] = None) -> None:
    """
    Sets up the qudi app icon.

    Parameters
    ----------
    icon : QtGui.QIcon, optional
        This icon will be used as main application icon (default uses standard qudi icon).
    """
    if icon is None:
        icon = QtGui.QIcon(os.path.join(get_artwork_dir(), 'logo', 'logo-qudi.svg'))
    QtWidgets.QApplication.instance().setWindowIcon(icon)


def configure_pyqtgraph(use_opengl: Optional[bool] = False) -> None:
    """
    Adjust global pyqtgraph configuration if this package is installed.

    Parameters
    ----------
    use_opengl : bool, optional
        Whether to enable OpenGL support in pyqtgraph or not (defaults to `False`).
    """
    try:
        import pyqtgraph
    except ImportError:
        return
    # test setting background of pyqtgraph
    testwidget = QtWidgets.QWidget()
    testwidget.ensurePolished()
    bgcolor = testwidget.palette().color(QtGui.QPalette.Normal, testwidget.backgroundRole())
    # set manually the background color in hex code according to our color scheme:
    pyqtgraph.setConfigOption('background', bgcolor)
    # experimental opengl usage
    pyqtgraph.setConfigOption('useOpenGL', use_opengl)
    # Disable pyqtgraph "application exit workarounds" because they cause errors on exit
    pyqtgraph.setConfigOption('exitCleanup', False)
