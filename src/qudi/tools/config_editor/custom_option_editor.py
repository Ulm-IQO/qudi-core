# -*- coding: utf-8 -*-

"""
QWidget serving as editor for custom config options.

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

__all__ = ['CustomOptionConfigurationWidget']

import os
from PySide2 import QtCore, QtWidgets, QtGui
from typing import Optional, Mapping, Union, Dict, Iterable

from qudi.util.paths import get_artwork_dir


class CustomOptionConfigurationWidget(QtWidgets.QWidget):
    """
    """
    def __init__(self,
                 forbidden_names: Optional[Iterable[str]] = None,
                 custom_config: Optional[Mapping[str, str]] = None,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)

        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setColumnStretch(2, 1)
        self.setLayout(layout)

        icons_dir = os.path.join(get_artwork_dir(), 'icons')
        self.add_option_button = QtWidgets.QToolButton()
        self.add_option_button.setIcon(QtGui.QIcon(os.path.join(icons_dir, 'list-add')))
        self.add_option_button.setToolTip('Add a custom configuration option with given name.')
        self.add_option_button.clicked.connect(self.add_option)
        self.option_name_lineedit = QtWidgets.QLineEdit()
        self.option_name_lineedit.setPlaceholderText('Enter custom option name')
        layout.addWidget(self.add_option_button, 0, 0, 1, 1)
        layout.addWidget(self.option_name_lineedit, 0, 1, 1, 2)

        # Remove icons reused for each custom option
        self._remove_icon = QtGui.QIcon(os.path.join(icons_dir, 'list-remove'))
        # Keep track of custom option editor widgets
        self._option_widgets = dict()
        # forbidden config option names
        self._forbidden_names = frozenset() if forbidden_names is None else frozenset(
            forbidden_names)

        # Set config if given
        self.set_options(custom_config)

    @property
    def options(self) -> Dict[str, Union[None, Union[None, str, int, float, bool]]]:
        config = {name: widgets[2].text().strip() for name, widgets in self._option_widgets.items()}
        for name, value in config.items():
            if value in ['', 'None', 'null', 'none']:
                config[name] = None
            elif value in ['True', 'true']:
                config[name] = True
            elif value in ['False', 'false']:
                config[name] = False
            else:
                try:
                    config[name] = int(value)
                except (TypeError, ValueError):
                    try:
                        config[name] = float(value)
                    except (TypeError, ValueError):
                        pass
        return config

    def set_options(self,
                    config: Union[None, Mapping[str, Union[None, str, int, float, bool]]]
                    ) -> None:
        self.clear_options()
        if config:
            for name, value in config.items():
                self.add_option(name)
                self._option_widgets[name][2].setText('' if value is None else str(value))

    @QtCore.Slot()
    def add_option(self, name: Optional[str] = None) -> None:
        name = name if isinstance(name, str) else self.option_name_lineedit.text().strip()
        if name and (name not in self._forbidden_names) and (name not in self._option_widgets):
            self.option_name_lineedit.clear()
            label = QtWidgets.QLabel(f'{name}:')
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            editor = QtWidgets.QLineEdit()
            remove_button = QtWidgets.QToolButton()
            remove_button.setIcon(self._remove_icon)
            remove_button.clicked.connect(lambda: self.remove_option(name))
            row = len(self._option_widgets) + 1
            layout = self.layout()
            layout.addWidget(remove_button, row, 0)
            layout.addWidget(label, row, 1)
            layout.addWidget(editor, row, 2)
            self._option_widgets[name] = (remove_button, label, editor)

    def remove_option(self, name: Optional[str] = None) -> None:
        if name not in self._option_widgets:
            return

        layout = self.layout()

        # Remove all widgets from layout
        for button, label, editor in reversed(list(self._option_widgets.values())):
            layout.removeWidget(button)
            layout.removeWidget(label)
            layout.removeWidget(editor)

        # Delete widgets for row to remove
        button, label, editor = self._option_widgets.pop(name)
        button.clicked.disconnect()
        button.setParent(None)
        label.setParent(None)
        editor.setParent(None)
        button.deleteLater()
        label.deleteLater()
        editor.deleteLater()

        # Add all remaining widgets to layout again
        for row, (button, label, editor) in enumerate(self._option_widgets.values(), 1):
            layout.addWidget(button, row, 0)
            layout.addWidget(label, row, 1)
            layout.addWidget(editor, row, 2)

    def clear_options(self) -> None:
        layout = self.layout()
        widgets = list(self._option_widgets.values())
        self._option_widgets.clear()
        for button, label, editor in reversed(widgets):
            layout.removeWidget(button)
            layout.removeWidget(label)
            layout.removeWidget(editor)
            button.setParent(None)
            label.setParent(None)
            editor.setParent(None)
            button.deleteLater()
            label.deleteLater()
            editor.deleteLater()
