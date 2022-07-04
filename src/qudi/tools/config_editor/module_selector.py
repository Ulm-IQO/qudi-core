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

__all__ = ['ModuleSelector']

from PySide2 import QtWidgets, QtCore
from typing import Optional, Iterable, List, Mapping, Tuple, Dict

from qudi.tools.config_editor.tree_widgets import AvailableModulesTreeWidget
from qudi.tools.config_editor.tree_widgets import SelectedModulesTreeWidget
from qudi.util.widgets.separator_lines import HorizontalLine


class ModuleSelector(QtWidgets.QDialog):
    """ QDialog representing a selection editor for qudi modules to configure
    """

    def __init__(self,
                 available_modules: Iterable[str],
                 named_modules: Optional[Mapping[str, str]] = None,
                 unnamed_modules: Optional[Iterable[str]] = None,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)

        self.setWindowTitle('Qudi Config Editor: Module Selection')
        screen_size = QtWidgets.QApplication.instance().primaryScreen().availableSize()
        self.resize(screen_size.width() // 3, screen_size.height() // 3)

        # Create two customized QTreeWidgets. One for all available modules to select from and one
        # for the selected modules.
        self.available_treewidget = AvailableModulesTreeWidget(modules=available_modules)
        self.selected_treewidget = SelectedModulesTreeWidget(named_modules=named_modules,
                                                             unnamed_modules=unnamed_modules)

        # Create left side of splitter widget
        left_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel('Available Modules')
        font = label.font()
        font.setPointSize(font.pointSize() + 4)
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label)
        layout.addWidget(self.available_treewidget)
        left_widget.setLayout(layout)

        # Create right side of splitter widget
        right_widget = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout()
        right_widget.setLayout(layout)
        label = QtWidgets.QLabel('Selected Modules')
        label.setFont(font)
        self.add_remote_button = QtWidgets.QPushButton('Add Remote Module')
        self.add_custom_button = QtWidgets.QPushButton('Add Custom Module')
        self.custom_module_lineedit = QtWidgets.QLineEdit()
        self.custom_module_lineedit.setPlaceholderText('Custom module name (module.Class)')
        self.base_selection_combobox = QtWidgets.QComboBox()
        self.base_selection_combobox.addItems(['GUI', 'Logic', 'Hardware'])
        self.add_remote_button.clicked.connect(self._add_remote_module_clicked)
        self.add_custom_button.clicked.connect(self._add_custom_module_clicked)
        layout.addWidget(label, 0, 0, 1, 3)
        layout.addWidget(self.selected_treewidget, 1, 0, 1, 3)
        label = QtWidgets.QLabel('Module Base:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 2, 0)
        layout.addWidget(self.base_selection_combobox, 2, 1)
        layout.addWidget(self.add_remote_button, 2, 2)
        layout.addWidget(self.custom_module_lineedit, 3, 0, 1, 2)
        layout.addWidget(self.add_custom_button, 3, 2)
        layout.setColumnStretch(0, 1)
        layout.setRowStretch(1, 1)

        # set splitter as main widget
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        # Create buttonbox for this dialog

        label = QtWidgets.QLabel(
            'Include qudi modules by dragging them into the right field (press DEL to remove).'
        )
        label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.addWidget(label)
        sub_layout.addStretch()
        sub_layout.addWidget(self.button_box)

        # Add everything to the main layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(splitter)
        layout.addWidget(HorizontalLine())
        layout.addLayout(sub_layout)
        layout.setStretch(0, 1)
        self.setLayout(layout)

    @property
    def selected_modules(self) -> Tuple[Dict[str, str], List[str]]:
        return self.selected_treewidget.modules

    @QtCore.Slot()
    def _add_remote_module_clicked(self) -> None:
        base = self.base_selection_combobox.currentText().lower()
        if base == 'gui':
            raise ValueError('Unable to add remote module.\nGUI modules can not be remote modules.')
        self.selected_treewidget.add_module(f'{base}.<REMOTE MODULE>')

    @QtCore.Slot()
    def _add_custom_module_clicked(self) -> None:
        base = self.base_selection_combobox.currentText().lower()
        module = self.custom_module_lineedit.text().strip()
        if module:
            self.selected_treewidget.add_module(f'{base}.{module}')
