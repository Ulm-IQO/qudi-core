# -*- coding: utf-8 -*-
"""
This file contains a widget to control a ModuleTask and display its state.

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

__all__ = ['TaskTableView', 'TaskResultDelegate', 'TaskStateDelegate', 'TaskArgumentsDelegate',
           'TaskStateWidget', 'TaskArgumentsWidget']

import os
import inspect
from typing import Optional, Dict, Any, Mapping, Callable
from PySide2 import QtCore, QtWidgets, QtGui

from qudi.util.paths import get_artwork_dir
from qudi.util.parameters import ParameterWidgetMapper
from qudi.util.helpers import call_slot_from_native_thread
from qudi.core.task import ModuleTaskState, ModuleTaskWorker, ModuleTaskManager


class TaskArgumentsWidget(QtWidgets.QScrollArea):
    """ """
    def __init__(self,
                 parameters: Mapping[str, inspect.Parameter],
                 parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        self.setWidgetResizable(True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        # Create task parameter editors and put them in the scroll area
        self.parameter_widgets = dict()
        layout = QtWidgets.QGridLayout()
        for row, (name, param) in enumerate(parameters.items()):
            editor = ParameterWidgetMapper.widget_for_parameter(param)
            if editor is None:
                editor = QtWidgets.QLabel('Unknown parameter type')
                editor.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
            else:
                editor = editor()
                editor.setMinimumWidth(100)
            label = QtWidgets.QLabel(f'{name}:')
            label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
            self.parameter_widgets[name] = (label, editor)
            layout.addWidget(label, row, 0)
            layout.addWidget(editor, row, 1)
        layout.setColumnStretch(1, 1)
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.setWidget(widget)

    def get_arguments(self) -> Dict[str, Any]:
        arguments = dict()
        for name, (_, editor) in self.parameter_widgets.items():
            if isinstance(editor, QtWidgets.QLabel):
                continue
            try:
                arguments[name] = editor.value()
            except AttributeError:
                try:
                    arguments[name] = editor.isChecked()
                except AttributeError:
                    arguments[name] = editor.text()
        return arguments

    def set_arguments(self, arguments: Mapping[str, Any]) -> None:
        for name, value in arguments.items():
            try:
                editor = self.parameter_widgets[name][1]
            except KeyError:
                continue
            if isinstance(editor, QtWidgets.QLabel):
                continue
            try:
                editor.setValue(value)
            except AttributeError:
                try:
                    editor.setChecked(value)
                except AttributeError:
                    editor.setText(value)


class TaskStateWidget(QtWidgets.QWidget):
    """ """
    sigRunInterruptClicked = QtCore.Signal(bool)  # run: True, interrupt: False

    def __init__(self,
                 parent: Optional[QtWidgets.QWidget] = None,
                 f: Optional[QtCore.Qt.WindowFlags] = QtCore.Qt.WindowFlags()) -> None:
        super().__init__(parent=parent, f=f)
        # Remember icons for swapping and current button state
        icon_dir = os.path.join(get_artwork_dir(), 'icons')
        self._play_icon = QtGui.QIcon(os.path.join(icon_dir, 'media-playback-start'))
        self._stop_icon = QtGui.QIcon(os.path.join(icon_dir, 'media-playback-stop'))
        self._interrupt_enabled = True

        # Create state label and run/interrupt button
        self.state_label = QtWidgets.QLabel(ModuleTaskState.RUNNING.value)
        self.state_label.setAlignment(QtCore.Qt.AlignCenter)
        font = self.state_label.font()
        font.setBold(True)
        self.state_label.setFont(font)
        self.run_interrupt_button = QtWidgets.QToolButton()
        self.run_interrupt_button.setIcon(self._stop_icon)
        self.run_interrupt_button.setToolButtonStyle(QtGui.Qt.ToolButtonIconOnly)
        control_width = self.state_label.sizeHint().width() * 1.5
        self.run_interrupt_button.setFixedWidth(control_width)
        self.run_interrupt_button.setFixedHeight(control_width)
        self.run_interrupt_button.setIconSize(self.run_interrupt_button.size())
        self.run_interrupt_button.clicked.connect(self._run_interrupt_clicked)
        # layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.run_interrupt_button, alignment=QtCore.Qt.AlignCenter)
        layout.addWidget(self.state_label)
        self.setLayout(layout)

    @QtCore.Slot()
    def _run_interrupt_clicked(self) -> None:
        self.run_interrupt_button.setEnabled(False)
        self.sigRunInterruptClicked.emit(not self._interrupt_enabled)

    @QtCore.Slot(ModuleTaskState)
    def update_state(self, state: ModuleTaskState) -> None:
        self.state_label.setText(state.value)
        if state.running:
            self.run_interrupt_button.setIcon(self._stop_icon)
            self._interrupt_enabled = True
        else:
            self.run_interrupt_button.setIcon(self._play_icon)
            self._interrupt_enabled = False
        self.run_interrupt_button.setEnabled(True)


class TaskArgumentsDelegate(QtWidgets.QStyledItemDelegate):
    """ """
    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent=parent)
        self._size_hint = QtCore.QSize(300, 50)

    def createEditor(self, parent, option, index) -> QtWidgets.QWidget:
        editor = TaskArgumentsWidget(parameters=index.data(QtCore.Qt.UserRole).call_parameters,
                                     parent=parent)
        # Found no other way to perfectly match editor and rendered item view (using paint())
        editor.setContentsMargins(2, 2, 2, 2)
        return editor

    def setEditorData(self, editor, index) -> None:
        editor.set_arguments(index.data(QtCore.Qt.DisplayRole))

    def setModelData(self, editor, model, index) -> None:
        model.setData(index, editor.get_arguments())

    def destroyEditor(self, editor, index):
        # Needed for persistent editor (does not automatically commit data to model)
        self.setModelData(editor, index.model(), index)
        return super().destroyEditor(editor, index)

    def sizeHint(self, option=None, index=None):
        return self._size_hint

    def paint(self, painter, option, index):
        task = index.data(QtCore.Qt.UserRole)
        widget = TaskArgumentsWidget(parameters=task.call_parameters)
        widget.set_arguments(task.arguments)
        widget.setGeometry(option.rect)
        painter.save()
        painter.translate(option.rect.topLeft())
        widget.render(painter, QtCore.QPoint())
        painter.restore()


class TaskStateDelegate(QtWidgets.QStyledItemDelegate):
    """ """

    _sigRunTask = QtCore.Signal()

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent=parent)
        self._render_widget = TaskStateWidget()
        self._size_hint = self._render_widget.sizeHint()

    def createEditor(self, parent, option, index) -> QtWidgets.QWidget:
        task = index.data(QtCore.Qt.UserRole)
        editor = TaskStateWidget(parent=parent)
        editor.sigRunInterruptClicked.connect(self.__get_run_interrupt_slot(task))
        # Found no other way to perfectly match editor and rendered item view (using paint())
        editor.setContentsMargins(2, 2, 2, 2)
        return editor

    def setEditorData(self, editor, index) -> None:
        editor.update_state(index.data(QtCore.Qt.DisplayRole))

    def destroyEditor(self, editor, index):
        editor.sigRunInterruptClicked.disconnect()
        return super().destroyEditor(editor, index)

    def sizeHint(self, option=None, index=None):
        return self._size_hint

    def paint(self, painter, option, index):
        self._render_widget.update_state(index.data(QtCore.Qt.DisplayRole))
        self._render_widget.setGeometry(option.rect)
        painter.save()
        painter.translate(option.rect.topLeft())
        self._render_widget.render(painter, QtCore.QPoint())
        painter.restore()

    @staticmethod
    def __get_run_interrupt_slot(task: ModuleTaskWorker) -> Callable[[bool], None]:

        def run_interrupt_slot(run: bool) -> None:
            if run:
                call_slot_from_native_thread(task, 'run', blocking=False)
            else:
                task.interrupt()

        return run_interrupt_slot


class TaskResultDelegate(QtWidgets.QStyledItemDelegate):
    """ """

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent=parent)
        icon_dir = os.path.join(get_artwork_dir(), 'icons')
        self._invalid_icon = QtGui.QIcon(os.path.join(icon_dir, 'edit-delete'))
        self._valid_icon = QtGui.QIcon(os.path.join(icon_dir, 'dialog-ok-apply'))
        self._size_hint = QtCore.QSize(32, 32)

    def sizeHint(self, option=None, index=None):
        return self._size_hint

    def paint(self, painter, option, index):
        if index.data(QtCore.Qt.DisplayRole)[1]:
            self._valid_icon.paint(painter, option.rect)
        else:
            self._invalid_icon.paint(painter, option.rect)


class TaskTableView(QtWidgets.QTableView):
    """ """
    def __init__(self, task_manager: ModuleTaskManager, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)
        self.setModel(task_manager)
        # Set delegates
        self._arguments_delegate = TaskArgumentsDelegate()
        self._state_delegate = TaskStateDelegate()
        self._result_delegate = TaskResultDelegate()
        self.setItemDelegateForColumn(0, self._arguments_delegate)
        self.setItemDelegateForColumn(1, self._state_delegate)
        self.setItemDelegateForColumn(2, self._result_delegate)
        # Set column size and resize policy
        self.resizeRowsToContents()
        self.resizeColumnsToContents()
        self.horizontalHeader().setMinimumWidth(
            self.horizontalHeader().sectionSize(0) +
            self.horizontalHeader().sectionSize(1) +
            self.horizontalHeader().sectionSize(2)
        )
        self.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.setMinimumWidth(self.width())
        self.setMinimumHeight(
            self.horizontalHeader().height() +
            max(self._arguments_delegate.sizeHint().height(),
                self._state_delegate.sizeHint().height(),
                self._result_delegate.sizeHint().height())
        )
        # Ensure editing upon mouse hover works
        self.setMouseTracking(True)
        self.entered.connect(self._index_entered_callback)
        self.__edited_index = QtCore.QModelIndex()

    def _index_entered_callback(self, index: QtCore.QModelIndex) -> None:
        if self.__edited_index != index:
            if self.__edited_index.isValid():
                self.closePersistentEditor(self.__edited_index)
                self.__edited_index = QtCore.QModelIndex()
            if index.isValid() and (0 <= index.column() <= 1):
                self.setCurrentIndex(index)
                self.openPersistentEditor(index)
                self.__edited_index = index

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        if self.__edited_index.isValid():
            self.closePersistentEditor(self.__edited_index)
            self.__edited_index = QtCore.QModelIndex()
        super().leaveEvent(event)
