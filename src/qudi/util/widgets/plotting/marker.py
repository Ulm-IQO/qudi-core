# -*- coding: utf-8 -*-

"""
This file contains customized pyqtgraph graphics items to be used as data marker in 1D and 2D plots.
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

__all__ = ['InfiniteCrosshair']

import numpy as np
from math import isinf
from typing import Union, Tuple, Optional, List, Sequence, Any

from PySide2 import QtCore, QtGui
from pyqtgraph import InfiniteLine, ViewBox, ROI
from pyqtgraph import TargetItem as _TargetItem


class InfiniteCrosshair(QtCore.QObject):
    """ Represents a crosshair (two perpendicular infinite lines) """

    _default_pen = {'color': '#00ff00', 'width': 1}
    _default_hover_pen = {'color': '#ffff00', 'width': 1}

    sigPositionChanged = QtCore.Signal(tuple)  # current_pos
    # start_pos, current_pos, is_start, is_finished
    sigPositionDragged = QtCore.Signal(tuple, tuple, bool, bool)

    def __init__(self,
                 viewbox: ViewBox,
                 position: Optional[Tuple[float, float]] = (0, 0),
                 bounds: Optional[Sequence[Tuple[Union[None, float], Union[None, float]]]] = None,
                 movable: Optional[bool] = True,
                 pen: Optional[Any] = None,
                 hover_pen: Optional[Any] = None,
                 ) -> None:
        super().__init__(parent=viewbox)
        if position is None:
            position = (0, 0)
        if movable is None:
            movable = True
        if pen is None:
            pen = self._default_pen
        if hover_pen is None:
            hover_pen = self._default_hover_pen

        self._bounds = self._normalize_bounds(bounds)
        self._z_value = None
        self.__is_dragged = False
        self.vline = InfiniteLine(pos=position[0],
                                  angle=90,
                                  movable=movable,
                                  pen=pen,
                                  hoverPen=hover_pen)
        self.hline = InfiniteLine(pos=position[1],
                                  angle=0,
                                  movable=movable,
                                  pen=pen,
                                  hoverPen=hover_pen)

        self.vline.sigDragged.connect(self._line_dragged)
        self.vline.sigPositionChangeFinished.connect(self._line_position_change_finished)
        self.hline.sigDragged.connect(self._line_dragged)
        self.hline.sigPositionChangeFinished.connect(self._line_position_change_finished)
        self.show()

    def movable(self) -> bool:
        return bool(self.vline.movable)

    def set_movable(self, movable: bool) -> None:
        """ (Un-)Set the crosshair movable (draggable by mouse cursor) """
        self.vline.setMovable(movable)
        self.hline.setMovable(movable)

    movable = property(movable, set_movable)

    def z_value(self) -> Union[None, int]:
        return self._z_value

    def set_z_value(self, value: int) -> None:
        """ (Un-)Set the crosshair movable (draggable by mouse cursor) """
        self.vline.setZValue(value)
        self.hline.setZValue(value)
        self._z_value = value

    z_value = property(z_value, set_z_value)

    @property
    def position(self) -> Tuple[float, float]:
        return self.vline.value(), self.hline.value()

    def set_position(self, pos: Tuple[float, float]) -> None:
        self.vline.blockSignals(True)
        self.hline.blockSignals(True)
        try:
            self.vline.setPos(pos[0])
            self.hline.setPos(pos[1])
        finally:
            self.vline.blockSignals(False)
            self.hline.blockSignals(False)
        self.sigPositionChanged.emit(self.position)

    @property
    def bounds(self) -> List[Tuple[Union[None, float], Union[None, float]]]:
        return self._bounds.copy()

    def set_bounds(self,
                   bounds: Union[None, Sequence[Tuple[Union[None, float], Union[None, float]]]]
                   ) -> None:
        """ Sets a range boundary for the crosshair position """
        self._bounds = self._normalize_bounds(bounds)
        self.vline.setBounds(self._bounds[0])
        self.hline.setBounds(self._bounds[1])

    def show(self):
        view = self.parent()
        if self.vline not in view.items():
            view.addItem(self.vline)
            view.addItem(self.hline)
            if self._z_value is not None:
                self.vline.setZValue(self._z_value)
                self.hline.setZValue(self._z_value)

    def hide(self):
        view = self.parent()
        if self.vline in view.items():
            view.removeItem(self.vline)
            view.removeItem(self.hline)

    def set_pen(self, pen: Any) -> None:
        """ Sets the pen to be used for drawing the crosshair lines.
        Given parameter must be compatible with pyqtgraph.mkPen()
        """
        self.vline.setPen(pen)
        self.hline.setPen(pen)

    def set_hover_pen(self, pen: Any) -> None:
        """ Sets the pen to be used for drawing the crosshair lines when the mouse cursor is
        hovering over them.
        Given parameter must be compatible with pyqtgraph.mkPen()
        """
        self.vline.setHoverPen(pen)
        self.hline.setHoverPen(pen)

    @staticmethod
    def _normalize_bounds(
            bounds: Union[None, Sequence[Tuple[Union[None, float], Union[None, float]]]]
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

    def _line_dragged(self, line: Optional[InfiniteLine] = None) -> None:
        if self.__is_dragged:
            is_start = False
        else:
            self.__is_dragged = True
            is_start = True

        current_pos = self.position
        if line is self.vline:
            start_pos = (self.vline.startPosition[0], current_pos[1])
        else:
            start_pos = (current_pos[0], self.hline.startPosition[1])

        if line.moving:
            is_end = False
        else:
            self.__is_dragged = False
            is_end = True

        self.sigPositionDragged.emit(start_pos, current_pos, is_start, is_end)

    def _line_position_change_finished(self, line: Optional[InfiniteLine] = None) -> None:
        self.sigPositionChanged.emit(self.position)


class RectGraphicsItem(ROI):
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

    def movable(self) -> bool:
        return self.translatable

    def set_movable(self, movable: bool) -> None:
        self.translatable = bool(movable)

    movable = property(movable, set_movable)

    def z_value(self) -> Union[None, int]:
        return self._z_value

    def set_z_value(self, value: int) -> None:
        """ (Un-)Set the crosshair movable (draggable by mouse cursor) """
        self.vline.setZValue(value)
        self.hline.setZValue(value)
        self._z_value = value

    z_value = property(z_value, set_z_value)

    @property
    def position(self) -> Tuple[float, float]:
        return self.vline.value(), self.hline.value()

    def set_position(self, pos: Tuple[float, float]) -> None:
        self.vline.blockSignals(True)
        self.hline.blockSignals(True)
        try:
            self.vline.setPos(pos[0])
            self.hline.setPos(pos[1])
        finally:
            self.vline.blockSignals(False)
            self.hline.blockSignals(False)
        self.sigPositionChanged.emit(self.position)

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
