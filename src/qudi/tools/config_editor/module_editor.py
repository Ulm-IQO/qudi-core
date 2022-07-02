# -*- coding: utf-8 -*-

"""
QWidgets serving as editors for the individual module config sections

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

import copy
import os
from PySide2 import QtCore, QtGui, QtWidgets
from typing import Optional, Iterable, Mapping, Dict, Sequence, Union, Any, Tuple
from qudi.core import Connector, ConfigOption
from qudi.util.paths import get_artwork_dir
from qudi.util.widgets.lines import HorizontalLine
from qudi.tools.config_editor.module_finder import QudiModules
from qudi.tools.config_editor.custom_widgets import CustomOptionsWidget, CustomConnectorsWidget


class ModuleEditorWidget(QtWidgets.QWidget):
    """
    """
    sigModuleConfigFinished = QtCore.Signal(str, dict, dict, dict)

    _add_icon_path = os.path.join(get_artwork_dir(), 'icons', 'list-add')
    _remove_icon_path = os.path.join(get_artwork_dir(), 'icons', 'list-remove')

    def __init__(self, qudi_modules: QudiModules, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)
        self.setLayout(layout)

        self.placeholder_label = QtWidgets.QLabel(
            'Please select a module to configure from the module tree.'
        )
        font = self.placeholder_label.font()
        font.setBold(True)
        font.setPointSize(10)
        self.placeholder_label.setFont(font)
        self.placeholder_label.setAlignment(QtCore.Qt.AlignCenter)
        self.placeholder_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                             QtWidgets.QSizePolicy.Expanding)
        layout.addWidget(self.placeholder_label)

        self._qudi_modules = qudi_modules
        self._current_editor = None

    def open_module_editor(self,
                           module: str,
                           config: Optional[Dict[str, Dict[str, Union[str, bool, Dict[str, str], Dict[str, Any]]]]] = None,
                           named_modules: Optional[Mapping[str, str]] = None
                           ) -> None:
        if self._current_editor is not None:
            self.close_module_editor()

        editor = LocalModuleConfigurationWidget(module=module,
                                                qudi_modules=self._qudi_modules,
                                                named_modules=named_modules)
        editor.set_config(config)
        layout = self.layout()
        self.placeholder_label.hide()
        layout.addWidget(editor)
        self._current_editor = editor

    def close_module_editor(self):
        if self._current_editor is None:
            return
        layout = self.layout()
        layout.removeWidget(self._current_editor)
        self.placeholder_label.show()
        self._current_editor.setParent(None)
        self._current_editor.deleteLater()
        self._current_editor = None
