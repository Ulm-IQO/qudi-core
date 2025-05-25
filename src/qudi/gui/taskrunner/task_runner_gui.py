# -*- coding: utf-8 -*-
"""
This file contains the qudi task runner GUI.

Copyright (c) 2021-2024, the qudi developers. See the AUTHORS.md file at the top-level directory of
this distribution and on <https://github.com/Ulm-IQO/qudi-core/>

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

from PySide2 import QtCore

from qudi.core.connector import Connector
from qudi.core.module import GuiBase
from qudi.core.modulemanager import ModuleManager
from qudi.gui.taskrunner.main_window import TaskMainWindow
from qudi.logic.taskrunner import TaskRunnerLogic


class TaskRunnerGui(GuiBase):
    """ TODO: Document """

    # declare connectors
    _task_runner = Connector(name='task_runner', interface=TaskRunnerLogic)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mw = None

    def on_activate(self):
        """Create all UI objects and show the window """
        # Initialize main window and connect task widgets
        self._mw = TaskMainWindow(task_manager=self._task_runner.data_model)
        self._mw.sigClosed.connect(self._deactivate_self)
        self._restore_window_geometry(self._mw)
        self.show()

    def show(self):
        """Make sure that the window is visible and at the top.
        """
        self._mw.show()

    @QtCore.Slot()
    def _deactivate_self(self):
        ModuleManager.instance().deactivate_module(self.nametag)

    def on_deactivate(self):
        """Hide window and stop ipython console.
        """
        self._save_window_geometry(self._mw)
        self._mw.close()
        self._mw = None
