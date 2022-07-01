# -*- coding: utf-8 -*-

"""
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

__all__ = ['GlobalConfigurationWidget']

from typing import Dict, Union, Mapping
from PySide2 import QtCore, QtWidgets
from qudi.util.widgets.lines import HorizontalLine
from qudi.tools.config_editor.custom_option_editor import CustomOptionConfigurationWidget
from qudi.tools.config_editor.global_editor.default_global_option_editor import DefaultGlobalConfigurationWidget
from qudi.core.config.schema import config_schema


class GlobalConfigurationWidget(QtWidgets.QWidget):
    """
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create main layout
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Create header
        header = QtWidgets.QLabel('Global Configuration')
        header.setAlignment(QtCore.Qt.AlignCenter)
        font = header.font()
        font.setBold(True)
        font.setPointSize(10)
        header.setFont(font)
        layout.addWidget(header)

        # Create default config editor
        self.default_config_editor = DefaultGlobalConfigurationWidget()
        layout.addWidget(self.default_config_editor)

        # Add separator
        layout.addWidget(HorizontalLine())

        # Create custom option editor
        self.custom_options_editor = CustomOptionConfigurationWidget(
            forbidden_names=list(config_schema()['properties']['global']['properties'])
        )
        layout.addWidget(self.custom_options_editor)

        layout.addStretch(1)

    @property
    def config(self) -> Dict[str, Union[None, str, int, bool, float]]:
        config = self.default_config_editor.config
        config.update(self.custom_options_editor.options)
        return config

    def set_config(self, config: Union[None, Mapping[str, Union[None, str, int, bool, float]]]):
        if config is None:
            self.default_config_editor.set_config(None)
            self.custom_options_editor.set_options(None)
        else:
            default_config = {name: value for name, value in config.items() if
                              name in self.default_config_editor.option_names}
            custom_config = {
                name: value for name, value in config.items() if name not in default_config
            }
            self.default_config_editor.set_config(default_config)
            self.custom_options_editor.set_options(custom_config)
