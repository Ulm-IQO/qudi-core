# -*- coding: utf-8 -*-

"""
QWidget serving as main editor for the global configuration section

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

__all__ = ['GlobalEditorWidget']

from PySide6 import QtCore, QtWidgets
from typing import Optional, Mapping, Dict, Union, Any
from qudi.tools.config_editor.global_widgets import GlobalConfigWidget


class GlobalEditorWidget(QtWidgets.QStackedWidget):
    """
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent=parent)

        self.placeholder_label = QtWidgets.QLabel('Please load configuration from file\n'
                                                  'or create a new one.')
        font = self.placeholder_label.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 4)
        self.placeholder_label.setFont(font)
        self.placeholder_label.setAlignment(QtCore.Qt.AlignCenter)
        self.placeholder_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                             QtWidgets.QSizePolicy.Expanding)
        self.addWidget(self.placeholder_label)

        self.global_editor_widget = GlobalConfigWidget()
        self.addWidget(self.global_editor_widget)

        self.setCurrentIndex(0)

    @property
    def config(self) -> Union[None, Dict[str, Any]]:
        if self.currentIndex() == 0:
            return None
        else:
            return self.global_editor_widget.config

    def set_config(self, config: Union[None, Dict[str, Any]]) -> None:
        self.global_editor_widget.set_config(config)

    def open_editor(self, config: Union[None, Mapping[str, Any]]) -> None:
        self.global_editor_widget.set_config(config)
        self.setCurrentIndex(1)

    def close_editor(self):
        self.setCurrentIndex(0)
