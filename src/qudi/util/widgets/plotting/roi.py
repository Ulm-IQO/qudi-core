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
                 pos=(0, 0),
                 size=(1, 1),
                 bounds=None,
                 apply_bounds_to_center=False,
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
                     (0, 0),
                     size=(1, 1),
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
        self.__center_position = (0, 0)
        self.__norm_size = (1, 1)
        self.__min_norm_size = (0, 0)
        self.__start_pos = (0, 0)
        self._apply_bounds_to_center = bool(apply_bounds_to_center)
        self._bounds = self.normalize_bounds(bounds)
        self.set_area(position=pos, size=size)

    @property
    def min_size(self) -> Tuple[float, float]:
        return self.__min_norm_size

    def set_min_size(self, size: Union[None, Tuple[float, float]]) -> None:
        self.__min_norm_size = (0, 0) if size is None else (abs(size[0]), abs(size[1]))
        self.set_area(size=self.__norm_size)

    @property
    def area(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        return self.__center_position, self.__norm_size

    def set_area(self,
                 position: Optional[Tuple[float, float]] = None,
                 size: Optional[Tuple[float, float]] = None
                 ) -> None:
        if position is not None:
            constr_size = (max(self.__norm_size[0], self.__min_norm_size[0]),
                           max(self.__norm_size[1], self.__min_norm_size[1]))
            self.setPos(QtCore.QPointF(position[0] - constr_size[0] / 2,
                                       position[1] + constr_size[1] / 2),
                        update=False,
                        finish=False)
            self.__center_position = (position[0], position[1])
        if size is not None:
            size = (abs(size[0]), abs(size[1]))
            constr_size = (max(size[0], self.__min_norm_size[0]),
                           max(size[1], self.__min_norm_size[1]))
            self.setSize(QtCore.QPointF(constr_size[0], -constr_size[1]),
                         center=(0.5, 0.5),
                         update=False,
                         finish=False)
            self.__norm_size = size
        if position is not None and size is not None:
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
        position = list(self.__center_position)
        size = list(self.__norm_size)
        x_min, x_max = self._bounds[0]
        y_min, y_max = self._bounds[1]
        if self._apply_bounds_to_center:
            if (x_min is not None) and (position[0] < x_min):
                position[0] = x_min
            elif (x_max is not None) and (position[0] > x_max):
                position[0] = x_max
            if (y_min is not None) and (position[1] < y_min):
                position[1] = y_min
            elif (y_max is not None) and (position[1] > y_max):
                position[1] = y_max
        else:
            left = position[0] - size[0] / 2
            right = position[0] + size[0] / 2
            top = position[1] + size[1] / 2
            bottom = position[1] - size[1] / 2
            if (x_min is not None) and (left < x_min):
                position[0] = x_min + size[0] / 2
            elif (x_max is not None) and (right > x_max):
                position[0] = x_max - size[0] / 2
            if (y_min is not None) and (bottom < y_min):
                position[1] = y_min + size[1] / 2
            elif (y_max is not None) and (top > y_max):
                position[1] = y_max - size[1] / 2
        translate = (position[0] - self.__center_position[0],
                     position[1] - self.__center_position[1])
        self.__center_position = tuple(position)
        self.translate(translate, update=update, finish=finish)

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

    def checkPointMove(self, handle, pos, modifiers):
        if not self._apply_bounds_to_center:
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

    def cancelMove(self) -> None:
        if self.isMoving:
            self.__center_position = self.__start_pos
        return super().cancelMove()

    def mouseDragEvent(self, ev) -> None:
        if not ev.isAccepted():
            if self.translatable and ev.button() == QtCore.Qt.LeftButton and ev.modifiers() == QtCore.Qt.NoModifier:
                is_start = ev.isStart()
                is_finish = ev.isFinish()
                ev.accept()
                if is_start:
                    self.setSelected(True)
                    self._moveStarted()
                    self.__start_pos = self.__center_position
                if self.isMoving:
                    total_move = self.mapToParent(ev.pos()) - self.mapToParent(ev.buttonDownPos())
                    self.__center_position = (self.__start_pos[0] + total_move.x(),
                                              self.__start_pos[1] + total_move.y())
                    new_pos = self.preMoveState['pos'] + total_move
                    self.setPos(new_pos, update=False, finish=False)
                    self._clip_area(update=True, finish=False)
                if is_finish:
                    self._moveFinished()
            else:
                ev.ignore()
