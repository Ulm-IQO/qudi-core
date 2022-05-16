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

import numpy as np
from typing import Union, Optional, Tuple
from PySide2 import QtCore, QtWidgets
from pyqtgraph import PlotWidget, TargetItem

from qudi.core.module import GuiBase
from qudi.util.widgets.plotting.view_box import DataSelectionViewBox
from qudi.util.widgets.plotting.plot_item import DataImageItem
from qudi.util.widgets.plotting.marker import InfiniteCrosshair, Rectangle


class TestGui(GuiBase):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.viewbox = DataSelectionViewBox()
        self.plotwidget = PlotWidget(viewBox=self.viewbox)
        # self.plotwidget = PlotWidget()
        self.data = 100 * np.random.rand(10, 10)
        self.image = DataImageItem(self.data)
        self.image.set_image_extent(((0, 9), (0, 9)), adjust_for_px_size=True)
        self.plotwidget.addItem(self.image)
        self._mw = QtWidgets.QMainWindow()
        self._mw.setWindowTitle('Derp Herp Inc.')
        self._mw.setCentralWidget(self.plotwidget)
        self.viewbox.set_region_selection_mode(self.viewbox.SelectionMode.XY)
        self.viewbox.set_marker_selection_mode(self.viewbox.SelectionMode.XY)
        self.viewbox.set_selection_mutable(True)
        self.viewbox.set_selection_bounds([(-0.5, 9.5), (-0.5, 9.5)])

    def show(self) -> None:
        self._mw.show()
        self._mw.raise_()
        self._mw.activateWindow()

    def on_activate(self) -> None:
        self.show()

    def on_deactivate(self) -> None:
        self._mw.close()
        self.plotwidget.removeItem(self.crosshair)

