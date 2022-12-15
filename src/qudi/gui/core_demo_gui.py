# -*- coding: utf-8 -*-
"""
FIXME

Copyright (c) 2022, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-iqo-modules/>

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

from enum import IntEnum
from pyqtgraph import ScatterPlotItem
from PySide2 import QtWidgets, QtCore, QtGui

from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.core.module import GuiBase
from qudi.core.configoption import ConfigOption

from qudi.util.widgets.plotting.plot_widget import DataSelectionPlotWidget
from qudi.util.widgets.plotting.interactive_curve import InteractiveCurvesWidget


class FollowWidget(DataSelectionPlotWidget):
    def __init__(self):
        ranges = (-0.0005, 0.0005)
        super().__init__(selection_bounds=[ranges, ranges],
                         allow_tracking_outside_data=True,
                         xy_region_selection_crosshair=True,
                         xy_region_selection_handles=False,
                         xy_region_min_size_percentile=0.015)
        self.plot_data = ScatterPlotItem()
        self.addItem(self.plot_data)
        self.add_region_selection(span=((0, 0), (0, 0)), mode=self.SelectionMode.XY)
        self.setRange(xRange=ranges, yRange=ranges)


class InteractivePlotWidget(InteractiveCurvesWidget):
    def __init__(self):
        super().__init__(allow_tracking_outside_data=True,
                         max_mouse_pos_update_rate=20,
                         selection_bounds=None,
                         selection_pen=None,
                         selection_hover_pen=None,
                         selection_brush=None,
                         selection_hover_brush=None,
                         xy_region_selection_crosshair=False,
                         xy_region_selection_handles=True)
        self.layout().setContentsMargins(0, 0, 0, 0)


class _MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setWindowTitle('qudi-core demo')

        self.follow_widget = FollowWidget()
        self.interactive_widget = InteractivePlotWidget()

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.follow_widget)
        layout.addWidget(self.interactive_widget)
        widget.setLayout(layout)
        self.setCentralWidget(widget)


class CoreDemoGui(GuiBase):
    """ FIXME
    """

    # declare connectors
    _core_demo = Connector(name='core_demo_logic', interface='CoreDemoLogic')

    # declare signals
    sigFollowTargetPositionUpdated = QtCore.Signal(tuple)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mw = None

    def on_activate(self):
        """ Create all UI objects and show the window.
        """
        self._mw = _MainWindow()
        self._mw.follow_widget.sigRegionSelectionChanged.connect(self._follow_crosshair_moved)
        self._restore_window_geometry(self._mw)
        core_demo = self._core_demo()
        core_demo.sigFollowPositionChanged.connect(self._follow_position_updated,
                                                   QtCore.Qt.QueuedConnection)
        self.sigFollowTargetPositionUpdated.connect(core_demo.set_follow_target_pos,
                                                    QtCore.Qt.QueuedConnection)
        curr_pos = core_demo.current_follow_pos
        self._follow_position_updated(curr_pos)
        crosshair_span = ((curr_pos[0]-0.00001, curr_pos[0]+0.00001),
                          (curr_pos[1]-0.00001, curr_pos[1]+0.00001))
        self._mw.follow_widget.move_region_selection(crosshair_span, 0)
        self.show()

    def on_deactivate(self):
        """ Hide window empty the GUI and disconnect signals
        """
        self._mw.follow_widget.sigRegionSelectionChanged.disconnect()
        self.sigFollowTargetPositionUpdated.disconnect()
        self._core_demo().sigFollowPositionChanged.disconnect(self._follow_position_updated)
        self._save_window_geometry(self._mw)
        self._mw.close()

    def show(self):
        """ Make sure that the window is visible and at the top.
        """
        self._mw.show()

    def _follow_crosshair_moved(self, selection_dict):
        selection = selection_dict[DataSelectionPlotWidget.SelectionMode.XY]
        if selection:
            self.sigFollowTargetPositionUpdated.emit(selection[0][0])

    def _follow_position_updated(self, pos):
        x, y = pos
        self._mw.follow_widget.plot_data.addPoints(x=[x], y=[y])
