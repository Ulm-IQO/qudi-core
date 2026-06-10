# -*- coding: utf-8 -*-

"""
This module contains the QTreeWidget object to display qudi configurations.

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

__all__ = ['ConfigQTreeWidget']

from typing import Any, Mapping
from collections.abc import Sequence as AbstractSequence
from collections.abc import Mapping as AbstractMapping
from PySide6 import QtWidgets


class ConfigQTreeWidget(QtWidgets.QTreeWidget):
    """Specialized QTreeWidget to display qudi configurations.
    """

    def set_config(self, config: Mapping[str, Any]) -> None:
        self.clear()
        self._insert_value(self.invisibleRootItem(), config)

    def _insert_value(self, root: QtWidgets.QTreeWidgetItem, value: Any) -> None:
        """Recursively fill the QTreeWidgeItem.
        """
        # if value is a mapping, open up a new sub-tree and recursively fill it
        if isinstance(value, AbstractMapping):
            if len(value) == 0:
                root.setText(0, f'{root.text(0)} {{}}')
            else:
                for key, val in value.items():
                    child = QtWidgets.QTreeWidgetItem()
                    child.setText(0, f'{key}:')
                    root.addChild(child)
                    self._insert_value(child, val)
                root.setExpanded(True)
        # if value is any string (or similar) type, e.g. str, bytes, bytearray, just add it to root
        elif isinstance(value, (str, bytearray, bytes)):
            try:
                text = value.decode('utf8')
            except (UnicodeDecodeError, AttributeError):
                text = str(value)
            root.setText(0, f'{root.text(0)} "{text}"')
        # If the value is a sequence of values itself, open up a new sub-tree and fill it
        elif isinstance(value, AbstractSequence):
            if len(value) == 0:
                root.setText(0, f'{root.text(0)} []')
            else:
                for val in value:
                    child = QtWidgets.QTreeWidgetItem()
                    child.setText(0, '-')
                    root.addChild(child)
                    self._insert_value(child, val)
                root.setExpanded(True)
        # If the value is anything else, just convert to str
        else:
            root.setText(0, f'{root.text(0)} {str(value)}')
