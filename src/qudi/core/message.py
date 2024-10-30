# -*- coding: utf-8 -*-
"""
Contains functions to send messages prompts to qudi users.

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

__all__ = ['popup_message', 'balloon_message', 'prompt_shutdown', 'prompt_restart']

from PySide2 import QtWidgets, QtGui
from typing import Optional

from qudi.core.logger import get_logger
from qudi.core.trayicon import QudiTrayIcon


def popup_message(title: str,
                  message: str,
                  parent: Optional[QtWidgets.QWidget] = None) -> None:
    """
    Helper function prompting a dialog window with a message and an OK button to dismiss it.
    If qudi runs headless, send message to logger instead.

    Parameters
    ----------
    title : str
        Title of the popup message.
    message : str
        Popup message text body.
    parent : QtWidgets.QWidget, optional
        Parent QtWidgets.QWidget instance for modal dialog (defaults to `None`).
    """
    if QtWidgets.QApplication.instance() is None:
        get_logger('popup-message').info(f'{title}:\n{message}')
    else:
        QtWidgets.QMessageBox.information(parent, title, message, QtWidgets.QMessageBox.Ok)


def balloon_message(title: str,
                    message: str,
                    time: Optional[float] = 10.,
                    icon: Optional[QtGui.QIcon] = None) -> None:
    """
    Helper function to invoke balloon messages in the system tray.
    If no tray icon has been initialized or the system does not support it, send message to logger
    instead.

    Parameters
    ----------
    title : str
        Title of the balloon message.
    message : str
        Balloon message text body.
    time : float, optional
        Lingering time in seconds for the balloon message (defaults to 10 seconds).
    icon : QtGui.QIcon, optional
        This icon will be used in the balloon message if supported (defaults to OS default).
    """
    tray = QudiTrayIcon.instance()
    if (tray is not None) and tray.supportsMessages():
        if icon is None:
            icon = QtGui.QIcon()
        tray.showMessage(title, message, icon, int(round(time * 1000)))
    else:
        get_logger('balloon-message').info(f'{title}:\n{message}')


def prompt_shutdown(modules_locked: Optional[bool] = False,
                    parent: Optional[QtWidgets.QWidget] = None) -> bool:
    """
    Display a dialog asking the user to confirm shutdown.

    Parameters
    ----------
    modules_locked : bool, optional
        If `True` some modules may be terminated in an unsafe way and the user is informed
        (defaults to `False`).
    parent : QtWidgets.QWidget, optional
        Parent QtWidgets.QWidget instance for modal dialog (defaults to `None`).

    Returns
    -------
    bool
        Flag indicating if the user accepts the shutdown (`True`) or not (`False`).
    """
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
                   parent: Optional[QtWidgets.QWidget] = None) -> bool:
    """
    Display a dialog asking the user to confirm restart.

    Parameters
    ----------
    modules_locked : bool, optional
        If `True` some modules may be terminated in an unsafe way and the user is informed
        (defaults to `False`).
    parent : QtWidgets.QWidget, optional
        Parent QtWidgets.QWidget instance for modal dialog (defaults to `None`).

    Returns
    -------
    bool
        Flag indicating if the user accepts the restart (`True`) or not (`False`).
    """
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
