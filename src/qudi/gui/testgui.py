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
from PySide2 import QtCore, QtWidgets
from qudi.core.module import GuiBase
from qudi.util.widgets.plotting.image_widget import RubberbandZoomSelectionImageWidget
from qudi.util.widgets.plotting.plot_widget import RubberbandZoomSelectionPlotWidget
from qudi.util.widgets.plotting.plot_item import XYPlotItem


class TestGui(GuiBase):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._mw = QtWidgets.QMainWindow()
        self._mw.setWindowTitle('Derp Herp Inc.')
        central_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        central_widget.setLayout(layout)
        self._mw.setCentralWidget(central_widget)

        self.plotwidget = RubberbandZoomSelectionPlotWidget()
        self.plot_data = 100 * np.random.rand(10)
        self.plot_item = XYPlotItem(self.plot_data)
        self.plotwidget.addItem(self.plot_item)
        layout.addWidget(self.plotwidget)

        self.image_widget = RubberbandZoomSelectionImageWidget()
        self.image_data = 100 * np.random.rand(10, 10)
        self.image_widget.set_image(self.image_data)
        layout.addWidget(self.image_widget)
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)

    def show(self) -> None:
        self._mw.show()
        self._mw.raise_()
        self._mw.activateWindow()

    def on_activate(self) -> None:
        self.show()

    def on_deactivate(self) -> None:
        self._mw.close()
        self.plotwidget.removeItem(self.crosshair)

