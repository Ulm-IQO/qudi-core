# -*- coding: utf-8 -*-
"""
This file contains the Qudi console app class.

Copyright (c) 2024, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-core/>

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
           'configure_pyqtgraph', 'prompt_shutdown', 'prompt_restart', 'pop_up_message']

import os
import platform
from PySide2 import QtGui, QtWidgets
from typing import Optional

from qudi.util.paths import get_artwork_dir


def set_theme(theme: Optional[str] = 'qudiTheme') -> None:
    """ Set icon theme for qudi app """
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
    """ Set qss style sheet for application """
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
    """ Close all application windows """
    QtWidgets.QApplication.instance().closeAllWindows()


def initialize_app_icon(icon: Optional[QtGui.QIcon] = None) -> None:
    """ Set up the Qudi application icon """
    if icon is None:
        icon = QtGui.QIcon(os.path.join(get_artwork_dir(), 'logo', 'logo-qudi.svg'))
    QtWidgets.QApplication.instance().setWindowIcon(icon)


def configure_pyqtgraph(use_opengl: Optional[bool] = False) -> None:
    """ Configure pyqtgraph (if present) """
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


def pop_up_message(title: str,
                   message: str,
                   parent: Optional[QtWidgets.QMainWindow] = None) -> None:
    """ Slot prompting a dialog window with a message and an OK button to dismiss it.

    @param str title: The window title of the dialog
    @param str message: The message to be shown in the dialog window
    @param QMainWindow parent: The parent main window to make this pop-up modal to
    """
    QtWidgets.QMessageBox.information(parent, title, message, QtWidgets.QMessageBox.Ok)


def prompt_shutdown(modules_locked: Optional[bool] = False,
                    parent: Optional[QtWidgets.QMainWindow] = None) -> bool:
    """ Display a dialog, asking the user to confirm shutdown """
    if modules_locked:
        msg = 'Some qudi modules are locked right now.\n' \
              'Do you really want to quit and force modules to deactivate?'
    else:
        msg = 'Do you really want to quit?'
    result = QtWidgets.QMessageBox.question(parent,
                                            'Qudi: Quit?',
                                            msg,
                                            QtWidgets.QMessageBox.Yes,
                                            QtWidgets.QMessageBox.No)
    return result == QtWidgets.QMessageBox.Yes


def prompt_restart(modules_locked: Optional[bool] = False,
                   parent: Optional[QtWidgets.QMainWindow] = None) -> bool:
    """ Display a dialog, asking the user to confirm restart """
    if modules_locked:
        msg = 'Some qudi modules are locked right now.\n' \
              'Do you really want to restart and force modules to deactivate?'
    else:
        msg = 'Do you really want to restart?'
    result = QtWidgets.QMessageBox.question(parent,
                                            'Qudi: Restart?',
                                            msg,
                                            QtWidgets.QMessageBox.Yes,
                                            QtWidgets.QMessageBox.No)
    return result == QtWidgets.QMessageBox.Yes
