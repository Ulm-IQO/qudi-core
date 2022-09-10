# -*- coding: utf-8 -*-

"""
Improved pyqtgraph.AxisItem objects.

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

__all__ = ['LabelNudgeAxis', 'label_nudged_plot_widget']

from PySide2.QtCore import QSizeF, QPointF
from pyqtgraph import AxisItem, PlotWidget
from typing import Type


def label_nudged_plot_widget(plot_widget_type: Type[PlotWidget]) -> Type[PlotWidget]:
    class NudgedPlotWidget(plot_widget_type):
        def __init__(self, **kwargs) -> None:
            if 'axisItems' not in kwargs:
                bottom_axis = LabelNudgeAxis(orientation='bottom')
                left_axis = LabelNudgeAxis(orientation='left')
                bottom_axis.nudge = 0
                left_axis.nudge = 0
                kwargs['axisItems'] = {'bottom': bottom_axis, 'left': left_axis}
            super().__init__(**kwargs)
    return NudgedPlotWidget


class LabelNudgeAxis(AxisItem):
    """ This is a custom axis that extends the normal pyqtgraph to be able to nudge the axis labels
    """

    @property
    def nudge(self):
        if not hasattr(self, '_nudge'):
            self._nudge = 5
        return self._nudge

    @nudge.setter
    def nudge(self, nudge):
        self._nudge = nudge
        s = self.size()
        # call resizeEvent indirectly
        self.resize(s + QSizeF(1, 1))
        self.resize(s)

    def resizeEvent(self, ev=None):
        # Set the position of the label
        nudge = self.nudge
        br = self.label.boundingRect()
        p = QPointF(0, 0)
        size = self.size()
        if self.orientation == 'left':
            p.setY(int(size.height() / 2 + br.width() / 2))
            p.setX(-nudge)
        elif self.orientation == 'right':
            p.setY(int(size.height() / 2 + br.width() / 2))
            p.setX(int(size.width() - br.height() + nudge))
        elif self.orientation == 'top':
            p.setY(-nudge)
            p.setX(int(size.width() / 2.0 - br.width() / 2.0))
        elif self.orientation == 'bottom':
            p.setX(int(size.width() / 2.0 - br.width() / 2.0))
            p.setY(int(size.height() - br.height() + nudge))
        self.label.setPos(p)
        self.picture = None
