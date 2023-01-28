# -*- coding: utf-8 -*-

"""
QWidgets serving as editors for custom configuration entries.

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

__all__ = ['CustomItemsWidget', 'CustomOptionsWidget', 'CustomConnectorsWidget']

import os
from PySide6 import QtCore, QtWidgets, QtGui
from typing import Optional, Mapping, Union, Dict, Iterable, Any

from qudi.util.paths import get_artwork_dir


class CustomItemsWidget(QtWidgets.QWidget):
    """
    """
    def __init__(self,
                 forbidden_names: Optional[Iterable[str]] = None,
                 allowed_values: Optional[Iterable[str]] = None,
                 config: Optional[Mapping[str, str]] = None,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)

        self._forbidden_names = frozenset() if forbidden_names is None else frozenset(
            forbidden_names)
        self._allowed_values = [val.strip() for val in allowed_values] if allowed_values else None

        layout = QtWidgets.QGridLayout()
        layout.setColumnStretch(2, 1)
        self.setLayout(layout)

        icons_dir = os.path.join(get_artwork_dir(), 'icons')
        self.add_item_button = QtWidgets.QToolButton()
        self.add_item_button.setIcon(QtGui.QIcon(os.path.join(icons_dir, 'list-add')))
        self.add_item_button.clicked.connect(self._add_item_clicked)
        self.item_name_lineedit = QtWidgets.QLineEdit()
        layout.addWidget(self.add_item_button, 0, 0, 1, 1)
        layout.addWidget(self.item_name_lineedit, 0, 1, 1, 2)

        # Remove icons reused for each custom item
        self._remove_icon = QtGui.QIcon(os.path.join(icons_dir, 'list-remove'))
        # Keep track of custom item widgets
        self._item_widgets = dict()

        # Set config if given
        self.set_config(config)

    @property
    def config(self) -> Dict[str, str]:
        if self._allowed_values is None:
            config = {
                name: widgets[2].text().strip() for name, widgets in self._item_widgets.items()
            }
        else:
            config = {
                name: widgets[2].currentText() for name, widgets in self._item_widgets.items()
            }
        return config

    def set_config(self, config: Union[None, Mapping[str, str]]) -> None:
        self.clear_items()
        if config:
            for name, value in config.items():
                self.add_item(name, value)

    def add_item(self, name: str, value: Optional[str] = None) -> None:
        if not name:
            raise ValueError('Item name must be non-empty string')
        if name in self._forbidden_names:
            raise ValueError(f'Item name to add "{name}" is one of the forbidden names:\n'
                             f'{set(self._forbidden_names)}')
        if name in self._item_widgets:
            raise ValueError(f'Item name to add "{name}" is already present')

        label = QtWidgets.QLabel(f'{name}:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        label.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        if self._allowed_values:
            editor = QtWidgets.QComboBox()
            editor.addItem('')
            editor.addItems(self._allowed_values)
            editor.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        else:
            editor = QtWidgets.QLineEdit()
        remove_button = QtWidgets.QToolButton()
        remove_button.setIcon(self._remove_icon)
        remove_button.clicked.connect(lambda: self.remove_item(name))
        row = len(self._item_widgets) + 1
        layout = self.layout()
        layout.addWidget(remove_button, row, 0)
        layout.addWidget(label, row, 1)
        layout.addWidget(editor, row, 2)
        self._item_widgets[name] = (remove_button, label, editor)

    def remove_item(self, name: str) -> None:
        if name not in self._item_widgets:
            return

        layout = self.layout()

        # Remove all widgets from layout
        for button, label, editor in reversed(list(self._item_widgets.values())):
            layout.removeWidget(button)
            layout.removeWidget(label)
            layout.removeWidget(editor)

        # Delete widgets for row to remove
        button, label, editor = self._item_widgets.pop(name)
        button.clicked.disconnect()
        button.setParent(None)
        label.setParent(None)
        editor.setParent(None)
        button.deleteLater()
        label.deleteLater()
        editor.deleteLater()

        # Add all remaining widgets to layout again
        for row, (button, label, editor) in enumerate(self._item_widgets.values(), 1):
            layout.addWidget(button, row, 0)
            layout.addWidget(label, row, 1)
            layout.addWidget(editor, row, 2)

    def clear_items(self) -> None:
        layout = self.layout()
        widgets = list(self._item_widgets.values())
        self._item_widgets.clear()
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

    @QtCore.Slot()
    def _add_item_clicked(self) -> None:
        name = self.item_name_lineedit.text().strip()
        try:
            self.add_item(name)
            self.item_name_lineedit.clear()
        except ValueError:
            pass


class CustomOptionsWidget(CustomItemsWidget):
    """
    """
    def __init__(self,
                 forbidden_names: Optional[Iterable[str]] = None,
                 config: Optional[Mapping[str, Any]] = None,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(forbidden_names=forbidden_names, config=config, parent=parent)

        self.add_item_button.setToolTip('Add custom ConfigOption with given name.')
        self.item_name_lineedit.setPlaceholderText('Enter custom ConfigOption name')

    @property
    def config(self) -> Dict[str, Any]:
        cfg = super().config
        for name, value in cfg.items():
            if value == '':
                cfg[name] = None
            else:
                try:
                    cfg[name] = eval(value)
                except:
                    pass
        return cfg

    def set_config(self, config: Union[None, Mapping[str, Any]]) -> None:
        if config:
            config = {name: '' if val is None else repr(val) for name, val in config.items()}
        return super().set_config(config)

    def add_item(self, name: str, value: Optional[str] = None) -> None:
        super().add_item(name=name, value=value)
        self._item_widgets[name][2].setPlaceholderText('text parsed by eval()')


class CustomConnectorsWidget(CustomItemsWidget):
    """
    """
    def __init__(self,
                 forbidden_names: Optional[Iterable[str]] = None,
                 module_names: Optional[Iterable[str]] = None,
                 config: Optional[Mapping[str, Any]] = None,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(forbidden_names=forbidden_names,
                         allowed_values=module_names,
                         config=config,
                         parent=parent)

        self.add_item_button.setToolTip('Add custom Connector with given name.')
        self.item_name_lineedit.setPlaceholderText('Enter custom Connector name')
