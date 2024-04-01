# -*- coding: utf-8 -*-
"""
This file contains the QMainWindow class for the task GUI.

Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
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

import os
from PySide2 import QtCore, QtGui, QtWidgets

from qudi.util.paths import get_artwork_dir
from qudi.core.task import ModuleTaskManager

from .taskwidget import TaskTableView


class TaskMainWindow(QtWidgets.QMainWindow):
    """ Main Window definition for the task GUI """

    sigClosed = QtCore.Signal()

    def __init__(self, task_manager: ModuleTaskManager, **kwargs):
        super().__init__(**kwargs)
        self.setWindowTitle('qudi: Taskrunner')

        # Create actions
        icon_path = os.path.join(get_artwork_dir(), 'icons')
        self.action_quit = QtWidgets.QAction()
        self.action_quit.setIcon(QtGui.QIcon(os.path.join(icon_path, 'application-exit')))
        self.action_quit.setText('Close')
        self.action_quit.setToolTip('Close')
        self.action_quit.triggered.connect(self.close)

        # Create menu bar
        self.menubar = QtWidgets.QMenuBar()
        menu = QtWidgets.QMenu('File')
        menu.addAction(self.action_quit)
        self.menubar.addMenu(menu)
        self.setMenuBar(self.menubar)

        # Initialize central widget (table view) and resize window
        self.task_view = TaskTableView(task_manager=task_manager)
        self.setCentralWidget(self.task_view)
        self.adjustSize()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        super().closeEvent(event)
        self.sigClosed.emit()
