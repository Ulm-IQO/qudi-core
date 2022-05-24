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

__all__ = ['RectangleROI']

from math import isinf
from typing import Union, Tuple, Optional, Sequence, List
from PySide2 import QtCore
from pyqtgraph import ROI


class RectangleROI(ROI):
    """
    """
    def __init__(self,
                 pos,
                 size=(1, 1),
                 bounds=None,
                 parent=None,
                 pen=None,
                 hoverPen=None,
                 handlePen=None,
                 handleHoverPen=None,
                 movable=True,
                 resizable=True,
                 aspectLocked=False
                 ) -> None:
        ROI.__init__(self,
                     pos,
                     size=size,
                     angle=0,
                     invertible=True,
                     maxBounds=None,
                     scaleSnap=False,
                     translateSnap=False,
                     rotateSnap=False,
                     parent=parent,
                     pen=pen,
                     hoverPen=hoverPen,
                     handlePen=handlePen,
                     handleHoverPen=handleHoverPen,
                     movable=movable,
                     rotatable=False,
                     resizable=resizable,
                     removable=False,
                     aspectLocked=aspectLocked)
        self._bounds = self.normalize_bounds(bounds)
        self._clip_area(update=False)

    @property
    def area(self) -> QtCore.QRectF:
        return self.normalize_rect(self.pos(), self.size())

    def set_area(self, area: QtCore.QRectF) -> None:
        area = self.normalize_rect(area.topLeft(), area.size())
        self.setSize(area.size(), update=False, finish=False)
        self.setPos(area.topLeft(), update=False, finish=False)
        self._clip_area(update=True, finish=True)

    @property
    def bounds(self) -> List[Tuple[Union[None, float], Union[None, float]]]:
        return self._bounds.copy()

    def set_bounds(self,
                   bounds: Union[None, Sequence[Tuple[Union[None, float], Union[None, float]]]]
                   ) -> None:
        self._bounds = self.normalize_bounds(bounds)
        self._clip_area(update=True, finish=True)

    def _clip_area(self, update: Optional[bool] = True, finish: Optional[bool] = True) -> None:
        current_area = self.area
        clipped_area = QtCore.QRectF(current_area)
        x_min, x_max = self._bounds[0]
        y_min, y_max = self._bounds[1]
        if (x_min is not None) and (current_area.left() < x_min):
            clipped_area.setLeft(x_min)
            clipped_area.setRight(min(x_min + current_area.width(), x_max))
        elif (x_max is not None) and (current_area.right() > x_max):
            clipped_area.setRight(x_max)
            clipped_area.setLeft(max(x_max - current_area.width(), x_min))
        if (y_min is not None) and (current_area.bottom() < y_min):
            clipped_area.setBottom(y_min)
            clipped_area.setTop(min(y_min + abs(current_area.height()), y_max))
        elif (y_max is not None) and (current_area.top() > y_max):
            clipped_area.setTop(y_max)
            clipped_area.setBottom(max(y_max - abs(current_area.height()), y_min))
        self.setSize(clipped_area.size(), update=False, finish=False)
        self.setPos(clipped_area.topLeft(), update=update, finish=finish)

    @staticmethod
    def normalize_bounds(bounds: Union[None, Sequence[Tuple[Union[None, float], Union[None, float]]]]
                         ) -> List[Tuple[Union[None, float], Union[None, float]]]:
        if bounds is None:
            bounds = [(None, None), (None, None)]
        else:
            bounds = [list(span) for span in bounds]
            # Replace inf values by None
            for span in bounds:
                for ii, val in enumerate(span):
                    try:
                        if isinf(val):
                            span[ii] = None
                    except TypeError:
                        pass
            # Sort spans in ascending order
            try:
                bounds[0] = tuple(sorted(bounds[0]))
            except TypeError:
                bounds[0] = tuple(bounds[0])
            try:
                bounds[1] = tuple(sorted(bounds[1]))
            except TypeError:
                bounds[1] = tuple(bounds[1])
        return bounds

    @staticmethod
    def normalize_rect(pos: Tuple[float, float], size: Tuple[float, float]) -> QtCore.QRectF:
        try:
            pos = QtCore.QPointF(pos[0], pos[1])
        except TypeError:
            pass
        try:
            size = QtCore.QSizeF(size[0], size[1])
        except TypeError:
            pass
        x_min, x_max = sorted([pos.x(), pos.x() + size.width()])
        y_min, y_max = sorted([pos.y(), pos.y() + size.height()])
        return QtCore.QRectF(x_min,
                             y_max,
                             abs(size.width()),
                             -abs(size.height()))

    def checkPointMove(self, handle, pos, modifiers):
        pos = self.mapSceneToParent(pos)
        x_min, x_max = self._bounds[0]
        y_min, y_max = self._bounds[1]
        if (x_min is not None) and pos.x() < x_min:
            return False
        if (x_max is not None) and pos.x() > x_max:
            return False
        if (y_min is not None) and pos.y() < y_min:
            return False
        if (y_max is not None) and pos.y() > y_max:
            return False
        return True

    def mouseDragEvent(self, ev) -> None:
        if not ev.isAccepted():
            if self.translatable and ev.button() == QtCore.Qt.LeftButton and ev.modifiers() == QtCore.Qt.NoModifier:
                is_start = ev.isStart()
                is_finish = ev.isFinish()
                ev.accept()
                if is_start:
                    self.setSelected(True)
                    self._moveStarted()
                if self.isMoving:
                    shift = self.mapToParent(ev.pos()) - self.mapToParent(ev.buttonDownPos())
                    new_pos = self.preMoveState['pos'] + shift
                    self.setPos(new_pos, update=False, finish=False)
                    self._clip_area(update=True, finish=False)
                if is_finish:
                    self._moveFinished()
            else:
                ev.ignore()
