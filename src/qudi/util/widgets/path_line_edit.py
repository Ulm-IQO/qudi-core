# -*- coding: utf-8 -*-

"""
This file contains a QWidget very similar to QLineEdit that can also open a file dialog to select
directories and files and display them in the QLineEdit.

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

__all__ = ['PathLineEdit']

import os
from PySide2 import QtCore, QtWidgets, QtGui
from typing import Optional, Any, List

from qudi.util.paths import get_artwork_dir as _get_artwork_dir


class PathLineEdit(QtWidgets.QWidget):
    """ QLineEdit for editing file system paths directly or via QFileDialog.
    No validation is performed on the entered string.
    Multiple paths are separated by single semicolon, e.g. '<path1>;<path2>;<path3>'

    Specify multiple filters by separating them with double(!) semicolons, e.g.:
    Images (*.png *.xpm *.jpg);;Text files (*.txt);;XML files (*.xml)
    """

    def __init__(self,
                 text: Optional[str] = None,
                 parent: Optional[QtWidgets.QWidget] = None,
                 dialog_caption: Optional[str] = None,
                 root_directory: Optional[str] = None,
                 filters: Optional[str] = None,
                 select_directory: Optional[bool] = False,
                 follow_symlinks: Optional[bool] = False,
                 ) -> None:
        super().__init__(parent=parent)
        self._line_edit = QtWidgets.QLineEdit(text)
        self._tool_button = QtWidgets.QToolButton()
        self._tool_button.setIcon(
            QtGui.QIcon(os.path.join(os.path.join(_get_artwork_dir(), 'icons', 'document-open')))
        )
        self._tool_button.setToolTip('Open file dialog')
        self._tool_button.clicked.connect(self._exec_file_dialog)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._line_edit)
        layout.addWidget(self._tool_button)
        layout.setStretch(0, 1)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self._filters = '' if filters is None else filters
        self._select_directory = bool(select_directory)
        self._follow_symlinks = bool(follow_symlinks)
        self._root_directory = os.path.abspath(os.sep) if root_directory is None else root_directory
        if dialog_caption is None:
            self._dialog_caption = 'Select Directory' if self._select_directory else 'Select Files'
        else:
            self._dialog_caption = dialog_caption

    def __getattr__(self, item: str) -> Any:
        try:
            return getattr(self._line_edit, item)
        except AttributeError:
            pass
        raise AttributeError(f"'{self.__class__.__name__}' object has not attribute '{item}'")

    @property
    def paths(self) -> List[str]:
        paths = (p.strip() for p in self._line_edit.text().split(';'))
        return [p for p in paths if p]

    @QtCore.Slot()
    def _exec_file_dialog(self) -> None:
        self._line_edit.clearFocus()
        dialog = QtWidgets.QFileDialog(parent=self,
                                       caption=self._dialog_caption,
                                       directory=self._root_directory,
                                       filter=self._filters)
        options = QtWidgets.QFileDialog.Option.ReadOnly
        if not self._follow_symlinks:
            options |= QtWidgets.QFileDialog.Option.DontResolveSymlinks
        if self._select_directory:
            dialog.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)
            options |= QtWidgets.QFileDialog.Option.ShowDirsOnly
        else:
            dialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFiles)
        dialog.setOptions(options)
        if dialog.exec_() == QtWidgets.QFileDialog.Accepted:
            paths = dialog.selectedFiles()
            if paths:
                text = ';'.join(p for p in paths if p)
                if text and text != self._line_edit.text():
                    self._line_edit.setText(text)
                    self._line_edit.textEdited.emit(text)
                    self._line_edit.editingFinished.emit()
        dialog.setParent(None)
        dialog.deleteLater()
