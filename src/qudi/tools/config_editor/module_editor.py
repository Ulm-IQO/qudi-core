# -*- coding: utf-8 -*-

"""
QWidget serving as main editor for the individual module config sections

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

__all__ = ['ModuleEditorWidget']

from PySide6 import QtCore, QtWidgets
from typing import Optional, Mapping, Dict, Union, Any
from qudi.util.widgets.separator_lines import HorizontalLine
from qudi.tools.config_editor.module_finder import QudiModules
from qudi.tools.config_editor.module_widgets import LocalModuleConfigWidget
from qudi.tools.config_editor.module_widgets import RemoteModuleConfigWidget


class ModuleEditorWidget(QtWidgets.QStackedWidget):
    """
    """

    sigModuleRenamed = QtCore.Signal(str)

    def __init__(self,
                 qudi_modules: QudiModules,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)

        assert isinstance(qudi_modules, QudiModules)
        self._qudi_modules = qudi_modules

        self.placeholder_label = QtWidgets.QLabel(
            'Please select a module to configure from the tree view.'
        )
        font = self.placeholder_label.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 4)
        self.placeholder_label.setFont(font)
        self.placeholder_label.setAlignment(QtCore.Qt.AlignCenter)
        self.placeholder_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                             QtWidgets.QSizePolicy.Expanding)
        self.addWidget(self.placeholder_label)

        self._editor_layout = QtWidgets.QVBoxLayout()
        self._editor_layout.setStretch(2, 1)

        # Module name editor
        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.setStretch(1, 1)
        label = QtWidgets.QLabel('* Module Name:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.module_name_lineedit = QtWidgets.QLineEdit()
        self.module_name_lineedit.setPlaceholderText('Enter locally unique module name')
        self.module_name_lineedit.setFont(font)
        self.module_name_lineedit.textChanged.connect(self.sigModuleRenamed)
        sub_layout.addWidget(label)
        sub_layout.addWidget(self.module_name_lineedit)
        self._editor_layout.addLayout(sub_layout)

        # Add separator
        self._editor_layout.addWidget(HorizontalLine())

        editor_widget = QtWidgets.QWidget()
        editor_widget.setLayout(self._editor_layout)
        self.addWidget(editor_widget)

        self._current_editor = None

    @property
    def config(self) -> Union[None, Dict[str, Any]]:
        try:
            return self._current_editor.config
        except AttributeError:
            return None

    def set_config(self, config: Union[None, Dict[str, Any]]) -> None:
        try:
            self._current_editor.set_config(config)
        except AttributeError:
            pass

    @property
    def module_name(self) -> str:
        return self.module_name_lineedit.text()

    def set_module_name(self, name: str) -> None:
        self.module_name_lineedit.blockSignals(True)
        try:
            self.module_name_lineedit.setText(name)
        finally:
            self.module_name_lineedit.blockSignals(False)

    def open_remote_module(self,
                           name: Optional[str] = None,
                           config: Optional[Mapping[str, Union[str, None]]] = None
                           ) -> None:
        if self._current_editor is not None:
            self.close_editor()

        self._current_editor = RemoteModuleConfigWidget(config=config)
        self._editor_layout.addWidget(self._current_editor)
        self.set_module_name(name if name else '')
        self.setCurrentIndex(1)

    def open_local_module(self,
                          module_class: str,
                          named_modules: Mapping[str, str],
                          name: Optional[str] = None,
                          config: Optional[Dict[str, Union[str, bool, Dict[str, str], Dict[str, Any]]]] = None,
                          ) -> None:
        if self._current_editor is not None:
            self.close_editor()

        connectors = self._qudi_modules.module_connectors(module_class)
        config_options = self._qudi_modules.module_config_options(module_class)
        valid_connector_targets = self._qudi_modules.module_connector_targets(module_class)
        self._current_editor = LocalModuleConfigWidget(
            module_class=module_class,
            config_options=config_options,
            connectors=connectors,
            valid_connector_targets=valid_connector_targets,
            named_modules=named_modules,
            config=config
        )
        self._editor_layout.addWidget(self._current_editor)
        self.set_module_name(name if name else '')
        self.setCurrentIndex(1)

    def close_editor(self):
        if self._current_editor is None:
            return
        self.setCurrentIndex(0)
        self._editor_layout.removeWidget(self._current_editor)
        self._current_editor.setParent(None)
        self._current_editor.deleteLater()
        self._current_editor = None
