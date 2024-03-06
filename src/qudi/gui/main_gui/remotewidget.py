# -*- coding: utf-8 -*-
"""
# FIXME

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

from PySide2 import QtWidgets


class RemoteWidget(QtWidgets.QWidget):
    """

    """
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        # Create widgets
        local_label = QtWidgets.QLabel('shared modules')
        remote_label = QtWidgets.QLabel('remote modules')
        self.server_label = QtWidgets.QLabel('Server URL')
        self.shared_module_listview = QtWidgets.QListView()
        self.shared_module_listview.setUniformItemSizes(True)
        self.shared_module_listview.setAlternatingRowColors(True)
        self.remote_module_listview = QtWidgets.QListView()
        self.remote_module_listview.setUniformItemSizes(True)
        self.remote_module_listview.setAlternatingRowColors(True)

        # Group widgets in a layout and set as main layout
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.server_label, 0, 0, 1, 2)
        layout.addWidget(local_label, 1, 0)
        layout.addWidget(self.shared_module_listview, 2, 0)
        layout.addWidget(remote_label, 1, 1)
        layout.addWidget(self.remote_module_listview, 2, 1)
        self.setLayout(layout)
