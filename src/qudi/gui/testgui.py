# -*- coding: utf-8 -*-

"""
ToDo

Copyright (c) 2022, the qudi developers. See the AUTHORS.md file at the top-level directory of this
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

__all__ = ['TestGui']

import numpy as np
from pprint import pprint
from PySide2 import QtCore, QtWidgets
from qudi.core.module import GuiBase
from qudi.util.widgets.plotting.interactive_curve import InteractiveCurvesWidget


class TestControlWidget(QtWidgets.QWidget):
    """
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.x_rubberband_checkbox = QtWidgets.QCheckBox('Rubberband Zoom X')
        self.y_rubberband_checkbox = QtWidgets.QCheckBox('Rubberband Zoom Y')

        self.cursor_position_checkbox = QtWidgets.QCheckBox('Cursor Position')
        self.cursor_position_checkbox.setChecked(True)
        self.plot_editor_checkbox = QtWidgets.QCheckBox('Plot Editor')
        self.plot_editor_checkbox.setChecked(True)
        self.plot_selector_checkbox = QtWidgets.QCheckBox('Plot Selector')
        self.plot_selector_checkbox.setChecked(True)

        self.x_marker_checkbox = QtWidgets.QCheckBox('X Marker Selection')
        self.y_marker_checkbox = QtWidgets.QCheckBox('Y Marker Selection')
        self.x_region_checkbox = QtWidgets.QCheckBox('X Region Selection')
        self.y_region_checkbox = QtWidgets.QCheckBox('y Region Selection')

        self.clear_region_button = QtWidgets.QPushButton('Clear Regions')
        self.clear_marker_button = QtWidgets.QPushButton('Clear Markers')
        self.print_region_button = QtWidgets.QPushButton('Print Regions')
        self.print_marker_button = QtWidgets.QPushButton('Print Markers')

        toggle_layout = QtWidgets.QVBoxLayout()
        toggle_layout.addWidget(self.cursor_position_checkbox)
        toggle_layout.addWidget(self.plot_editor_checkbox)
        toggle_layout.addWidget(self.plot_selector_checkbox)
        toggle_layout.addStretch()

        rubberband_layout = QtWidgets.QVBoxLayout()
        rubberband_layout.addWidget(self.x_rubberband_checkbox)
        rubberband_layout.addWidget(self.y_rubberband_checkbox)
        rubberband_layout.addStretch()

        selection_layout = QtWidgets.QVBoxLayout()
        selection_layout.addWidget(self.x_marker_checkbox)
        selection_layout.addWidget(self.y_marker_checkbox)
        selection_layout.addWidget(self.x_region_checkbox)
        selection_layout.addWidget(self.y_region_checkbox)
        selection_layout.addStretch()

        button_layout = QtWidgets.QVBoxLayout()
        button_layout.addWidget(self.clear_region_button)
        button_layout.addWidget(self.clear_marker_button)
        button_layout.addWidget(self.print_region_button)
        button_layout.addWidget(self.print_marker_button)
        button_layout.addStretch()

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(toggle_layout)
        layout.addLayout(rubberband_layout)
        layout.addLayout(selection_layout)
        layout.addLayout(button_layout)
        layout.addStretch()
        self.setLayout(layout)


class _MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.test_widget = InteractiveCurvesWidget()
        self.setCentralWidget(self.test_widget)

        self.control_widget = TestControlWidget()
        self.control_dockwidget = QtWidgets.QDockWidget('Test Controls', parent=self)
        self.control_dockwidget.setWidget(self.control_widget)
        self.control_dockwidget.setFloating(False)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.TopDockWidgetArea, self.control_dockwidget)

        self.control_widget.clear_marker_button.clicked.connect(
            self.test_widget.clear_marker_selections
        )
        self.control_widget.clear_region_button.clicked.connect(
            self.test_widget.clear_region_selections
        )
        self.control_widget.print_marker_button.clicked.connect(
            lambda: pprint(self.test_widget.marker_selection)
        )
        self.control_widget.print_region_button.clicked.connect(
            lambda: pprint(self.test_widget.region_selection)
        )
        self.control_widget.x_marker_checkbox.clicked.connect(self._update_marker_mode)
        self.control_widget.y_marker_checkbox.clicked.connect(self._update_marker_mode)
        self.control_widget.x_region_checkbox.clicked.connect(self._update_region_mode)
        self.control_widget.y_region_checkbox.clicked.connect(self._update_region_mode)
        self.control_widget.x_rubberband_checkbox.clicked.connect(self._update_rubberband_mode)
        self.control_widget.y_rubberband_checkbox.clicked.connect(self._update_rubberband_mode)
        self.control_widget.cursor_position_checkbox.clicked[bool].connect(
            lambda x: self.test_widget.toggle_cursor_position(x)
        )
        self.control_widget.plot_editor_checkbox.clicked[bool].connect(
            lambda x: self.test_widget.toggle_plot_editor(x)
        )
        self.control_widget.plot_selector_checkbox.clicked[bool].connect(
            lambda x: self.test_widget.toggle_plot_selector(x)
        )

    def _update_marker_mode(self) -> None:
        x = self.control_widget.x_marker_checkbox.isChecked()
        y = self.control_widget.y_marker_checkbox.isChecked()
        if x and y:
            mode = self.test_widget.SelectionMode.XY
        elif x:
            mode = self.test_widget.SelectionMode.X
        elif y:
            mode = self.test_widget.SelectionMode.Y
        else:
            mode = self.test_widget.SelectionMode.Disabled
        self.test_widget.set_marker_selection_mode(mode)

    def _update_region_mode(self) -> None:
        x = self.control_widget.x_region_checkbox.isChecked()
        y = self.control_widget.y_region_checkbox.isChecked()
        if x and y:
            mode = self.test_widget.SelectionMode.XY
        elif x:
            mode = self.test_widget.SelectionMode.X
        elif y:
            mode = self.test_widget.SelectionMode.Y
        else:
            mode = self.test_widget.SelectionMode.Disabled
        self.test_widget.set_region_selection_mode(mode)

    def _update_rubberband_mode(self) -> None:
        x = self.control_widget.x_rubberband_checkbox.isChecked()
        y = self.control_widget.y_rubberband_checkbox.isChecked()
        if x and y:
            mode = self.test_widget.SelectionMode.XY
        elif x:
            mode = self.test_widget.SelectionMode.X
        elif y:
            mode = self.test_widget.SelectionMode.Y
        else:
            mode = self.test_widget.SelectionMode.Disabled
        self.test_widget.set_rubberband_zoom_selection_mode(mode)


class TestGui(GuiBase):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mw = None

    def on_activate(self) -> None:
        self._mw = _MainWindow()
        x = np.linspace(0, 4*np.pi, 200)
        y1 = np.sin(x)
        y2 = 2 * np.sin(2*x)
        y3 = 3 * np.sin(3*x)
        y4 = 4 * np.sin(4*x)
        self._mw.test_widget.plot(x=x, y=y1, pen='g')
        self._mw.test_widget.plot(x=x, y=y2, name='my plot', pen='r')
        self._mw.test_widget.plot(x=x, y=y3, name='my other plot', pen='b')
        self._mw.test_widget.plot(x=x, y=y4, name='not mine', pen='c')
        self._mw.test_widget.set_units('rad', 'V')
        self._mw.test_widget.set_labels('Phase', 'Amplitude')
        self.show()

    def on_deactivate(self) -> None:
        self._mw.close()
        self._mw = None

    def show(self) -> None:
        self._mw.show()
        self._mw.raise_()
        self._mw.activateWindow()
