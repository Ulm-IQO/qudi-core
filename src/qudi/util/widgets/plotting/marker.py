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
        if self.vline not in view.childItems():
            view.addItem(self.vline)
            view.addItem(self.hline)
            if self._z_value is not None:
                self.vline.setZValue(self._z_value)
                self.hline.setZValue(self._z_value)

    def hide(self):
        view = self.parent()
        if self.vline in view.childItems():
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
            is_finished = False
        else:
            self.__is_dragged = False
            is_finished = True

        self.sigPositionDragged.emit(start_pos, current_pos, is_start, is_finished)

    def _line_position_change_finished(self, line: Optional[InfiniteLine] = None) -> None:
        self.sigPositionChanged.emit(self.position)


class Rectangle(QtCore.QObject):
    """
    """

    _default_pen = {'color': '#00ff00', 'width': 1}
    _default_hover_pen = {'color': '#ffff00', 'width': 1}

    sigAreaChanged = QtCore.Signal(QtCore.QRectF)  # current_area
    # start_area, current_area, is_start, is_finished
    sigAreaDragged = QtCore.Signal(QtCore.QRectF, QtCore.QRectF, bool, bool)

    def __init__(self,
                 viewbox: ViewBox,
                 position: Optional[Tuple[float, float]] = (0, 0),
                 size: Optional[Tuple[float, float]] = (1, 1),
                 edge_handles: Optional[bool] = False,
                 corner_handles: Optional[bool] = False,
                 bounds: Optional[Sequence[Tuple[Union[None, float], Union[None, float]]]] = None,
                 movable: Optional[bool] = True,
                 resizable: Optional[bool] = True,
                 pen: Optional[Any] = None,
                 hover_pen: Optional[Any] = None):
        super().__init__(parent=viewbox)
        if position is None:
            position = (0, 0)
        if size is None:
            size = (1, 1)
        if movable is None:
            movable = True
        if resizable is None:
            resizable = True
        if pen is None:
            pen = self._default_pen
        if hover_pen is None:
            hover_pen = self._default_hover_pen

        self.roi = ROI(pos=self._center_to_roi_pos(position, size),
                       size=size,
                       movable=movable,
                       resizable=resizable,
                       rotatable=False,
                       invertible=True,
                       pen=pen,
                       hoverPen=hover_pen,
                       handlePen=pen,
                       handleHoverPen=hover_pen)
        if corner_handles:
            self.roi.addScaleHandle([1, 1], [0, 0])
            self.roi.addScaleHandle([0, 0], [1, 1])
            self.roi.addScaleHandle([1, 0], [0, 1])
            self.roi.addScaleHandle([0, 1], [1, 0])
        if edge_handles:
            self.roi.addScaleHandle([1, 0.5], [0, 0.5])
            self.roi.addScaleHandle([0.5, 1], [0.5, 0])
            self.roi.addScaleHandle([0, 0.5], [1, 0.5])
            self.roi.addScaleHandle([0.5, 0], [0.5, 1])
        self.roi.sigRegionChanged.connect(self._roi_dragged)
        self.roi.sigRegionChangeFinished.connect(self._roi_drag_finished)
        self.roi.sigRegionChangeStarted.connect(self._roi_drag_started)

        self._bounds = self._normalize_bounds(bounds)
        self._z_value = None
        self.__is_dragged = False
        self.__start_area = self.area

        self.show()

    def movable(self) -> bool:
        return self.roi.translatable

    def set_movable(self, movable: bool) -> None:
        self.roi.translatable = bool(movable)

    movable = property(movable, set_movable)

    def resizable(self) -> bool:
        return self.roi.resizable

    def set_resizable(self, resizable: bool) -> None:
        self.roi.resizable = bool(resizable)

    resizable = property(resizable, set_resizable)

    def z_value(self) -> Union[None, int]:
        return self._z_value

    def set_z_value(self, value: int) -> None:
        """ (Un-)Set the crosshair movable (draggable by mouse cursor) """
        self.roi.setZValue(value)
        self._z_value = value

    z_value = property(z_value, set_z_value)

    @property
    def position(self) -> Tuple[float, float]:
        center = QtCore.QRectF(*self.roi.pos(), *self.roi.size()).center()
        return center.x(), center.y()

    def set_position(self, position: Tuple[float, float]) -> None:
        old_area = self.area
        self._set_roi_area(self._clip_area(self._pos_size_to_area(position, self.size)))
        new_area = self.area
        if old_area != new_area:
            self.sigAreaChanged.emit(new_area)

    @property
    def size(self) -> Tuple[float, float]:
        size = self.roi.size()
        return abs(size[0]), abs(size[1])

    def set_size(self, size: Tuple[float, float]) -> None:
        size = abs(size[0]), abs(size[1])
        old_area = self.area
        self._set_roi_area(self._clip_area(self._pos_size_to_area(self.position, size)))
        new_area = self.area
        if old_area != new_area:
            self.sigAreaChanged.emit(self.area)

    @property
    def area(self) -> QtCore.QRectF:
        return self._pos_size_to_area(self.position, self.size)

    def set_area(self, area: QtCore.QRectF) -> None:
        old_area = self.area
        self._set_roi_area(area)
        new_area = self.area
        if old_area != new_area:
            self.sigAreaChanged.emit(new_area)

    @property
    def bounds(self) -> List[Tuple[Union[None, float], Union[None, float]]]:
        return self._bounds.copy()

    def set_bounds(self,
                   bounds: Union[None, Sequence[Tuple[Union[None, float], Union[None, float]]]]
                   ) -> None:
        self._bounds = self._normalize_bounds(bounds)
        old_area = self.area
        self._correct_roi_area()
        new_area = self.area
        if old_area != new_area:
            self.sigAreaChanged.emit(new_area)

    def show(self):
        view = self.parent()
        if self.roi not in view.childItems():
            view.addItem(self.roi)
            if self._z_value is not None:
                self.roi.setZValue(self._z_value)

    def hide(self):
        view = self.parent()
        if self.roi in view.childItems():
            view.removeItem(self.roi)

    def set_pen(self, pen: Any) -> None:
        """ Given parameter must be compatible with pyqtgraph.mkPen() """
        self.roi.setPen(pen)

    def set_hover_pen(self, pen: Any) -> None:
        """ Given parameter must be compatible with pyqtgraph.mkPen() """
        self.roi.setHoverPen(pen)

    def _clip_area(self, area: QtCore.QRectF) -> QtCore.QRectF:
        clipped_area = QtCore.QRectF(area)
        x_min, x_max = self._bounds[0]
        y_min, y_max = self._bounds[1]
        if (x_min is not None) and (area.left() < x_min):
            clipped_area.setLeft(x_min)
            clipped_area.setRight(min(x_min + area.width(), x_max))
        elif (x_max is not None) and (area.right() > x_max):
            clipped_area.setRight(x_max)
            clipped_area.setLeft(max(x_max - area.width(), x_min))
        if (y_min is not None) and (area.bottom() < y_min):
            clipped_area.setBottom(y_min)
            clipped_area.setTop(min(y_min + abs(area.height()), y_max))
        elif (y_max is not None) and (area.top() > y_max):
            clipped_area.setTop(y_max)
            clipped_area.setBottom(max(y_max - abs(area.height()), y_min))
        return clipped_area

    def _set_roi_area(self, area: QtCore.QRectF) -> None:
        self.roi.blockSignals(True)
        try:
            self.roi.setSize(area.size())
            self.roi.setPos(area.topLeft())
        finally:
            self.roi.blockSignals(False)

    def _correct_roi_area(self) -> None:
        area = self.area
        corr_area = self._clip_area(area)
        if area != corr_area:
            self._set_roi_area(corr_area)

    @staticmethod
    def _center_to_roi_pos(position: Tuple[float, float],
                           size: Tuple[float, float]
                           ) -> Tuple[float, float]:
        return position[0] - size[0] / 2, position[1] - size[1] / 2

    @staticmethod
    def _roi_to_center_pos(position: Tuple[float, float],
                           size: Tuple[float, float]
                           ) -> Tuple[float, float]:
        return position[0] + size[0] / 2, position[1] + size[1] / 2

    @staticmethod
    def _pos_size_to_area(center: Tuple[float, float],
                          size: Tuple[float, float]
                          ) -> QtCore.QRectF:
        return QtCore.QRectF(center[0] - size[0] / 2,
                             center[1] + size[1] / 2,
                             size[0],
                             -size[1])

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

    def _roi_drag_started(self, roi: Optional[ROI] = None) -> None:
        print('drag started')
        self.__start_area = self.area

    def _roi_drag_finished(self, roi: Optional[ROI] = None) -> None:
        print('drag finished', self.roi.pos())
        self.__is_dragged = False
        self.sigAreaDragged.emit(self.__start_area, self.area, False, True)
        self.sigAreaChanged.emit(self.area)

    def _roi_dragged(self, roi: Optional[ROI] = None) -> None:
        is_start = not self.__is_dragged
        self.__is_dragged = True
        self._correct_roi_area()

