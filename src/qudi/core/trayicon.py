# -*- coding: utf-8 -*-
"""
Contains the qudi application tray icon.

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

__all__ = ['QudiTrayIcon']

import os
import weakref
from PySide2 import QtCore, QtWidgets, QtGui
from typing import Optional, Callable, Union, Dict

from qudi.util.paths import get_artwork_dir
from qudi.util.mutex import Mutex


class QudiTrayIcon(QtWidgets.QSystemTrayIcon):
    """
    QtWidgets.QSystemTrayIcon singleton for the qudi application.
    The singleton instance can be obtained during runtime via call to `QudiTrayIcon.instance()`.

    Parameters
    ----------
    quit_callback : function
        Callback function to call if the user shuts down qudi from the system tray.
    restart_callback : function
        Callback function to call if the user restarts qudi from the system tray.
    main_gui_callback : function, optional
        Callback function to call if the user activates the main GUI from the system tray (defaults
        to `None`).
    parent : QtCore.QObject, optional
        Parent QtCore.QObject instance (defaults to `None`).
    """

    _instance: Union[None, weakref.ref] = None  # Only instance will be stored here as weakref
    _lock = Mutex()
    _module_actions: Dict[str, QtWidgets.QAction]

    @classmethod
    def instance(cls) -> Union['QudiTrayIcon', None]:
        """Returns the only instance (singleton) of this class."""
        with cls._lock:
            if cls._instance is None:
                return None
            return cls._instance()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None or cls._instance() is None:
                obj = super().__new__(cls, *args, **kwargs)
                cls._instance = weakref.ref(obj)
                return obj
            raise RuntimeError(
                'QudiTrayIcon is a singleton. An instance has already been created in this '
                'process. Please use QudiTrayIcon.instance() instead.'
            )

    def __init__(self,
                 quit_callback: Callable[[], None],
                 restart_callback: Callable[[], None],
                 main_gui_callback: Optional[Callable[[], None]] = None,
                 parent: Optional[QtCore.QObject] = None):
        super().__init__(icon=QtWidgets.QApplication.instance().windowIcon(), parent=parent)

        self.right_click_menu = QtWidgets.QMenu('Menu')
        self.left_click_menu = QtWidgets.QMenu('Modules')
        self._module_actions = dict()

        iconpath = os.path.join(get_artwork_dir(), 'icons')
        # Generate quit action
        icon = QtGui.QIcon()
        icon.addFile(os.path.join(iconpath, 'application-exit'), QtCore.QSize(16, 16))
        self.quit_action = QtWidgets.QAction(icon, 'Quit', self.right_click_menu)
        self.quit_action.triggered.connect(quit_callback, QtCore.Qt.QueuedConnection)
        self.right_click_menu.addAction(self.quit_action)
        # Generate restart action
        icon = QtGui.QIcon()
        icon.addFile(os.path.join(iconpath, 'view-refresh'), QtCore.QSize(16, 16))
        self.restart_action = QtWidgets.QAction(icon, 'Restart', self.right_click_menu)
        self.restart_action.triggered.connect(restart_callback, QtCore.Qt.QueuedConnection)
        self.right_click_menu.addAction(self.restart_action)
        # Generate main GUI action if needed
        if main_gui_callback is not None:
            icon = QtGui.QIcon()
            icon.addFile(os.path.join(iconpath, 'go-home'), QtCore.QSize(16, 16))
            self.main_gui_action = QtWidgets.QAction(icon, 'Main GUI', self.left_click_menu)
            self.main_gui_action.triggered.connect(main_gui_callback, QtCore.Qt.QueuedConnection)
            self.left_click_menu.addAction(self.main_gui_action)
            self.left_click_menu.addSeparator()

        # Register both menus to be shown upon right and left mouse click events
        self.setContextMenu(self.right_click_menu)
        self.activated.connect(self._handle_activation)

    def add_module_action(self, name: str, callback: Callable[[], None]) -> None:
        with self._lock:
            if name in self._module_actions:
                raise ValueError(f'Action for module with name "{name}" already registered in tray')
            icon = QtGui.QIcon()
            icon.addFile(os.path.join(get_artwork_dir(), 'icons', 'go-next'))
            action = QtWidgets.QAction(icon=icon, text=name)
            action.triggered.connect(callback)
            self.left_click_menu.addAction(action)
            self._module_actions[name] = action

    def remove_module_action(self, name: str) -> None:
        with self._lock:
            action = self._module_actions.pop(name, None)
            try:
                action.triggered.disconnect()
            except AttributeError:
                pass
            else:
                self.left_click_menu.removeAction(action)

    @QtCore.Slot(QtWidgets.QSystemTrayIcon.ActivationReason)
    def _handle_activation(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason) -> None:
        """
        This method is called when the tray icon is left-clicked. It opens a menu at the position
        of the click.
        """
        if reason == self.Trigger:
            self.left_click_menu.exec_(QtGui.QCursor.pos())
