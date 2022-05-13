# -*- coding: utf-8 -*-

"""
This file contains customized pyqtgraph graphics items to be used as data ROI markers in 1D and 2D plots.
This is an attempt to provide a somewhat unified interface to these markers contrary to the
heterogeneous interfaces of pyqtgraph items.

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

__all__ = ['RectROI', 'TargetItem']

import numpy as np
from typing import Union, Tuple, Optional
from PySide2 import QtCore, QtGui
from pyqtgraph import ROI
from pyqtgraph import TargetItem as _TargetItem





class CrosshairROI(ROI):
    """
    """
    def __init__(self, pos, size, bounds=None, **kwargs):
        ROI.__init__(self, pos, size, **kwargs)
        self.bounds = bounds
        self._bounding_rect = None

    def paint(self, p, opt, widget):
        # Note: don't use self.boundingRect here, because subclasses may need to redefine it.
        r = self.roi_rect
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.setPen(self.currentPen)

        # Draw crosshair infinite lines
        vr = self.getViewBox().viewRect()
        top_scaled = (vr.bottom() - r.top()) / r.height()
        bottom_scaled = (r.top() - vr.top()) / r.height()
        p.drawLine(QtCore.QPointF(0.5, -bottom_scaled), QtCore.QPointF(0.5, top_scaled))
        right_scaled = (vr.right() - r.left()) / r.width()
        left_scaled = (r.left() - vr.left()) / r.width()
        p.drawLine(QtCore.QPointF(-left_scaled, 0.5), QtCore.QPointF(right_scaled, 0.5))

        # Draw ROI rect
        p.drawRect(0, 0, 1, 1)

    def boundingRect(self):
        if self._bounding_rect is None:
            self._calc_bounding_rect()
        return self._bounding_rect

    def viewTransformChanged(self):
        """
        Called whenever the transformation matrix of the view has changed.
        (eg, the view range has changed or the view was resized)
        """
        super().viewTransformChanged()
        self.update()

    def _calc_bounding_rect(self):
        self._bounding_rect = QtCore.QRectF(self.getViewBox().viewRect())
        self.prepareGeometryChange()

    def position(self) -> Tuple[float, float]:
        center = self.roi_rect.center()
        return center.x(), center.y()

    def set_position(self, pos: Tuple[float, float]) -> None:
        shift = QtCore.QPointF(*pos) - self.roi_rect.center()
        new_pos = self.pos() + shift
        self.setPos(new_pos)

    def set_size(self, size: Tuple[float, float]) -> None:
        self.setSize(size, center=(0.5, 0.5))

    @property
    def roi_rect(self) -> QtCore.QRectF:
        return QtCore.QRectF(self.state['pos'][0],
                             self.state['pos'][1],
                             self.state['size'][0],
                             self.state['size'][1]).normalized()


class TargetItem(_TargetItem):
    """
    """
    def __init__(self, bounds=None, **kwargs):
        self.bounds = bounds
        _TargetItem.__init__(self, **kwargs)

    def setPos(self, *args):
        if self.bounds is not None:
            x_pos, y_pos = args[0] if len(args) == 1 else args
            clipped_x = x_pos if self.bounds[0] is None else np.clip(x_pos, *self.bounds[0])
            clipped_y = y_pos if self.bounds[1] is None else np.clip(y_pos, *self.bounds[1])
            args = ((clipped_x, clipped_y),)
        return super().setPos(*args)

    def set_bounds(self, bounds):
        self.bounds = bounds
        self.setPos(self.pos())
