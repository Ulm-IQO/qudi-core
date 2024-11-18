# -*- coding: utf-8 -*-

"""
QWidget serving as editor for the default global configuration section

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

__all__ = ['GlobalConfigWidget', 'GlobalOptionsWidget', 'RemoteServerWidget', 'CustomOptionsWidget']

from typing import Dict, Union, Mapping, Optional, Any
from PySide2 import QtCore, QtWidgets

from qudi.util.widgets.separator_lines import HorizontalLine
from qudi.util.widgets.path_line_edit import PathLineEdit
from qudi.tools.config_editor.custom_widgets import CustomOptionsWidget
from qudi.core.config.schema import config_schema


class RemoteServerWidget(QtWidgets.QWidget):
    """ Remote modules server configuration editor widget.
    """
    def __init__(self,
                 config: Optional[Mapping[str, Union[int, str]]] = None,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)

        # Create main layout
        layout = QtWidgets.QGridLayout()
        layout.setColumnStretch(1, 1)
        self.setLayout(layout)

        # server enable flag
        label = QtWidgets.QLabel('Remote modules server:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.enable_checkbox = QtWidgets.QCheckBox()
        self.enable_checkbox.setChecked(True)
        self.enable_checkbox.setToolTip(
            'Whether qudi should start a remote modules server at all.\nYou will not be able to '
            'communicate with remote qudi instances if this is disabled.'
        )
        self.enable_checkbox.toggled.connect(self._toggle_editors)
        layout.addWidget(label, 0, 0)
        layout.addWidget(self.enable_checkbox, 0, 1)

        # Create server config editors in their own layout
        self._server_layout = QtWidgets.QGridLayout()
        self._server_layout.setColumnStretch(1, 1)
        layout.addLayout(self._server_layout, 1, 0, 1, 2)
        label = QtWidgets.QLabel('Host address:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.host_lineedit = QtWidgets.QLineEdit()
        self.host_lineedit.setToolTip(
            'The host address to share qudi modules with other qudi instances'
        )
        self._server_layout.addWidget(label, 0, 0)
        self._server_layout.addWidget(self.host_lineedit, 0, 1)

        label = QtWidgets.QLabel('Port:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.port_spinbox = QtWidgets.QSpinBox()
        self.port_spinbox.setToolTip('Port number for the remote modules server to bind to')
        self.port_spinbox.setRange(0, 65535)
        self.port_spinbox.setValue(12345)
        self._server_layout.addWidget(label, 1, 0)
        self._server_layout.addWidget(self.port_spinbox, 1, 1)

        label = QtWidgets.QLabel('Certificate file:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.certfile_lineedit = PathLineEdit(dialog_caption='Select SSL Certificate File',
                                              follow_symlinks=True)
        self.certfile_lineedit.setPlaceholderText('No certificate')
        self.certfile_lineedit.setToolTip('SSL certificate file path for the remote module server')
        self._server_layout.addWidget(label, 2, 0)
        self._server_layout.addWidget(self.certfile_lineedit, 2, 1)

        label = QtWidgets.QLabel('Key file:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.keyfile_lineedit = PathLineEdit(dialog_caption='Select SSL Key File',
                                             follow_symlinks=True)
        self.keyfile_lineedit.setPlaceholderText('No key')
        self.keyfile_lineedit.setToolTip('SSL key file path for the remote module server')
        self._server_layout.addWidget(label, 3, 0)
        self._server_layout.addWidget(self.keyfile_lineedit, 3, 1)

        self.set_config(config)

    @property
    def config(self) -> Union[None, Dict[str, Union[int, str]]]:
        if self.enable_checkbox.isChecked():
            host = self.host_lineedit.text().strip()
            cfg = {'address': host if host else 'localhost',
                   'port'   : self.port_spinbox.value()}
            try:
                cfg['certfile'] = self.certfile_lineedit.paths[0]
            except IndexError:
                pass
            try:
                cfg['keyfile'] = self.keyfile_lineedit.paths[0]
            except IndexError:
                pass

            return cfg
        return None

    def set_config(self, config: Union[None, Mapping[str, Union[None, int, str]]]) -> None:
        if config is None:
            self.enable_checkbox.setChecked(False)
        else:
            self.enable_checkbox.setChecked(True)
            host = config.get('address', None)
            port = config.get('port', None)
            certfile = config.get('certfile', None)
            keyfile = config.get('keyfile', None)
            if host is None:
                host = 'localhost'
            if port is None:
                port = 12345
            if certfile is None or keyfile is None:
                certfile = keyfile = ''
            self.host_lineedit.setText(host)
            self.port_spinbox.setValue(port)
            self.certfile_lineedit.setText(certfile)
            self.keyfile_lineedit.setText(keyfile)

    @QtCore.Slot(bool)
    def _toggle_editors(self, enabled: bool) -> None:
        widget_iterator = (
            self._server_layout.itemAt(ii).widget() for ii in range(self._server_layout.count())
        )
        for widget in widget_iterator:
            widget.setVisible(enabled)


class GlobalOptionsWidget(QtWidgets.QWidget):
    """
    """

    def __init__(self,
                 config: Optional[Mapping[str, Any]] = None,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)

        # Create main layout
        layout = QtWidgets.QGridLayout()
        layout.setColumnStretch(1, 1)
        self.setLayout(layout)

        # Create module server editor
        self.remote_server_editor = RemoteServerWidget()
        layout.addWidget(self.remote_server_editor, 0, 0, 1, 2)

        # Add separator
        layout.addWidget(HorizontalLine(), 1, 0, 1, 2)

        # Create local module server port editor
        label = QtWidgets.QLabel('Namespace server port:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.namespace_port_spinbox = QtWidgets.QSpinBox()
        self.namespace_port_spinbox.setToolTip('Port number for the local namespace server')
        self.namespace_port_spinbox.setRange(0, 65535)
        layout.addWidget(label, 2, 0)
        layout.addWidget(self.namespace_port_spinbox, 2, 1)

        # Create flag editor to enforce remote calls by value
        label = QtWidgets.QLabel('Force remote calls by value:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.force_calls_by_value_checkbox = QtWidgets.QCheckBox()
        self.force_calls_by_value_checkbox.setToolTip(
            'Will force all arguments from remote calls to qudi API methods to pass by value\n'
            '(serialized -> sent to qudi -> de-serialized).'
        )
        layout.addWidget(label, 3, 0)
        layout.addWidget(self.force_calls_by_value_checkbox, 3, 1)

        # Create flag editor to hide manager window upon startup
        label = QtWidgets.QLabel('Hide manager window:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.hide_manager_window_checkbox = QtWidgets.QCheckBox()
        self.hide_manager_window_checkbox.setToolTip(
            'Whether to suppress the qudi module manager window at startup.'
        )
        layout.addWidget(label, 4, 0)
        layout.addWidget(self.hide_manager_window_checkbox, 4, 1)

        # Create flag editor to auomatically create a data sub-directory for each day
        label = QtWidgets.QLabel('Create daily data directories:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.daily_data_dirs_checkbox = QtWidgets.QCheckBox()
        self.daily_data_dirs_checkbox.setToolTip(
            'Whether to automatically create daily sub-directories in the data directory for file '
            'based data storage facilities'
        )
        layout.addWidget(label, 5, 0)
        layout.addWidget(self.daily_data_dirs_checkbox, 5, 1)

        # Create default data path editor
        label = QtWidgets.QLabel('Default data directory:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.data_directory_lineedit = PathLineEdit(dialog_caption='Select Default Data Directory',
                                                    select_directory=True)
        self.data_directory_lineedit.setPlaceholderText('Default "<UserHome>/qudi/Data/"')
        self.data_directory_lineedit.setToolTip('Default data directory for qudi modules to save '
                                                'measurement data into.')
        layout.addWidget(label, 6, 0)
        layout.addWidget(self.data_directory_lineedit, 6, 1)

        # Create startup modules editor
        label = QtWidgets.QLabel('Startup Modules:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.startup_lineedit = QtWidgets.QLineEdit()
        self.startup_lineedit.setPlaceholderText('No startup modules')
        self.startup_lineedit.setToolTip('Modules to be automatically activated on qudi startup.\n'
                                         'Separate multiple module names with commas.')
        layout.addWidget(label, 7, 0)
        layout.addWidget(self.startup_lineedit, 7, 1)

        # Create stylesheet file path editor
        label = QtWidgets.QLabel('Stylesheet:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.stylesheet_lineedit = PathLineEdit(dialog_caption='Select QSS Stylesheet',
                                                filters='Stylesheets (*.qss)',
                                                follow_symlinks=True)
        self.stylesheet_lineedit.setPlaceholderText('Platform dependent Qt default')
        self.stylesheet_lineedit.setToolTip(
            'File path for qudi QSS stylesheet to use.\nIf just a file name is given, the file '
            'must be found in the qudi artwork resources.'
        )
        layout.addWidget(label, 8, 0)
        layout.addWidget(self.stylesheet_lineedit, 8, 1)

        # Get default config from JSON schema
        global_props = config_schema()['properties']['global']['properties']
        self._config_defaults = {
            name: prop.get('default', None) for name, prop in global_props.items()
        }
        # Fixme: Remove deprecated option manually
        del self._config_defaults['extension_paths']

        self.set_config(config)

    @property
    def config(self) -> Dict[str, Any]:
        config = {
            'remote_modules_server'      : self.remote_server_editor.config,
            'namespace_server_port'      : self.namespace_port_spinbox.value(),
            'force_remote_calls_by_value': self.force_calls_by_value_checkbox.isChecked(),
            'hide_manager_window'        : self.hide_manager_window_checkbox.isChecked(),
            'daily_data_dirs'            : self.daily_data_dirs_checkbox.isChecked(),
            'startup_modules'            : [mod.strip() for mod in
                                            self.startup_lineedit.text().split(',') if mod.strip()],
        }
        try:
            config['default_data_dir'] = self.data_directory_lineedit.paths[0]
        except IndexError:
            config['default_data_dir'] = self._config_defaults['default_data_dir']
        try:
            config['stylesheet'] = self.stylesheet_lineedit.paths[0]
        except IndexError:
            config['stylesheet'] = self._config_defaults['stylesheet']
        return config

    def set_config(self, config: Union[None, Mapping[str, Any]]):
        if config is None:
            config = dict()
        config = {
            name: config.get(name, default) for name, default in self._config_defaults.items()
        }

        self.remote_server_editor.set_config(config['remote_modules_server'])
        self.namespace_port_spinbox.setValue(config['namespace_server_port'])
        self.force_calls_by_value_checkbox.setChecked(config['force_remote_calls_by_value'])
        self.hide_manager_window_checkbox.setChecked(config['hide_manager_window'])
        self.daily_data_dirs_checkbox.setChecked(config['daily_data_dirs'])
        default_data_dir = config['default_data_dir']
        self.data_directory_lineedit.setText('' if default_data_dir is None else default_data_dir)
        stylesheet = config['stylesheet']
        self.stylesheet_lineedit.setText('' if stylesheet is None else stylesheet)
        self.startup_lineedit.setText(','.join(config['startup_modules']))


class GlobalConfigWidget(QtWidgets.QWidget):
    """
    """

    def __init__(self,
                 config: Optional[Mapping[str, Any]] = None,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)

        # Create main layout
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Create Caption
        label = QtWidgets.QLabel('Global Configuration')
        label.setAlignment(QtCore.Qt.AlignCenter)
        font = label.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 4)
        label.setFont(font)
        layout.addWidget(label)

        # Create default config editor
        self.default_options_widget = GlobalOptionsWidget()
        layout.addWidget(self.default_options_widget)

        # Remember default global config option names
        self._default_option_names = frozenset(self.default_options_widget.config)

        # Add separator
        layout.addWidget(HorizontalLine())

        # Create custom option editor
        self.custom_options_widget = CustomOptionsWidget(forbidden_names=self._default_option_names)
        layout.addWidget(self.custom_options_widget)

        layout.addStretch(1)

        self.set_config(config)

    @property
    def config(self) -> Dict[str, Any]:
        config = self.default_options_widget.config
        config.update(self.custom_options_widget.config)
        return config

    def set_config(self, config: Union[None, Mapping[str, Any]]) -> None:
        if config is None:
            self.default_options_widget.set_config(None)
            self.custom_options_widget.set_config(None)
        else:
            default_config = {name: value for name, value in config.items() if
                              name in self._default_option_names}
            custom_config = {name: value for name, value in config.items() if
                             name not in self._default_option_names}
            self.default_options_widget.set_config(default_config)
            self.custom_options_widget.set_config(custom_config)
