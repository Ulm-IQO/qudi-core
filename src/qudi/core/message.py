# -*- coding: utf-8 -*-
"""
This file contains functions to send messages to qudi users.

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

__all__ = ['popup_message', 'balloon_message', 'prompt_shutdown', 'prompt_restart']

from PySide2 import QtWidgets, QtGui
from typing import Optional

from qudi.core.logger import get_logger
from qudi.core.trayicon import QudiTrayIcon


def popup_message(title: str,
                  message: str,
                  parent: Optional[QtWidgets.QMainWindow] = None) -> None:
    """ Helper function prompting a dialog window with a message and an OK button to dismiss it.

    @param str title: The window title of the dialog
    @param str message: The message to be shown in the dialog window
    @param QMainWindow parent: The parent main window to make this pop-up modal to
    """
    if QtWidgets.QApplication.instance() is None:
        get_logger('popup-message').info(f'{title}:\n{message}')
    else:
        QtWidgets.QMessageBox.information(parent, title, message, QtWidgets.QMessageBox.Ok)


def balloon_message(title: str,
                    message: str,
                    time: Optional[float] = None,
                    icon: Optional[QtGui.QIcon] = None) -> None:
    """ Helper method to invoke balloon messages in the system tray by calling
    QSystemTrayIcon.showMessage().

    @param str title: The notification title of the balloon
    @param str message: The message to be shown in the balloon
    @param float time: optional, The lingering time of the balloon in seconds
    @param QIcon icon: optional, an icon to be used in the balloon. "None" will use OS default.
    """
    tray = QudiTrayIcon.instance()
    if (tray is not None) and tray.supportsMessages():
        if icon is None:
            icon = QtGui.QIcon()
        if time is None:
            time = 10
        tray.showMessage(title, message, icon, int(round(time * 1000)))
    else:
        get_logger('balloon-message').info(f'{title}:\n{message}')


def prompt_shutdown(modules_locked: Optional[bool] = False,
                    parent: Optional[QtWidgets.QMainWindow] = None) -> bool:
    """ Display a dialog, asking the user to confirm shutdown """
    if modules_locked:
        msg = 'Some qudi modules are locked right now.\n' \
              'Do you really want to quit and force modules to deactivate?'
    else:
        msg = 'Do you really want to quit?'

    if QtWidgets.QApplication.instance() is None:
        msg += ' (y/N)'
        result = input(msg).strip().lower() in ('y', 'yes')
    else:
        result = QtWidgets.QMessageBox.Yes == QtWidgets.QMessageBox.question(
            parent,
            'Qudi: Quit?',
            msg,
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.No
        )
    return result


def prompt_restart(modules_locked: Optional[bool] = False,
                   parent: Optional[QtWidgets.QMainWindow] = None) -> bool:
    """ Display a dialog, asking the user to confirm restart """
    if modules_locked:
        msg = 'Some qudi modules are locked right now.\n' \
              'Do you really want to restart and force modules to deactivate?'
    else:
        msg = 'Do you really want to restart?'

    if QtWidgets.QApplication.instance() is None:
        msg += ' (y/N)'
        result = input(msg).strip().lower() in ('y', 'yes')
    else:
        result = QtWidgets.QMessageBox.Yes == QtWidgets.QMessageBox.question(
            parent,
            'Qudi: Restart?',
            msg,
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.No
        )
    return result
