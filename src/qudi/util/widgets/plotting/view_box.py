# -*- coding: utf-8 -*-

"""
This file contains modified pyqtgraph ViewBoxes for qudi to track mouse activity and provide
advanced functionality inside data plots.

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

__all__ = ['MouseTrackingViewBox', 'DataSelectionViewBox']

from typing import Optional, Union, Any, Tuple, Mapping
from enum import IntEnum

import numpy as np
from PySide2 import QtCore
from pyqtgraph import ViewBox, SignalProxy, InfiniteLine, LinearRegionItem
from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent, MouseDragEvent
from qudi.util.widgets.plotting.roi import TargetItem


class MouseTrackingViewBox(ViewBox):
    """ Extension for pg.ViewBox to tap into mouse move/click/drag events and emit signals.

    x-y-positions emitted will be in real world data coordinates.
    """

    # position (x, y)
    sigMouseMoved = QtCore.Signal(tuple)
    # start_position (x, y), current_position (x, y), MouseDragEvent
    sigMouseDragged = QtCore.Signal(tuple, tuple, object)
    # position (x, y), MouseClickEvent
    sigMouseClicked = QtCore.Signal(tuple, object)

    def __init__(self, *args, max_mouse_pos_update_rate: Optional[float] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if max_mouse_pos_update_rate is not None and max_mouse_pos_update_rate > 0.:
            self._mouse_position_signal_proxy = SignalProxy(
                signal=self.scene().sigMouseMoved,
                rateLimit=max_mouse_pos_update_rate,
                delay=2 / max_mouse_pos_update_rate,  # Must be larger than 1/rateLimit
                slot=self.__mouse_moved
            )

    def __mouse_moved(self, args) -> None:
        pos = self.mapSceneToView(args[0])
        self.sigMouseMoved.emit((pos.x(), pos.y()))

    def mouseClickEvent(self, ev: MouseClickEvent) -> None:
        pos = self.mapToView(ev.pos())
        self.sigMouseClicked.emit((pos.x(), pos.y()), ev)
        if not ev.isAccepted():
            super().mouseClickEvent(ev)

    def mouseDragEvent(self, ev: MouseDragEvent, axis: Optional[int] = None) -> None:
        start = self.mapToView(ev.buttonDownPos())
        current = self.mapToView(ev.pos())
        self.sigMouseDragged.emit((start.x(), start.y()), (current.x(), current.y()), ev)
        if not ev.isAccepted():
            super().mouseDragEvent(ev, axis)


class DataSelectionViewBox(MouseTrackingViewBox):
    """ Expands MouseTrackingViewBox with data selection functionality.

    You can select:
        - linear region in x or y
        - xy ROIs
        - x, y or xy data markers

    Public methods will generally emit signals if they result in a selection change. The
    corresponding "protected" methods do not emit.

    ToDo: Implement XY selection mode (ROIs and points)
    """

    class SelectionMode(IntEnum):
        Disabled = 0
        X = 1
        Y = 2
        XY = 3

    sigMarkerSelectionChanged = QtCore.Signal(dict)
    sigRegionSelectionChanged = QtCore.Signal(dict)

    def __init__(self,
                 *args,
                 x_selection_limits: Optional[Tuple[float, float]] = None,
                 y_selection_limits: Optional[Tuple[float, float]] = None,
                 selection_pens: Optional[Mapping[str, Any]] = None,
                 selection_brushes: Optional[Mapping[str, Any]] = None,
                 **kwargs
                 ) -> None:
        super().__init__(*args, **kwargs)
        if x_selection_limits is not None:
            x_selection_limits = (min(x_selection_limits), max(x_selection_limits))
        if y_selection_limits is not None:
            y_selection_limits = (min(y_selection_limits), max(y_selection_limits))
        self._selection_pens = dict() if selection_pens is None else selection_pens.copy()
        self._selection_brushes = dict() if selection_brushes is None else selection_brushes.copy()
        self._region_selection_mode = self.SelectionMode.Disabled
        self._marker_selection_mode = self.SelectionMode.Disabled
        self._selection_movable = True
        self._selection_limits = (x_selection_limits , y_selection_limits)
        self.__regions = list()
        self.__markers = list()

    def mouseClickEvent(self, ev: MouseClickEvent) -> None:
        selection_enabled = self._marker_selection_mode != self.SelectionMode.Disabled
        if selection_enabled and (ev.button() == QtCore.Qt.LeftButton) and not ev.double():
            ev.accept()
            pos = self.mapToView(ev.pos())
            self.add_marker_selection((pos.x(), pos.y()))
        return super().mouseClickEvent(ev)

    def mouseDragEvent(self, ev: MouseDragEvent, axis: Optional[int] = None) -> None:
        selection_enabled = self._region_selection_mode != self.SelectionMode.Disabled
        if selection_enabled and axis is None and (ev.button() == QtCore.Qt.LeftButton) and not ev.isAccepted():
            ev.accept()
            start = self.mapToView(ev.buttonDownPos())
            end = self.mapToView(ev.pos())
            span = ((start.x(), end.x()), (start.y(), end.y()))
            if ev.isStart():
                print('start:', span)
                self._add_region_selection(span)
            else:
                try:
                    print('move:', span)
                    self._move_region_selection(span, index=-1)
                except IndexError:
                    pass
            if ev.isFinish():
                print('finished')
                self._emit_region_change()
        return super().mouseDragEvent(ev, axis)

    def region_selection_mode(self) -> SelectionMode:
        return self._region_selection_mode

    def set_region_selection_mode(self, mode: Union[SelectionMode, int]) -> None:
        self._region_selection_mode = self.SelectionMode(mode)

    region_selection_mode = property(region_selection_mode, set_region_selection_mode)

    def marker_selection_mode(self) -> SelectionMode:
        return self._marker_selection_mode

    def set_marker_selection_mode(self, mode: Union[SelectionMode, int]) -> None:
        self._marker_selection_mode = self.SelectionMode(mode)

    marker_selection_mode = property(marker_selection_mode, set_marker_selection_mode)

    def selection_movable(self) -> bool:
        return self._selection_movable

    def set_selection_movable(self, movable: bool) -> None:
        movable = bool(movable)
        if movable is not self._selection_movable:
            for m in self.__markers:
                m.setMovable(movable)
            for r in self.__regions:
                r.setMovable(movable)
            self._selection_movable = movable

    selection_movable = property(selection_movable, set_selection_movable)

    def selection_limits(self) -> Tuple[Union[None, Tuple[float, float]], Union[None, Tuple[float, float]]]:
        return self._selection_limits

    def set_selection_limits(self,
                             x: Union[None, Tuple[float, float]],
                             y: Union[None, Tuple[float, float]]
                             ) -> None:
        if x is not None:
            x = (min(x), max(x))
        if y is not None:
            y = (min(y), max(y))
        new_limits = (x, y)
        if new_limits != self._selection_limits:
            self._selection_limits = new_limits
            self._apply_selection_limits()

    selection_limits = property(selection_limits, set_selection_limits)

    def add_region_selection(self,
                             span: Tuple[Tuple[float, float], Tuple[float, float]],
                             mode: Optional[Union[SelectionMode, int]] = None,
                             ) -> None:
        self._add_region_selection(span, mode)
        self._emit_region_change()

    def _add_region_selection(self,
                              span: Tuple[Tuple[float, float], Tuple[float, float]],
                              mode: Optional[Union[SelectionMode, int]] = None,
                              ) -> None:
        mode = self._region_selection_mode if mode is None else self.SelectionMode(mode)
        if mode == self.SelectionMode.Disabled:
            return
        elif mode == self.SelectionMode.XY:
            item = RectROI(pos=(min(span[0]), min(span[1])),
                           size=(max(span[0]) - min(span[0]), max(span[1]) - min(span[1])),
                           invertible=False,
                           movable=self._selection_movable,
                           resizable=self._selection_movable,
                           rotatable=False,
                           bounds=self._selection_limits)
            item.sigRegionChangeFinished.connect(self._emit_region_change)
        else:
            if mode == self.SelectionMode.X:
                orientation = 'vertical'
                bounds = self._selection_limits[0]
                values = span[0]
            else:
                orientation = 'horizontal'
                bounds = self._selection_limits[1]
                values = span[1]
            item = LinearRegionItem(values=values,
                                    bounds=bounds,
                                    orientation=orientation,
                                    movable=self._selection_movable,
                                    span=(0, 1),
                                    swapMode='sort',
                                    **self._selection_pens,
                                    **self._selection_brushes)
            item.sigRegionChangeFinished.connect(self._emit_region_change)
        self.addItem(item)
        item.setZValue(1)
        self.__regions.append(item)

    def add_marker_selection(self,
                             position: Tuple[float, float],
                             mode: Optional[Union[SelectionMode, int]] = None,
                             ) -> None:
        self._add_marker_selection(position, mode)
        self._emit_marker_change()

    def _add_marker_selection(self,
                              position: Tuple[float, float],
                              mode: Optional[Union[SelectionMode, int]] = None,
                              ) -> None:
        mode = self._marker_selection_mode if mode is None else self.SelectionMode(mode)
        if mode == self.SelectionMode.Disabled:
            return
        elif mode == self.SelectionMode.XY:
            if self._selection_limits[0] is None and self._selection_limits[1] is None:
                bounds = None
            else:
                bounds = self._selection_limits
            item = TargetItem(pos=position, bounds=bounds)
            item.sigPositionChangeFinished.connect(self._emit_marker_change)
        else:
            if mode == self.SelectionMode.X:
                angle = 90
                bounds = self._selection_limits[0]
                pos = position[0]
            else:
                angle = 0
                bounds = self._selection_limits[1]
                pos = position[1]
            item = InfiniteLine(pos=pos,
                                bounds=bounds,
                                angle=angle,
                                movable=self._selection_movable,
                                span=(0, 1),
                                **self._selection_pens)
            item.sigPositionChangeFinished.connect(self._emit_marker_change)
        self.addItem(item)
        item.setZValue(2)
        self.__markers.append(item)

    def move_region_selection(self,
                              span: Tuple[Tuple[float, float], Tuple[float, float]],
                              index: int
                              ) -> None:
        self._move_region_selection(span, index)
        self._emit_region_change()

    def _move_region_selection(self,
                               span: Tuple[Tuple[float, float], Tuple[float, float]],
                               index: int
                               ) -> None:
        item = self.__regions[index]
        item.blockSignals(True)
        if isinstance(item, LinearRegionItem):
            if item.orientation == 'vertical':
                item.setRegion(span[0])
            else:
                item.setRegion(span[1])
        elif isinstance(item, RectROI):
            item.setPos((min(span[0]), min(span[1])))
            item.setSize((max(span[0]) - min(span[0]), max(span[1]) - min(span[1])))
        item.blockSignals(False)

    def move_marker_selection(self,
                              position: Tuple[float, float],
                              index: int
                              ) -> None:
        self._move_marker_selection(position, index)
        self._emit_marker_change()

    def _move_marker_selection(self,
                               position: Tuple[float, float],
                               index: int
                               ) -> None:
        item = self.__markers[index]
        item.blockSignals(True)
        if isinstance(item, InfiniteLine):
            item.setPos(position[0] if item.angle == 90 else position[1])
        elif isinstance(item, TargetItem):
            item.setPos(position)
        item.blockSignals(False)

    def clear_marker_selections(self) -> None:
        if len(self.__markers) != 0:
            try:
                while True:
                    self._delete_marker_selection(-1)
            except IndexError:
                pass
            self._emit_marker_change()

    def delete_marker_selection(self, index: int) -> None:
        self._delete_marker_selection(index)
        self._emit_marker_change()

    def _delete_marker_selection(self, index: int) -> None:
        item = self.__markers.pop(index)
        item.sigPositionChangeFinished.disconnect()
        self.removeItem(item)

    def clear_region_selections(self) -> None:
        if len(self.__regions) != 0:
            try:
                while True:
                    self._delete_region_selection(-1)
            except IndexError:
                pass
            self._emit_region_change()

    def delete_region_selection(self, index: int) -> None:
        self._delete_region_selection(index)
        self._emit_region_change()

    def _delete_region_selection(self, index: int) -> None:
        item = self.__regions.pop(index)
        item.sigRegionChangeFinished.disconnect()
        self.removeItem(item)

    def _emit_marker_change(self) -> None:
        markers = {
            self.SelectionMode.X : [
                m.value() for m in self.__markers if isinstance(m, InfiniteLine) and m.angle == 90
            ],
            self.SelectionMode.Y : [
                m.value() for m in self.__markers if isinstance(m, InfiniteLine) and m.angle == 0
            ],
            self.SelectionMode.XY: list()
        }
        self.sigMarkerSelectionChanged.emit(markers)

    def _emit_region_change(self) -> None:
        regions = {
            self.SelectionMode.X : [
                r.getRegion() for r in self.__regions if
                isinstance(r, LinearRegionItem) and r.orientation == 'vertical'
            ],
            self.SelectionMode.Y : [
                r.getRegion() for r in self.__regions if
                isinstance(r, LinearRegionItem) and r.orientation == 'horizontal'
            ],
            self.SelectionMode.XY: list()
        }
        self.sigRegionSelectionChanged.emit(regions)

    def _apply_selection_limits(self) -> None:
        x_lim, y_lim = self._selection_limits
        if x_lim is None:
            x_lim = (None, None)
        if y_lim is None:
            y_lim = (None, None)
        for m in self.__markers:
            if isinstance(m, InfiniteLine):
                m.setBounds(x_lim if m.angle == 90 else y_lim)
            elif isinstance(m, TargetItem):
                m.set_bounds((x_lim, y_lim))
        for r in self.__regions:
            if isinstance(r, LinearRegionItem):
                r.setBounds(x_lim if r.orientation == 'vertical' else y_lim)
            elif isinstance(r, RectROI):
                r.set_bounds(self._selection_limits)
