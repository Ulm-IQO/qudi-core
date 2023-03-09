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
from typing import Optional, Mapping, Dict
from PySide2 import QtCore, QtGui, QtWidgets
from qudi.util.paths import get_artwork_dir
from qudi.util.mutex import Mutex
from qudi.core.module import ModuleBase, ModuleState
from qudi.core.modulemanager import ModuleInfo


class ModuleFrameWidget(QtWidgets.QWidget):
    """
    Custom module QWidget for the Qudi main GUI
    """
    sigActivateClicked = QtCore.Signal(str)
    sigDeactivateClicked = QtCore.Signal(str)
    sigReloadClicked = QtCore.Signal(str)
    sigCleanupClicked = QtCore.Signal(str)

    def __init__(self, *args, module_name: Optional[str] = None, **kwargs):
        super().__init__(*args, **kwargs)

        # Create QToolButtons
        self.cleanup_button = QtWidgets.QToolButton()
        self.cleanup_button.setObjectName('cleanupButton')
        self.deactivate_button = QtWidgets.QToolButton()
        self.deactivate_button.setObjectName('deactivateButton')
        self.reload_button = QtWidgets.QToolButton()
        self.reload_button.setObjectName('reloadButton')

        # Set icons for QToolButtons
        icon_path = os.path.join(get_artwork_dir(), 'icons')
        self.cleanup_button.setIcon(QtGui.QIcon(os.path.join(icon_path, 'edit-clear')))
        self.deactivate_button.setIcon(QtGui.QIcon(os.path.join(icon_path, 'edit-delete')))
        self.reload_button.setIcon(QtGui.QIcon(os.path.join(icon_path, 'view-refresh')))

        # Create activation pushbutton
        self.activate_button = QtWidgets.QPushButton('load/activate <module_name>')
        self.activate_button.setObjectName('loadButton')
        self.activate_button.setCheckable(True)
        self.activate_button.setMinimumWidth(200)
        self.activate_button.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                           QtWidgets.QSizePolicy.Fixed)

        # Create status label
        self.status_label = QtWidgets.QLabel('Module status goes here...')
        self.status_label.setObjectName('statusLabel')

        # Set tooltips
        self.cleanup_button.setToolTip('Clean up module status file')
        self.deactivate_button.setToolTip('Deactivate module')
        self.reload_button.setToolTip('Reload module')
        self.activate_button.setToolTip('Load this module and all its dependencies')
        self.status_label.setToolTip('Displays module status information')

        # Combine all widgets in a layout and set as main layout
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.activate_button, 0, 0)
        layout.addWidget(self.reload_button, 0, 1)
        layout.addWidget(self.deactivate_button, 0, 2)
        layout.addWidget(self.cleanup_button, 0, 3)
        layout.addWidget(self.status_label, 1, 0, 1, 4)
        self.setLayout(layout)

        self._module_name = ''
        if module_name:
            self.set_module_name(module_name)

        self.activate_button.clicked.connect(self.activate_clicked)
        self.deactivate_button.clicked.connect(self.deactivate_clicked)
        self.reload_button.clicked.connect(self.reload_clicked)
        self.cleanup_button.clicked.connect(self.cleanup_clicked)

    def set_module_name(self, name: str) -> None:
        if name:
            self.activate_button.setText('Load {0}'.format(name))
            self._module_name = name

    def set_module_info(self, info: ModuleInfo) -> None:
        if info.state == ModuleState.DEACTIVATED:
            self.activate_button.setText(f'Activate {self._module_name}')
            self.cleanup_button.setEnabled(True)
            self.deactivate_button.setEnabled(False)
            self.reload_button.setEnabled(True)
            if self.activate_button.isChecked():
                self.activate_button.setChecked(False)
        else:
            self.activate_button.setText(
                f'Show {self._module_name}' if info.base == ModuleBase.GUI else self._module_name
            )
            self.cleanup_button.setEnabled(False)
            self.deactivate_button.setEnabled(True)
            self.reload_button.setEnabled(True)
            if not self.activate_button.isChecked():
                self.activate_button.setChecked(True)
        self.status_label.setText(f'Module is {info.state.value}')
        self.cleanup_button.setEnabled(info.has_appdata)

    @QtCore.Slot()
    def activate_clicked(self) -> None:
        self.sigActivateClicked.emit(self._module_name)

    @QtCore.Slot()
    def deactivate_clicked(self) -> None:
        self.sigDeactivateClicked.emit(self._module_name)

    @QtCore.Slot()
    def cleanup_clicked(self) -> None:
        self.sigCleanupClicked.emit(self._module_name)

    @QtCore.Slot()
    def reload_clicked(self) -> None:
        self.sigReloadClicked.emit(self._module_name)


class ModuleListModel(QtCore.QAbstractListModel):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = Mutex()
        self._module_infos = dict()
        self._module_names = list()

    def rowCount(self, parent):
        return len(self._module_names)

    def data(self, index, role):
        if not index.isValid() or role != QtCore.Qt.DisplayRole:
            return
        row = index.row()
        if row >= len(self._module_names):
            return
        name = self._module_names[row]
        info = self._module_infos[name]
        return name, info

    def flags(self, index):
        return QtCore.Qt.ItemNeverHasChildren | QtCore.Qt.ItemIsEnabled

    def append_module(self, name: str, info: ModuleInfo) -> None:
        with self._lock:
            if name in self._module_infos:
                raise RuntimeError(f'Module with name "{name}" already present in ModuleListModel.')
            self.beginInsertRows(len(self._module_names))
            self._module_names.append(name)
            self._module_infos[name] = info
            self.endInsertRows()

    def remove_module(self, name: str) -> None:
        with self._lock:
            if name not in self._module_infos:
                return
            row = self._module_names.index(name)
            self.beginRemoveRows(row, row + 1)
            del self._module_names[row]
            del self._module_infos[name]
            self.endRemoveRows()

    def reset_modules(self, infos_dict: Dict[str, ModuleInfo]) -> None:
        with self._lock:
            self.beginResetModel()
            self._module_infos = infos_dict.copy()
            self._module_names = list(infos_dict)
            self.endResetModel()

    def change_module_info(self, name: str, info: ModuleInfo) -> None:
        with self._lock:
            if name not in self._module_infos:
                raise RuntimeError(
                    f'Can not change module info in ModuleListModel. No module by the name '
                    f'"{name}" found.'
                )
            self._module_infos[name] = info
            row = self._module_names.index(name)
            self.dataChanged.emit(self.createIndex(row, 0),
                                  self.createIndex(row + 1, 0),
                                  (QtCore.Qt.DisplayRole,))


class ModuleListItemDelegate(QtWidgets.QStyledItemDelegate):
    """
    """
    sigActivateClicked = QtCore.Signal(str)
    sigDeactivateClicked = QtCore.Signal(str)
    sigReloadClicked = QtCore.Signal(str)
    sigCleanupClicked = QtCore.Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.render_widget = ModuleFrameWidget()
        self.__origin = QtCore.QPoint()

    def createEditor(self, parent, option, index):
        widget = ModuleFrameWidget(parent=parent)
        # Found no other way to pefectly match editor and rendered item view (using paint())
        widget.setContentsMargins(2, 2, 2, 2)
        widget.sigActivateClicked.connect(self.sigActivateClicked)
        widget.sigDeactivateClicked.connect(self.sigDeactivateClicked)
        widget.sigReloadClicked.connect(self.sigReloadClicked)
        widget.sigCleanupClicked.connect(self.sigCleanupClicked)
        return widget

    def setEditorData(self, editor, index):
        data = index.data()
        if data:
            editor.set_module_name(data[0])
            editor.set_module_info(data[1])

    def setModelData(self, editor, model, index):
        pass

    def sizeHint(self, option=None, index=None):
        return self.render_widget.sizeHint()

    def paint(self, painter, option, index):
        """
        """
        name, info = index.data()
        self.render_widget.set_module_name(name)
        self.render_widget.set_module_info(info)
        self.render_widget.setGeometry(option.rect)
        painter.save()
        painter.translate(option.rect.topLeft())
        self.render_widget.render(painter, self.__origin)
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.list_models = {ModuleBase.GUI     : ModuleListModel(),
                            ModuleBase.LOGIC   : ModuleListModel(),
                            ModuleBase.HARDWARE: ModuleListModel()}
        self.list_views = {ModuleBase.GUI     : ModuleListView(),
                           ModuleBase.LOGIC   : ModuleListView(),
                           ModuleBase.HARDWARE: ModuleListView()}
        self.addTab(self.list_views[ModuleBase.GUI], 'GUI')
        self.addTab(self.list_views[ModuleBase.LOGIC], 'Logic')
        self.addTab(self.list_views[ModuleBase.HARDWARE], 'Hardware')
        for base, view in self.list_views.items():
            view.setModel(self.list_models[base])
            delegate = view.itemDelegate()
            delegate.sigActivateClicked.connect(self.sigActivateModule)
            delegate.sigDeactivateClicked.connect(self.sigDeactivateModule)
            delegate.sigReloadClicked.connect(self.sigReloadModule)
            delegate.sigCleanupClicked.connect(self.sigCleanupModule)

    @QtCore.Slot(dict)
    def update_modules(self, modules_info: Mapping[str, ModuleInfo]):
        for base, model in self.list_models.items():
            model.reset_modules(
                {name: info for name, info in modules_info.items() if info.base == base}
            )

    @QtCore.Slot(str, ModuleInfo)
    def update_module_info(self, name: str, info: ModuleInfo) -> None:
        model = self.list_models[info.base]
        model.change_module_info(name, info)
