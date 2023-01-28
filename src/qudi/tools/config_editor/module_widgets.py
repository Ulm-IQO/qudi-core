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

__all__ = ['LocalModuleConfigWidget', 'RemoteModuleConfigWidget', 'ModuleConnectorsWidget',
           'ModuleOptionsWidget']

import copy
from PySide6 import QtCore, QtWidgets
from typing import Optional, Iterable, Mapping, Dict, Sequence, Union, Any, Tuple, List

from qudi.core import Connector, ConfigOption
from qudi.core.config.validator import validate_remote_module_config, validate_local_module_config
from qudi.core.config.validator import ValidationError
from qudi.util.widgets.separator_lines import HorizontalLine
from qudi.util.widgets.path_line_edit import PathLineEdit
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
        layout.setColumnStretch(1, 1)
        self.setLayout(layout)

        # Create Caption
        label = QtWidgets.QLabel('Connectors')
        label.setAlignment(QtCore.Qt.AlignCenter)
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label, 0, 0, 1, 2)

        # Keep track of connector editor widgets
        self._connector_editors = dict()
        # Create mandatory connectors
        for row, (name, targets) in enumerate(self._mandatory_targets.items(), 1):
            label, editor = self._make_conn_widgets(name, targets, False)
            layout.addWidget(label, row, 0)
            layout.addWidget(editor, row, 1)
            self._connector_editors[name] = editor
        # Create optional connectors
        offset = len(self._connector_editors) + 1
        for row, (name, targets) in enumerate(self._optional_targets.items(), offset):
            label, editor = self._make_conn_widgets(name, targets, True)
            layout.addWidget(label, row, 0)
            layout.addWidget(editor, row, 1)
            self._connector_editors[name] = editor

        # Add separator
        layout.addWidget(HorizontalLine(), len(self._connector_editors) + 1, 0, 1, 2)

        # Create custom connector editor
        self.custom_connectors_widget = CustomConnectorsWidget(
            forbidden_names=list(self._connector_editors),
            module_names=module_names
        )
        layout.addWidget(self.custom_connectors_widget, len(self._connector_editors) + 2, 0, 1, 2)

        layout.setRowStretch(len(self._connector_editors) + 3, 1)

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
        label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        label.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
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
        layout.setColumnStretch(1, 1)
        self.setLayout(layout)

        # Create Caption
        label = QtWidgets.QLabel('ConfigOptions')
        label.setAlignment(QtCore.Qt.AlignCenter)
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label, 0, 0, 1, 2)

        # Keep track of option editor widgets
        self._option_editors = dict()
        # Create mandatory options
        for row, name in enumerate(self._mandatory_names, 1):
            label, editor = self._make_option_widgets(name, False)
            layout.addWidget(label, row, 0)
            layout.addWidget(editor, row, 1)
            self._option_editors[name] = editor
        # Create optional options
        offset = len(self._option_editors) + 1
        for row, name in enumerate(self._optional_names, offset):
            label, editor = self._make_option_widgets(name, True)
            layout.addWidget(label, row, 0)
            layout.addWidget(editor, row, 1)
            self._option_editors[name] = editor

        # Add separator
        layout.addWidget(HorizontalLine(), len(self._option_editors) + 1, 0, 1, 2)

        # Create custom options editor
        self.custom_options_widget = CustomOptionsWidget(forbidden_names=list(self._option_editors))
        layout.addWidget(self.custom_options_widget, len(self._option_editors) + 2, 0, 1, 2)

        layout.setRowStretch(len(self._option_editors) + 3, 1)

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
        label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        label.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        editor = QtWidgets.QLineEdit()
        editor.setPlaceholderText('text parsed by eval()')
        return label, editor


class LocalModuleConfigWidget(QtWidgets.QWidget):
    """
    """

    def __init__(self,
                 module_class: str,
                 config_options: Sequence[ConfigOption],
                 connectors: Sequence[Connector],
                 valid_connector_targets: Mapping[str, Sequence[str]],
                 named_modules: Mapping[str, str],
                 config: Optional[Dict[str, Union[str, bool, Dict[str, str], Dict[str, Any]]]] = None,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setStretch(2, 1)
        self.setLayout(layout)

        # Module label
        sub_layout = QtWidgets.QGridLayout()
        sub_layout.setColumnStretch(1, 1)
        layout.addLayout(sub_layout)
        label = QtWidgets.QLabel('module.Class:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self._module_label = QtWidgets.QLabel(module_class)
        font = self._module_label.font()
        font.setBold(True)
        self._module_label.setFont(font)
        sub_layout.addWidget(label, 0, 0)
        sub_layout.addWidget(self._module_label, 0, 1)
        # allow_remote flag editor
        label = QtWidgets.QLabel('Allow remote connection:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.allow_remote_checkbox = QtWidgets.QCheckBox()
        self.allow_remote_checkbox.setToolTip(
            'Allow other qudi instances to connect to this module via remote modules server.'
        )
        self.allow_remote_checkbox.toggled.connect(self._validate_and_mark_config)
        sub_layout.addWidget(label, 1, 0)
        sub_layout.addWidget(self.allow_remote_checkbox, 1, 1)

        # Separator
        layout.addWidget(HorizontalLine())

        # Create splitter to spread options and connectors horizontally
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                    QtWidgets.QSizePolicy.Expanding)
        layout.addWidget(self.splitter)
        # Module Connectors editor
        mandatory_targets, optional_targets = self._get_connector_targets(
            connectors=connectors,
            named_modules=named_modules,
            valid_targets=valid_connector_targets
        )
        self.connectors_editor = ModuleConnectorsWidget(mandatory_targets=mandatory_targets,
                                                        optional_targets=optional_targets,
                                                        module_names=list(named_modules))
        self.splitter.addWidget(self.connectors_editor)
        # Module ConfigOptions editor
        self.options_editor = ModuleOptionsWidget(
            mandatory_names=[opt.name for opt in config_options if not opt.optional],
            optional_names=[opt.name for opt in config_options if opt.optional]
        )
        self.splitter.addWidget(self.options_editor)

        self.set_config(config)
        self._validate_and_mark_config()

    @property
    def module_class(self) -> str:
        return self._module_label.text()

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

    @staticmethod
    def _get_connector_targets(connectors: Sequence[Connector],
                               named_modules: Mapping[str, str],
                               valid_targets: Mapping[str, Sequence[str]]
                               ) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        mandatory_targets = dict()
        optional_targets = dict()
        for conn in connectors:
            targets = [
                name for name, mod in named_modules.items() if mod in valid_targets[conn.name]
            ]
            if conn.optional:
                optional_targets[conn.name] = targets
            else:
                mandatory_targets[conn.name] = targets
        return mandatory_targets, optional_targets

    def validate_config(self) -> None:
        validate_local_module_config(self.config)

    @QtCore.Slot()
    def _validate_and_mark_config(self) -> None:
        try:
            self.validate_config()
        except ValidationError as err:
            print(f'Invalid local module config. Problematic fields: {list(err.relative_path)}')


class RemoteModuleConfigWidget(QtWidgets.QWidget):
    """
    """

    def __init__(self,
                 config: Optional[Mapping[str, Union[str, None]]] = None,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)

        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(5, 1)
        self.setLayout(layout)

        # remote name editor
        label = QtWidgets.QLabel('* Native module name:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.native_name_lineedit = QtWidgets.QLineEdit()
        self.native_name_lineedit.setToolTip('The native module name as configured on the remote '
                                             'host qudi instance to connect to.')
        self.native_name_lineedit.setPlaceholderText('Module name on remote host')
        self.native_name_lineedit.textChanged.connect(self._validate_and_mark_config)
        layout.addWidget(label, 0, 0)
        layout.addWidget(self.native_name_lineedit, 0, 1)

        # remote host editor
        label = QtWidgets.QLabel('* Remote address:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.remote_host_lineedit = QtWidgets.QLineEdit('localhost')
        self.remote_host_lineedit.setToolTip('The IP address of the remote host. Can also be '
                                             '"localhost" for local qudi instances.')
        self.remote_host_lineedit.setPlaceholderText('IP address or "localhost"')
        self.remote_host_lineedit.textChanged.connect(self._validate_and_mark_config)
        layout.addWidget(label, 1, 0)
        layout.addWidget(self.remote_host_lineedit, 1, 1)

        # remote port editor
        label = QtWidgets.QLabel('* Remote port:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.remote_port_spinbox = QtWidgets.QSpinBox()
        self.remote_port_spinbox.setRange(0, 65535)
        self.remote_port_spinbox.setValue(12345)
        self.remote_port_spinbox.setToolTip('Port to reach the remote host on.')
        self.remote_port_spinbox.valueChanged.connect(self._validate_and_mark_config)
        layout.addWidget(label, 2, 0)
        layout.addWidget(self.remote_port_spinbox, 2, 1)

        # certfile editor
        label = QtWidgets.QLabel('Certificate file:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.certfile_lineedit = PathLineEdit(dialog_caption='Select SSL Certificate File',
                                              follow_symlinks=True)
        self.certfile_lineedit.setPlaceholderText('No certificate')
        self.certfile_lineedit.setToolTip(
            'SSL certificate file path for the remote module connection'
        )
        self.certfile_lineedit.textChanged.connect(self._validate_and_mark_config)
        layout.addWidget(label, 3, 0)
        layout.addWidget(self.certfile_lineedit, 3, 1)

        # keyfile editor
        label = QtWidgets.QLabel('Key file:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.keyfile_lineedit = PathLineEdit(dialog_caption='Select SSL Key File',
                                             follow_symlinks=True)
        self.keyfile_lineedit.setPlaceholderText('No key')
        self.keyfile_lineedit.setToolTip('SSL key file path for the remote module server')
        self.keyfile_lineedit.textChanged.connect(self._validate_and_mark_config)
        layout.addWidget(label, 4, 0)
        layout.addWidget(self.keyfile_lineedit, 4, 1)

        self.set_config(config)
        self._validate_and_mark_config()

    @property
    def config(self) -> Dict[str, Union[None, int, str]]:
        native_module_name = self.native_name_lineedit.text()
        host = self.remote_host_lineedit.text()
        cfg = {'native_module_name': native_module_name if native_module_name else None,
               'address'           : host if host else None,
               'port'              : self.remote_port_spinbox.value()}
        try:
            cfg['certfile'] = self.certfile_lineedit.paths[0]
        except IndexError:
            pass
        try:
            cfg['keyfile'] = self.keyfile_lineedit.paths[0]
        except IndexError:
            pass
        return cfg

    def set_config(self, config: Union[None, Dict[str, Union[None, int, str]]]) -> None:
        if config:
            native_module_name = config.get('native_module_name', None)
            host = config.get('address', None)
            port = config.get('port', None)
            try:
                certfile = config['certfile']
                keyfile = config['keyfile']
            except KeyError:
                certfile = keyfile = ''
            if certfile is None or keyfile is None:
                certfile = keyfile = ''
            self.remote_host_lineedit.setText(host if host else '')
            self.remote_port_spinbox.setValue(port if isinstance(port, int) else 12345)
            self.native_name_lineedit.setText(native_module_name if native_module_name else '')
            self.certfile_lineedit.setText(certfile)
            self.certfile_lineedit.setText(keyfile)
        else:
            self.remote_host_lineedit.setText('')
            self.remote_port_spinbox.setValue(12345)
            self.native_name_lineedit.setText('')
            self.certfile_lineedit.setText('')
            self.certfile_lineedit.setText('')

    def validate_config(self) -> None:
        validate_remote_module_config(self.config)

    @QtCore.Slot()
    def _validate_and_mark_config(self) -> None:
        try:
            self.validate_config()
        except ValidationError as err:
            print(f'Invalid remote module config. Problematic fields: {list(err.relative_path)}')
