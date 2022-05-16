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

__all__ = ['InfiniteCrosshair', 'InfiniteLine', 'LinearRegion', 'Rectangle']

from math import isinf
from typing import Union, Tuple, Optional, List, Sequence, Any

from PySide2 import QtCore
from pyqtgraph import ViewBox, ROI, LinearRegionItem
from pyqtgraph import InfiniteLine as _InfiniteLine
from qudi.util.widgets.plotting.roi import RectangleROI


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
        self.vline = _InfiniteLine(pos=position[0],
                                   bounds=self._bounds[0],
                                   angle=90,
                                   movable=movable,
                                   pen=pen,
                                   hoverPen=hover_pen)
        self.hline = _InfiniteLine(pos=position[1],
                                   bounds=self._bounds[1],
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
        if self.vline not in view.addedItems:
            view.addItem(self.vline)
            view.addItem(self.hline)
            if self._z_value is not None:
                self.vline.setZValue(self._z_value)
                self.hline.setZValue(self._z_value)

    def hide(self):
        view = self.parent()
        try:
            view.removeItem(self.vline)
            view.removeItem(self.hline)
        except:
            pass

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

    def _line_dragged(self, line: Optional[_InfiniteLine] = None) -> None:
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

    def _line_position_change_finished(self, line: Optional[_InfiniteLine] = None) -> None:
        self.sigPositionChanged.emit(self.position)


class InfiniteLine(QtCore.QObject):
    """ Represents a horizontal or vertical infinite line data marker """

    _default_pen = {'color': '#00ff00', 'width': 1}
    _default_hover_pen = {'color': '#ffff00', 'width': 1}

    sigPositionChanged = QtCore.Signal(object)  # current_pos
    # start_pos, current_pos, is_start, is_finished
    sigPositionDragged = QtCore.Signal(object, object, bool, bool)

    def __init__(self,
                 viewbox: ViewBox,
                 orientation: QtCore.Qt.Orientation,
                 position: Optional[float] = 0,
                 bounds: Optional[Tuple[Union[None, float]]] = None,
                 movable: Optional[bool] = True,
                 pen: Optional[Any] = None,
                 hover_pen: Optional[Any] = None,
                 ) -> None:
        super().__init__(parent=viewbox)
        if position is None:
            position = 0
        if movable is None:
            movable = True
        if pen is None:
            pen = self._default_pen
        if hover_pen is None:
            hover_pen = self._default_hover_pen

        self._bounds = self._normalize_bounds(bounds)
        self._z_value = None
        self.__is_dragged = False
        self.line = _InfiniteLine(pos=position,
                                  angle=0 if orientation is QtCore.Qt.Horizontal else 90,
                                  movable=movable,
                                  pen=pen,
                                  hoverPen=hover_pen)

        self.line.sigDragged.connect(self._line_dragged)
        self.line.sigPositionChangeFinished.connect(self._line_position_change_finished)

        self.show()

    @property
    def orientation(self) -> QtCore.Qt.Orientation:
        return QtCore.Qt.Vertical if self.line.angle == 90 else QtCore.Qt.Horizontal

    def movable(self) -> bool:
        return bool(self.line.movable)

    def set_movable(self, movable: bool) -> None:
        self.line.setMovable(movable)

    movable = property(movable, set_movable)

    def z_value(self) -> Union[None, int]:
        return self._z_value

    def set_z_value(self, value: int) -> None:
        self.line.setZValue(value)
        self._z_value = value

    z_value = property(z_value, set_z_value)

    @property
    def position(self) -> float:
        return self.line.value()

    def set_position(self, position: float) -> None:
        self.line.blockSignals(True)
        try:
            self.line.setPos(position)
        finally:
            self.line.blockSignals(False)
        self.sigPositionChanged.emit(self.position)

    @property
    def bounds(self) -> Tuple[Union[None, float], Union[None, float]]:
        return self._bounds

    def set_bounds(self,
                   bounds: Union[None, Tuple[Union[None, float], Union[None, float]]]
                   ) -> None:
        """ Sets a range boundary for the line position """
        self._bounds = self._normalize_bounds(bounds)
        self.line.setBounds(self._bounds)

    def show(self):
        view = self.parent()
        if self.line not in view.addedItems:
            view.addItem(self.line)
            if self._z_value is not None:
                self.line.setZValue(self._z_value)

    def hide(self):
        try:
            self.parent().removeItem(self.line)
        except:
            pass

    def set_pen(self, pen: Any) -> None:
        """ Sets the pen to be used for drawing the line.
        Given parameter must be compatible with pyqtgraph.mkPen()
        """
        self.line.setPen(pen)

    def set_hover_pen(self, pen: Any) -> None:
        """ Sets the pen to be used for drawing the line when the mouse cursor is hovering over it.
        Given parameter must be compatible with pyqtgraph.mkPen()
        """
        self.line.setHoverPen(pen)

    @staticmethod
    def _normalize_bounds(bounds: Union[None, Tuple[Union[None, float], Union[None, float]]]
                          ) -> Tuple[Union[None, float], Union[None, float]]:
        if bounds is None:
            bounds = (None, None)
        else:
            # Replace inf values by None
            try:
                if isinf(bounds[0]):
                    bounds = (None, bounds[1])
            except TypeError:
                pass
            try:
                if isinf(bounds[1]):
                    bounds = (bounds[0], None)
            except TypeError:
                pass
            # Sort spans in ascending order
            try:
                bounds = tuple(sorted(bounds))
            except TypeError:
                bounds = tuple(bounds)
        return bounds

    def _line_dragged(self, line: Optional[_InfiniteLine] = None) -> None:
        if self.__is_dragged:
            is_start = False
        else:
            self.__is_dragged = True
            is_start = True

        current_pos = self.position
        start_pos = self.line.startPosition[0 if self.line.angle == 90 else 1]

        if line.moving:
            is_finished = False
        else:
            self.__is_dragged = False
            is_finished = True

        self.sigPositionDragged.emit(start_pos, current_pos, is_start, is_finished)

    def _line_position_change_finished(self, line: Optional[_InfiniteLine] = None) -> None:
        self.sigPositionChanged.emit(self.position)


class LinearRegion(QtCore.QObject):
    """
    """
    _default_pen = {'color': '#00ff00', 'width': 1}
    _default_hover_pen = {'color': '#ffff00', 'width': 1}
    _default_brush = None
    _default_hover_brush = None

    sigAreaChanged = QtCore.Signal(tuple)  # current_area
    # start_area, current_area, is_start, is_finished
    sigAreaDragged = QtCore.Signal(tuple, tuple, bool, bool)

    def __init__(self,
                 viewbox: ViewBox,
                 orientation: QtCore.Qt.Orientation,
                 span: Optional[Tuple[float, float]] = (0, 1),
                 bounds: Optional[Tuple[Union[None, float], Union[None, float]]] = None,
                 movable: Optional[bool] = True,
                 pen: Optional[Any] = None,
                 hover_pen: Optional[Any] = None,
                 brush: Optional[Any] = None,
                 hover_brush: Optional[Any] = None
                 ) -> None:
        super().__init__(parent=viewbox)
        if span is None:
            span = (0, 1)
        if movable is None:
            movable = True
        if pen is None:
            pen = self._default_pen
        if hover_pen is None:
            hover_pen = self._default_hover_pen
        if brush is None:
            brush = self._default_brush
        if hover_brush is None:
            hover_brush = self._default_hover_brush
        orientation = 'vertical' if orientation == QtCore.Qt.Vertical else 'horizontal'

        self._bounds = self._normalize_bounds(bounds)
        self.region = LinearRegionItem(values=span,
                                       orientation=orientation,
                                       brush=brush,
                                       pen=pen,
                                       hoverBrush=hover_brush,
                                       hoverPen=hover_pen,
                                       movable=movable,
                                       bounds=self._bounds,
                                       swapMode='sort')

        self._z_value = None
        self.__is_dragged = False
        self.__start_area = self.area

        self.region.sigRegionChangeFinished.connect(self._region_change_finished)
        self.region.sigRegionChanged.connect(self._region_changed)

        self.show()

    @property
    def orientation(self) -> QtCore.Qt.Orientation:
        return QtCore.Qt.Vertical if self.region.orientation == 'vertical' else QtCore.Qt.Horizontal

    def movable(self) -> bool:
        return self.roi.translatable

    def set_movable(self, movable: bool) -> None:
        self.roi.translatable = bool(movable)

    movable = property(movable, set_movable)

    def z_value(self) -> Union[None, int]:
        return self._z_value

    def set_z_value(self, value: int) -> None:
        self.region.setZValue(value)
        self._z_value = value

    z_value = property(z_value, set_z_value)

    @property
    def area(self) -> Tuple[float, float]:
        return self.region.getRegion()

    def set_area(self, area: Tuple[float, float]) -> None:
        self.region.blockSignals(True)
        try:
            self.region.setRegion(area)
        finally:
            self.region.blockSignals(False)
        self.sigAreaChanged.emit(self.area)

    @property
    def bounds(self) -> Tuple[Union[None, float], Union[None, float]]:
        return self._bounds

    def set_bounds(self,
                   bounds: Union[None, Tuple[Union[None, float], Union[None, float]]]
                   ) -> None:
        self._bounds = self._normalize_bounds(bounds)
        self.region.setBounds(self._bounds)

    def show(self):
        view = self.parent()
        if self.region not in view.addedItems:
            view.addItem(self.region)
            if self._z_value is not None:
                self.region.setZValue(self._z_value)

    def hide(self):
        try:
            self.parent().removeItem(self.region)
        except:
            pass

    def set_pen(self, pen: Any) -> None:
        """ Sets the pen to be used for drawing the lines.
        Given parameter must be compatible with pyqtgraph.mkPen()
        """
        for line in self.region.lines:
            line.setPen(pen)

    def set_hover_pen(self, pen: Any) -> None:
        """ Sets the pen to be used for drawing the lines when the mouse cursor is hovering over it.
        Given parameter must be compatible with pyqtgraph.mkPen()
        """
        for line in self.region.lines:
            line.setHoverPen(pen)

    def set_brush(self, brush: Any) -> None:
        """ Sets the brush to be used for filling the area between the lines.
        Given parameter must be compatible with pyqtgraph.mkBrush()
        """
        self.region.setBrush(brush)

    def set_hover_brush(self, brush: Any) -> None:
        """ Sets the brush to be used for filling the area between the lines when the mouse cursor
        is hovering over it.
        Given parameter must be compatible with pyqtgraph.mkBrush()
        """
        self.region.setHoverBrush(brush)

    @staticmethod
    def _normalize_bounds(bounds: Union[None, Tuple[Union[None, float], Union[None, float]]]
                          ) -> Tuple[Union[None, float], Union[None, float]]:
        if bounds is None:
            bounds = (None, None)
        else:
            # Replace inf values by None
            try:
                if isinf(bounds[0]):
                    bounds = (None, bounds[1])
            except TypeError:
                pass
            try:
                if isinf(bounds[1]):
                    bounds = (bounds[0], None)
            except TypeError:
                pass
            # Sort spans in ascending order
            try:
                bounds = tuple(sorted(bounds))
            except TypeError:
                bounds = tuple(bounds)
        return bounds

    def _region_changed(self, obj: Optional[LinearRegionItem] = None) -> None:
        if self.__is_dragged:
            is_start = False
        else:
            self.__is_dragged = True
            is_start = True
            if self.region.orientation == 'vertical':
                self.__start_area = tuple(pos[0] for pos in self.region.startPositions)
            else:
                self.__start_area = tuple(pos[1] for pos in self.region.startPositions)

        if self.region.moving:
            is_finished = False
        else:
            self.__is_dragged = False
            is_finished = True

        self.sigAreaDragged.emit(self.__start_area, self.area, is_start, is_finished)

    def _region_change_finished(self, obj: Optional[LinearRegionItem] = None) -> None:
        current_area = self.area
        if self.__is_dragged:
            self.__is_dragged = False
            self.sigAreaDragged.emit(self.__start_area, current_area, False, True)
        self.sigAreaChanged.emit(current_area)


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
                 hover_pen: Optional[Any] = None
                 ) -> None:
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

        self.roi = RectangleROI(pos=self._center_to_roi_pos(position, size),
                                size=size,
                                bounds=bounds,
                                movable=movable,
                                resizable=resizable,
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
        self.roi.sigRegionChanged.connect(self._roi_changed)
        self.roi.sigRegionChangeFinished.connect(self._roi_change_finished)
        self.roi.sigRegionChangeStarted.connect(self._roi_change_started)

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
        center = self.roi.area.center()
        return center.x(), center.y()

    def set_position(self, position: Tuple[float, float]) -> None:
        old_area = self.roi.area
        center = old_area.center()
        new_area = old_area.translated(position[0] - center.x(), position[1] - center.y())
        self.roi.set_area(new_area)

    @property
    def size(self) -> Tuple[float, float]:
        area = self.roi.area
        return abs(area.width()), abs(area.height())

    def set_size(self, size: Tuple[float, float]) -> None:
        size = abs(size[0]), abs(size[1])
        current_pos = self.position
        new_area = self.roi.normalize_rect(
            pos=(current_pos[0] - size[0] / 2, current_pos[1] - size[1] / 2),
            size=size
        )
        self.roi.set_area(new_area)

    @property
    def area(self) -> QtCore.QRectF:
        return self.roi.area

    def set_area(self, area: QtCore.QRectF) -> None:
        return self.roi.set_area(area)

    @property
    def bounds(self) -> List[Tuple[Union[None, float], Union[None, float]]]:
        return self.roi.bounds

    def set_bounds(self,
                   bounds: Union[None, Sequence[Tuple[Union[None, float], Union[None, float]]]]
                   ) -> None:
        return self.roi.set_bounds(bounds)

    def show(self):
        view = self.parent()
        if self.roi not in view.addedItems:
            view.addItem(self.roi)
            if self._z_value is not None:
                self.roi.setZValue(self._z_value)

    def hide(self):
        try:
            self.parent().removeItem(self.roi)
        except:
            pass

    def set_pen(self, pen: Any) -> None:
        """ Given parameter must be compatible with pyqtgraph.mkPen() """
        self.roi.setPen(pen)

    def set_hover_pen(self, pen: Any) -> None:
        """ Given parameter must be compatible with pyqtgraph.mkPen() """
        self.roi.setHoverPen(pen)

    @staticmethod
    def _center_to_roi_pos(position: Tuple[float, float],
                           size: Tuple[float, float]
                           ) -> Tuple[float, float]:
        return position[0] - size[0] / 2, position[1] - size[1] / 2

    def _roi_change_started(self, roi: Optional[ROI] = None) -> None:
        self.__start_area = self.area
        self.__is_dragged = True
        self.sigAreaDragged.emit(self.__start_area, self.__start_area, True, False)

    def _roi_change_finished(self, roi: Optional[ROI] = None) -> None:
        current_area = self.area
        if self.__is_dragged:
            self.__is_dragged = False
            self.sigAreaDragged.emit(self.__start_area, current_area, False, True)
        self.sigAreaChanged.emit(current_area)

    def _roi_changed(self, roi: Optional[ROI] = None) -> None:
        if self.__is_dragged:
            self.sigAreaDragged.emit(self.__start_area, self.area, False, False)

