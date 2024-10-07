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

from PySide2 import QtWidgets, QtCore
from typing import Optional, Union

from qudi.core.modulemanager import ModuleManager


class SharedModulesListModel(QtCore.QAbstractListModel):
    """ List model for all local qudi modules that are allowed to be shared remotely """
    def __init__(self,
                 module_manager: ModuleManager,
                 parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        self._module_manager = module_manager
        self._index_to_name = sorted(name for name in self._module_manager.module_names if
                                     self._module_manager.allow_remote(name))
        # self._name_to_index = {name: idx for idx, name in enumerate(self._index_to_name)}

    def rowCount(self, parent: Optional[QtCore.QModelIndex] = None) -> int:
        """ Returns the number of stored items (rows) """
        return len(self._index_to_name)

    def flags(self, index: Optional[QtCore.QModelIndex] = None) -> QtCore.Qt.ItemFlags:
        """ Determines what can be done with the given indexed cell """
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self,
             index: QtCore.QModelIndex,
             role: Optional[QtCore.Qt.ItemDataRole] = QtCore.Qt.DisplayRole
             ) -> Union[None, str]:
        """ Get data from model for a given cell. Data can have a role that affects display. """
        if index.isValid() and role == QtCore.Qt.DisplayRole:
            return self._index_to_name[index.row()]
        return None

    def headerData(self,
                   section: int,
                   orientation: QtCore.Qt.Orientation,
                   role: Optional[QtCore.Qt.ItemDataRole] = QtCore.Qt.DisplayRole
                   ) -> Union[None, str]:
        """ Data for the table view headers """
        if (orientation == QtCore.Qt.Horizontal) and (role == QtCore.Qt.DisplayRole):
            return 'Module Name'
        return None


class RemoteModulesListModel(QtCore.QAbstractListModel):
    """ List model for all configured remote qudi modules """
    def __init__(self,
                 module_manager: ModuleManager,
                 parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        self._index_to_name = sorted(name for name in module_manager.module_names if
                                     module_manager.is_remote(name))
        # self._name_to_index = {name: idx for idx, name in enumerate(self._index_to_name)}

    def rowCount(self, parent: Optional[QtCore.QModelIndex] = None) -> int:
        """ Returns the number of stored items (rows) """
        return len(self._index_to_name)

    def flags(self, index: Optional[QtCore.QModelIndex] = None) -> QtCore.Qt.ItemFlags:
        """ Determines what can be done with the given indexed cell """
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self,
             index: QtCore.QModelIndex,
             role: Optional[QtCore.Qt.ItemDataRole] = QtCore.Qt.DisplayRole
             ) -> Union[None, str]:
        """ Get data from model for a given cell. Data can have a role that affects display. """
        if index.isValid() and role == QtCore.Qt.DisplayRole:
            return self._index_to_name[index.row()]
        return None

    def headerData(self,
                   section: int,
                   orientation: QtCore.Qt.Orientation,
                   role: Optional[QtCore.Qt.ItemDataRole] = QtCore.Qt.DisplayRole
                   ) -> Union[None, str]:
        """ Data for the table view headers """
        if (orientation == QtCore.Qt.Horizontal) and (role == QtCore.Qt.DisplayRole):
            return 'Module Name'
        return None


class RemoteWidget(QtWidgets.QWidget):
    """

    """
    def __init__(self, module_manager: ModuleManager, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

        # Create widgets
        local_label = QtWidgets.QLabel('shared modules')
        remote_label = QtWidgets.QLabel('remote modules')
        self.server_label = QtWidgets.QLabel('Server URL')
        self.shared_module_model = SharedModulesListModel(module_manager=module_manager,
                                                          parent=self)
        self.remote_module_model = RemoteModulesListModel(module_manager=module_manager,
                                                          parent=self)
        self.shared_module_listview = QtWidgets.QListView()
        self.shared_module_listview.setUniformItemSizes(True)
        self.shared_module_listview.setAlternatingRowColors(True)
        self.shared_module_listview.setModel(self.shared_module_model)
        self.remote_module_listview = QtWidgets.QListView()
        self.remote_module_listview.setUniformItemSizes(True)
        self.remote_module_listview.setAlternatingRowColors(True)
        self.remote_module_listview.setModel(self.remote_module_model)

        # Group widgets in a layout and set as main layout
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.server_label, 0, 0, 1, 2)
        layout.addWidget(local_label, 1, 0)
        layout.addWidget(self.shared_module_listview, 2, 0)
        layout.addWidget(remote_label, 1, 1)
        layout.addWidget(self.remote_module_listview, 2, 1)
        self.setLayout(layout)
