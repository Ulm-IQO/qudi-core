# -*- coding: utf-8 -*-
"""
This file contains a custom module widget for the Qudi manager GUI.

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
from typing import Optional, Union, Tuple

from qudi.util.paths import get_artwork_dir
from qudi.core.module import ModuleState, ModuleBase
from qudi.core.modulemanager import ModuleManager


class ModuleListModel(QtCore.QAbstractListModel):
    """ List model for all configured qudi modules with a certain ModuleBase filter """
    def __init__(self,
                 base: ModuleBase,
                 module_manager: ModuleManager,
                 parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        self._base = base
        self._module_manager = module_manager
        self._index_to_name = [name for name in self._module_manager.module_names if
                               self._module_manager.module_base(name) == base]
        self._name_to_index = {name: idx for idx, name in enumerate(self._index_to_name)}
        # Handle data updates from module manager
        self._module_manager.sigStateChanged.connect(self._state_updated)
        self._module_manager.sigHasAppdataChanged.connect(self._state_updated)

    def rowCount(self, parent: Optional[QtCore.QModelIndex] = None) -> int:
        """ Returns the number of stored items (rows) """
        return len(self._index_to_name)

    def flags(self, index: Optional[QtCore.QModelIndex] = None) -> QtCore.Qt.ItemFlags:
        """ Determines what can be done with the given indexed cell """
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self,
             index: QtCore.QModelIndex,
             role: Optional[QtCore.Qt.ItemDataRole] = QtCore.Qt.DisplayRole
             ) -> Union[None, Tuple[str, ModuleState, bool]]:
        """ Get data from model for a given cell. Data can have a role that affects display. """
        if index.isValid() and role == QtCore.Qt.DisplayRole:
            name = self._index_to_name[index.row()]
            state = self._module_manager.module_state(name)
            has_appdata = self._module_manager.has_appdata(name)
            return name, state, has_appdata
        return None

    def headerData(self,
                   section: int,
                   orientation: QtCore.Qt.Orientation,
                   role: Optional[QtCore.Qt.ItemDataRole] = QtCore.Qt.DisplayRole
                   ) -> Union[None, str]:
        """ Data for the table view headers """
        if (orientation == QtCore.Qt.Horizontal) and (role == QtCore.Qt.DisplayRole):
            return 'State'
        return None

    def _state_updated(self, base: ModuleBase, name: str, _: Union[ModuleState, bool]) -> None:
        if base == self._base:
            index = self.index(self._name_to_index[name], 0)
            self.dataChanged.emit(index, index)


class ModuleFrameWidget(QtWidgets.QWidget):
    """
    Custom module QWidget for the Qudi main GUI
    """
    sigActivateClicked = QtCore.Signal(str)
    sigDeactivateClicked = QtCore.Signal(str)
    sigReloadClicked = QtCore.Signal(str)
    sigCleanupClicked = QtCore.Signal(str)

    def __init__(self, *args, module_name: Optional[str] = '', **kwargs):
        super().__init__(*args, **kwargs)
        self._module_name = module_name

        # Create QToolButtons
        self.cleanup_button = QtWidgets.QToolButton()
        self.deactivate_button = QtWidgets.QToolButton()
        self.reload_button = QtWidgets.QToolButton()
        # Set icons for QToolButtons
        icon_path = os.path.join(get_artwork_dir(), 'icons')
        self.cleanup_button.setIcon(QtGui.QIcon(os.path.join(icon_path, 'edit-clear')))
        self.deactivate_button.setIcon(QtGui.QIcon(os.path.join(icon_path, 'edit-delete')))
        self.reload_button.setIcon(QtGui.QIcon(os.path.join(icon_path, 'view-refresh')))
        # Create activation pushbutton
        self.activate_button = QtWidgets.QPushButton(f'Activate {self._module_name}')
        self.activate_button.setCheckable(True)
        self.activate_button.setMinimumWidth(200)
        self.activate_button.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                           QtWidgets.QSizePolicy.Fixed)
        # Create status label
        self.status_label = QtWidgets.QLabel(ModuleState.DEACTIVATED.value)

        # Set tooltips
        self.cleanup_button.setToolTip(
            'Clean up module appdata file. Only available for deactivated modules.'
        )
        self.deactivate_button.setToolTip('Deactivate module and all modules depending on it')
        self.reload_button.setToolTip(
            'Reload module, i.e. re-import the containing python module from file'
        )
        self.activate_button.setToolTip('Activate this module and all its dependencies')
        self.status_label.setToolTip('Displays module status information')

        # Combine all widgets in a layout and set as main layout
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.activate_button, 0, 0)
        layout.addWidget(self.reload_button, 0, 1)
        layout.addWidget(self.deactivate_button, 0, 2)
        layout.addWidget(self.cleanup_button, 0, 3)
        layout.addWidget(self.status_label, 1, 0, 1, 4)
        self.setLayout(layout)

        # Connect widget signals
        self.activate_button.clicked.connect(self.activate_clicked)
        self.deactivate_button.clicked.connect(self.deactivate_clicked)
        self.reload_button.clicked.connect(self.reload_clicked)
        self.cleanup_button.clicked.connect(self.cleanup_clicked)

    def set_module_data(self, name: str, state: ModuleState, has_appdata: bool) -> None:
        self._module_name = name
        if state == ModuleState.DEACTIVATED:
            self.activate_button.setText(f'Activate {self._module_name}')
            self.cleanup_button.setEnabled(has_appdata)
            self.deactivate_button.setEnabled(False)
            self.reload_button.setEnabled(True)
            self.activate_button.setChecked(False)
        else:
            self.activate_button.setText(self._module_name)
            self.cleanup_button.setEnabled(False)
            self.deactivate_button.setEnabled(True)
            self.reload_button.setEnabled(True)
            self.activate_button.setChecked(True)
        self.status_label.setText(f'Module is {state.value}')

    @QtCore.Slot()
    def activate_clicked(self):
        self.sigActivateClicked.emit(self._module_name)

    @QtCore.Slot()
    def deactivate_clicked(self):
        self.sigDeactivateClicked.emit(self._module_name)

    @QtCore.Slot()
    def cleanup_clicked(self):
        self.sigCleanupClicked.emit(self._module_name)

    @QtCore.Slot()
    def reload_clicked(self):
        self.sigReloadClicked.emit(self._module_name)


class ModuleListItemDelegate(QtWidgets.QStyledItemDelegate):
    sigActivateClicked = QtCore.Signal(str)
    sigDeactivateClicked = QtCore.Signal(str)
    sigReloadClicked = QtCore.Signal(str)
    sigCleanupClicked = QtCore.Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__render_widget = ModuleFrameWidget()
        self.__origin = QtCore.QPoint()

    def createEditor(self, parent, option, index) -> QtWidgets.QWidget:
        widget = ModuleFrameWidget(parent=parent)
        # Found no other way to pefectly match editor and rendered item view (using paint())
        widget.setContentsMargins(2, 2, 2, 2)
        widget.sigActivateClicked.connect(self.sigActivateClicked)
        widget.sigDeactivateClicked.connect(self.sigDeactivateClicked)
        widget.sigReloadClicked.connect(self.sigReloadClicked)
        widget.sigCleanupClicked.connect(self.sigCleanupClicked)
        return widget

    def setEditorData(self, editor, index) -> None:
        data = index.data()
        if data is not None:
            editor.set_module_data(*data)

    # def destroyEditor(self, editor, index) -> None:
    #     return super().destroyEditor(editor, index)

    def sizeHint(self, option=None, index=None):
        return self.__render_widget.sizeHint()

    def paint(self, painter, option, index):
        data = index.data()
        self.__render_widget.set_module_data(*data)
        self.__render_widget.setGeometry(option.rect)
        painter.save()
        painter.translate(option.rect.topLeft())
        self.__render_widget.render(painter, self.__origin)
        painter.restore()


class ModuleListView(QtWidgets.QListView):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)
        delegate = ModuleListItemDelegate()
        self.setItemDelegate(delegate)
        self.setMinimumWidth(delegate.sizeHint().width())
        self.setUniformItemSizes(True)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(1)
        self.previous_index = QtCore.QModelIndex()

    def mouseMoveEvent(self, event):
        index = self.indexAt(event.pos())
        if index != self.previous_index:
            if self.previous_index.isValid():
                self.closePersistentEditor(self.previous_index)
            if index.isValid():
                self.openPersistentEditor(index)
            self.previous_index = index

    def leaveEvent(self, event):
        if self.previous_index.isValid():
            self.closePersistentEditor(self.previous_index)
        self.previous_index = QtCore.QModelIndex()


class ModuleWidget(QtWidgets.QTabWidget):
    """
    """
    sigActivateModule = QtCore.Signal(str)
    sigDeactivateModule = QtCore.Signal(str)
    sigCleanupModule = QtCore.Signal(str)
    sigReloadModule = QtCore.Signal(str)

    def __init__(self, *args, module_manager: ModuleManager, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.list_views = {'gui'     : ModuleListView(),
                           'logic'   : ModuleListView(),
                           'hardware': ModuleListView()}
        self.data_models = {'gui'     : ModuleListModel(base=ModuleBase.GUI,
                                                        module_manager=module_manager,
                                                        parent=self),
                            'logic'   : ModuleListModel(base=ModuleBase.LOGIC,
                                                        module_manager=module_manager,
                                                        parent=self),
                            'hardware': ModuleListModel(base=ModuleBase.HARDWARE,
                                                        module_manager=module_manager,
                                                        parent=self)}
        self.addTab(self.list_views['gui'], 'GUI')
        self.addTab(self.list_views['logic'], 'Logic')
        self.addTab(self.list_views['hardware'], 'Hardware')
        for base, view in self.list_views.items():
            view.setModel(self.data_models[base])
            delegate = view.itemDelegate()
            delegate.sigActivateClicked.connect(self.sigActivateModule)
            delegate.sigDeactivateClicked.connect(self.sigDeactivateModule)
            delegate.sigReloadClicked.connect(self.sigReloadModule)
            delegate.sigCleanupClicked.connect(self.sigCleanupModule)
