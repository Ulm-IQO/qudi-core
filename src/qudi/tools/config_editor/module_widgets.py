# -*- coding: utf-8 -*-

"""
QWidgets for configuring the individual module config sections

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

__all__ = ['LocalModuleConfigWidget', 'ModuleConnectorsWidget', 'ModuleOptionsWidget']

import copy
from PySide2 import QtCore, QtWidgets
from typing import Optional, Iterable, Mapping, Dict, Sequence, Union, Any, Tuple
from qudi.util.widgets.lines import HorizontalLine
from qudi.tools.config_editor.custom_widgets import CustomOptionsWidget, CustomConnectorsWidget


class ModuleConnectorsWidget(QtWidgets.QWidget):
    """
    """
    def __init__(self,
                 mandatory_targets: Optional[Mapping[str, Sequence[str]]] = None,
                 optional_targets: Optional[Mapping[str, Sequence[str]]] = None,
                 module_names: Optional[Iterable[str]] = None,
                 config: Optional[Mapping[str, str]] = None,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)

        if mandatory_targets is None:
            self._mandatory_targets = dict()
        else:
            self._mandatory_targets = copy.deepcopy(mandatory_targets)
        if optional_targets is None:
            self._optional_targets = dict()
        else:
            self._optional_targets = copy.deepcopy(optional_targets)
        if set(self._mandatory_targets).intersection(self._optional_targets):
            raise ValueError('Connector names can not be both mandatory AND optional')

        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setColumnStretch(1, 1)
        self.setLayout(layout)

        # Keep track of connector editor widgets
        self._connector_editors = dict()
        # Create mandatory connectors
        for row, (name, targets) in enumerate(self._mandatory_targets.items()):
            label, editor = self._make_conn_widgets(name, targets, False)
            layout.addWidget(label, row, 0)
            layout.addWidget(editor, row, 1)
            self._connector_editors[name] = editor
        # Create optional connectors
        offset = len(self._connector_editors)
        for row, (name, targets) in enumerate(self._optional_targets.items(), offset):
            label, editor = self._make_conn_widgets(name, targets, True)
            layout.addWidget(label, row, 0)
            layout.addWidget(editor, row, 1)
            self._connector_editors[name] = editor

        # Add separator
        layout.addWidget(HorizontalLine(), len(self._connector_editors), 0, 1, 2)

        # Create custom connector editor
        self.custom_connectors_widget = CustomConnectorsWidget(
            forbidden_names=list(self._connector_editors),
            module_names=module_names
        )
        layout.addWidget(self.custom_connectors_widget, len(self._connector_editors) + 1, 0, 1, 2)

        self.set_config(config)

    @property
    def config(self) -> Dict[str, Union[None, str]]:
        conn = {name: editor.currentText() for name, editor in self._connector_editors.items()}
        conn.update(self.custom_connectors_widget.config)
        return {name: target if target else None for name, target in conn.items()}

    def set_config(self, config: Union[None, Mapping[str, Union[None, str]]]) -> None:
        if config is None:
            for editor in self._connector_editors.values():
                editor.setCurrentIndex(0)
            self.custom_connectors_widget.set_config(None)
        else:
            cfg = config.copy()
            for name, editor in self._connector_editors.items():
                target = cfg.pop(name, editor.currentText())
                index = max(0, editor.findText(target)) if target else 0
                editor.setCurrentIndex(index)
            # Remaining connectors are custom
            self.custom_connectors_widget.set_config(cfg)

    @staticmethod
    def _make_conn_widgets(name: str,
                           targets: Sequence[str],
                           optional: bool
                           ) -> Tuple[QtWidgets.QLabel, QtWidgets.QComboBox]:
        label = QtWidgets.QLabel(f'{name}:' if optional else f'* {name}:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        editor = QtWidgets.QComboBox()
        editor.addItem('')
        editor.addItems(targets)
        editor.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        return label, editor


class ModuleOptionsWidget(QtWidgets.QWidget):
    """
    """
    def __init__(self,
                 mandatory_names: Optional[Iterable[str]] = None,
                 optional_names: Optional[Iterable[str]] = None,
                 config: Optional[Mapping[str, Any]] = None,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)

        self._mandatory_names = list() if mandatory_names is None else list(mandatory_names)
        self._optional_names = list() if optional_names is None else list(optional_names)
        if set(self._mandatory_names).intersection(self._optional_names):
            raise ValueError('ConfigOption names can not be both mandatory AND optional')

        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setColumnStretch(1, 1)
        self.setLayout(layout)

        # Keep track of option editor widgets
        self._option_editors = dict()
        # Create mandatory options
        for row, name in enumerate(self._mandatory_names):
            label, editor = self._make_option_widgets(name, False)
            layout.addWidget(label, row, 0)
            layout.addWidget(editor, row, 1)
            self._option_editors[name] = editor
        # Create optional options
        offset = len(self._option_editors)
        for row, name in enumerate(self._optional_names, offset):
            label, editor = self._make_option_widgets(name, True)
            layout.addWidget(label, row, 0)
            layout.addWidget(editor, row, 1)
            self._option_editors[name] = editor

        # Add separator
        layout.addWidget(HorizontalLine(), len(self._option_editors), 0, 1, 2)

        # Create custom options editor
        self.custom_options_widget = CustomOptionsWidget(forbidden_names=list(self._option_editors))
        layout.addWidget(self.custom_options_widget, len(self._option_editors) + 1, 0, 1, 2)

        self.set_config(config)

    @property
    def config(self) -> Dict[str, Any]:
        cfg = dict()
        for name, editor in self._option_editors.items():
            text = editor.text().strip()
            if text == '':
                # Interpret empty text as None for mandatory options. Skip missing optional options.
                if name in self._optional_names:
                    continue
                else:
                    cfg[name] = None
            else:
                # Try to parse text with eval(). If that fails, interpret text as plain string.
                try:
                    cfg[name] = eval(text)
                except (NameError, SyntaxError, ValueError):
                    cfg[name] = text
        return cfg

    def set_config(self, config: Union[None, Mapping[str, Any]]) -> None:
        if config is None:
            for editor in self._option_editors.values():
                editor.setText('')
            self.custom_options_widget.set_config(None)
        else:
            cfg = config.copy()
            for name, editor in self._option_editors.items():
                try:
                    editor.setText(repr(cfg.pop(name)))
                except:
                    editor.setText('')
            # Remaining options are custom
            self.custom_options_widget.set_config(cfg)

    @staticmethod
    def _make_option_widgets(name: str,
                             optional: bool
                             ) -> Tuple[QtWidgets.QLabel, QtWidgets.QLineEdit]:
        label = QtWidgets.QLabel(f'{name}:' if optional else f'* {name}:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        editor = QtWidgets.QLineEdit()
        editor.setPlaceholderText('text parsed by eval()')
        return label, editor


class LocalModuleConfigWidget(QtWidgets.QWidget):
    """
    """

    def __init__(self,
                 module_class: str,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)

        self._module_class = module_class

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Create splitter to spread sub-widgets horizontally
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        layout.addWidget(self.splitter)

        # Create layout and widget for left side of splitter
        left_layout = QtWidgets.QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setStretch(1, 1)
        left_widget = QtWidgets.QWidget()
        left_widget.setLayout(left_layout)
        # Caption
        label = QtWidgets.QLabel('Module Connections')
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        label.setAlignment(QtCore.Qt.AlignCenter)
        left_layout.addWidget(label)
        # Module Connectors editor
        self.connectors_editor = ModuleConnectorsWidget()  # Fixme: arguments
        left_layout.addWidget(self.connectors_editor)
        left_layout.addStretch()
        self.splitter.addWidget(left_widget)

        # Create layout and widget for right side of splitter
        right_layout = QtWidgets.QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setStretch(2, 1)
        right_widget = QtWidgets.QWidget()
        right_widget.setLayout(right_layout)
        # Caption
        label = QtWidgets.QLabel('Configuration Options')
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        label.setAlignment(QtCore.Qt.AlignCenter)
        right_layout.addWidget(label)
        # allow_remote flag editor
        label = QtWidgets.QLabel('Allow remote connection:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.allow_remote_checkbox = QtWidgets.QCheckBox()
        self.allow_remote_checkbox.setToolTip(
            'Allow other qudi instances to connect to this module via remote modules server.'
        )
        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.setStretch(1, 1)
        sub_layout.addWidget(label)
        sub_layout.addWidget(self.allow_remote_checkbox)
        right_layout.addLayout(sub_layout)
        # Module ConfigOptions editor
        self.options_editor = ModuleOptionsWidget()  # Fixme: arguments
        right_layout.addWidget(self.options_editor)
        right_layout.addStretch()
        self.splitter.addWidget(right_widget)

    @property
    def module_class(self) -> str:
        return self._module_class

    @property
    def config(self) -> Dict[str, Union[str, bool, Dict[str, str], Dict[str, Any]]]:
        return {'module.Class': self.module_class,
                'allow_remote': self.allow_remote_checkbox.isChecked(),
                'options'     : self.options_editor.config,
                'connect'     : self.connectors_editor.config}

    def set_config(self,
                   config: Union[None, Dict[str, Union[str, bool, Dict[str, str], Dict[str, Any]]]]
                   ) -> None:
        if config:
            self.allow_remote_checkbox.setChecked(config.get('allow_remote', False))
            self.options_editor.set_config(config.get('options', dict()))
            self.connectors_editor.set_config(config.get('connect', dict()))
        else:
            self.allow_remote_checkbox.setChecked(False)
            self.options_editor.set_config(None)
            self.connectors_editor.set_config(None)
