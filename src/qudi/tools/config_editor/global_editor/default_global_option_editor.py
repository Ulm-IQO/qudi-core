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

__all__ = ['DefaultGlobalConfigurationWidget']

from typing import Dict, Union, Mapping, List
from PySide2 import QtCore, QtWidgets
from qudi.util.widgets.lines import HorizontalLine
from qudi.util.widgets.path_line_edit import PathLineEdit
from qudi.tools.config_editor.global_editor.remote_server_editor import RemoteServerConfigurationWidget


class DefaultGlobalConfigurationWidget(QtWidgets.QWidget):
    """
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create main layout
        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Create module server editor
        self.remote_server_editor = RemoteServerConfigurationWidget()
        layout.addWidget(self.remote_server_editor, 0, 0, 1, 2)

        # Add separator
        layout.addWidget(HorizontalLine(), 1, 0, 1, 2)

        # Create local module server port editor
        label = QtWidgets.QLabel('Namespace server port:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.namespace_port_spinbox = QtWidgets.QSpinBox()
        self.namespace_port_spinbox.setToolTip('Port number for the local namespace server')
        self.namespace_port_spinbox.setRange(0, 65535)
        self.namespace_port_spinbox.setValue(18861)
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
        self.force_calls_by_value_checkbox.setChecked(True)
        layout.addWidget(label, 3, 0)
        layout.addWidget(self.force_calls_by_value_checkbox, 3, 1)

        # Create flag editor to hide manager window upon startup
        label = QtWidgets.QLabel('Hide manager window:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.hide_manager_window_checkbox = QtWidgets.QCheckBox()
        self.hide_manager_window_checkbox.setToolTip(
            'Whether to suppress the qudi module manager window at startup.'
        )
        self.hide_manager_window_checkbox.setChecked(False)
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
        self.daily_data_dirs_checkbox.setChecked(True)
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
        self.stylesheet_lineedit = PathLineEdit('qdark.qss',
                                                dialog_caption='Select QSS Stylesheet',
                                                filters='Stylesheets (*.qss)',
                                                follow_symlinks=True)
        self.stylesheet_lineedit.setPlaceholderText('Platform dependent Qt default')
        self.stylesheet_lineedit.setToolTip(
            'File path for qudi QSS stylesheet to use.\nIf just a file name is given, the file '
            'must be found in the qudi artwork resources.'
        )
        layout.addWidget(label, 8, 0)
        layout.addWidget(self.stylesheet_lineedit, 8, 1)

    @property
    def option_names(self) -> List[str]:
        return ['remote_modules_server',
                'namespace_server_port',
                'force_remote_calls_by_value',
                'hide_manager_window',
                'daily_data_dirs',
                'startup_modules',
                'default_data_dir',
                'stylesheet']

    @property
    def config(self) -> Dict[str, Union[None, str, int, bool, float]]:
        config = {'remote_modules_server'      : self.remote_server_editor.config,
                  'namespace_server_port'      : self.namespace_port_spinbox.value(),
                  'force_remote_calls_by_value': self.force_calls_by_value_checkbox.isChecked(),
                  'hide_manager_window'        : self.hide_manager_window_checkbox.isChecked(),
                  'daily_data_dirs'            : self.daily_data_dirs_checkbox.isChecked(),
                  'startup_modules'            : [mod.strip() for mod in
                                                  self.startup_lineedit.text().strip().split(',') if
                                                  mod.strip()]}
        try:
            config['default_data_dir'] = self.data_directory_lineedit.paths[0]
        except IndexError:
            config['default_data_dir'] = None
        try:
            config['stylesheet'] = self.stylesheet_lineedit.paths[0]
        except IndexError:
            pass
        return config

    def set_config(self, config: Union[None, Mapping[str, Union[None, str, int, bool, float]]]):
        if config is None:
            config = dict()
        self.remote_server_editor.set_config(config.get('remote_modules_server', None))
        self.namespace_port_spinbox.setValue(config.get('namespace_server_port', 18861))
        self.force_calls_by_value_checkbox.setChecked(
            config.get('force_remote_calls_by_value', True)
        )
        self.hide_manager_window_checkbox.setChecked(config.get('hide_manager_window', False))
        self.daily_data_dirs_checkbox.setChecked(config.get('daily_data_dirs', True))
        default_data_dir = config.get('default_data_dir', None)
        self.data_directory_lineedit.setText('' if default_data_dir is None else default_data_dir)
        stylesheet = config.get('stylesheet', None)
        self.stylesheet_lineedit.setText('qdark.qss' if stylesheet is None else stylesheet)
        self.startup_lineedit.setText(','.join(config.get('startup_modules', list())))
