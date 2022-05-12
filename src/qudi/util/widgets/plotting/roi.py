# -*- coding: utf-8 -*-

"""
This file contains custom pyqtgraph.ROI subclasses to be used in graphs.

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


class RectROI(ROI):
    """
    """
    def __init__(self, pos, size, bounds=None, corner_handles=True, side_handles=True, **kwargs):
        self.maxBounds = None
        kwargs['maxBounds'] = self._get_maxBounds(bounds)
        ROI.__init__(self, pos, size, **kwargs)
        self._bounds = bounds
        if corner_handles:
            self.addScaleHandle([1, 1], [0, 0])
            self.addScaleHandle([0, 0], [1, 1])
            self.addScaleHandle([1, 0], [0, 1])
            self.addScaleHandle([0, 1], [1, 0])
        if side_handles:
            self.addScaleHandle([1, 0.5], [0, 0.5])
            self.addScaleHandle([0.5, 1], [0.5, 0])
            self.addScaleHandle([0, 0.5], [1, 0.5])
            self.addScaleHandle([0.5, 0], [0.5, 1])

    def set_bounds(self, bounds) -> None:
        bound_rect = self._get_maxBounds(bounds)
        self.maxBounds = bound_rect
        self._bounds = bounds
        self._correct_bounds()

    def get_bounds(self):
        return self._bounds

    def _correct_bounds(self):
        if isinstance(self.maxBounds, QtCore.QRectF):
            curr_rect = QtCore.QRectF(*self.pos(), *self.size()).normalized()
            if not self.maxBounds.contains(curr_rect):
                intersect = self.maxBounds.intersected(curr_rect).normalized()
                super().setPos(intersect.x(), intersect.y())
                super().setSize(intersect.size())

    @staticmethod
    def _get_maxBounds(bounds) -> Union[None, QtCore.QRectF]:
        if bounds is None or (bounds[0] is None and bounds[1] is None):
            return None
        try:
            x_min, x_max = bounds[0]
        except TypeError:
            x_min = x_max = None
        try:
            y_min, y_max = bounds[1]
        except TypeError:
            y_min = y_max = None

        if x_min is x_max is y_min is y_max is None:
            return None

        if x_min is None:
            x_min = float('-inf')
        if x_max is None:
            x_max = float('inf')
        if y_min is None:
            y_min = float('-inf')
        if y_max is None:
            y_max = float('inf')
        return QtCore.QRectF(QtCore.QPointF(x_min, y_min),
                             QtCore.QPointF(x_max, y_max)).normalized()

    def setPos(self, pos, y=None, update=True, finish=True):
        super().setPos(pos, y, update, finish)
        self._correct_bounds()

    def setSize(self, size, center=None, centerLocal=None, snap=False, update=True, finish=True):
        super().setSize(size, center, centerLocal, snap, update, finish)
        self._correct_bounds()


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
