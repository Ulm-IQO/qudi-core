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

__all__ = ['MouseTrackingViewBox', 'DataSelectionViewBox', 'RubberbandZoomViewBox',
           'RubberbandZoomSelectionViewBox', 'RubberbandZoomMixin', 'DataSelectionMixin',
           'MouseTrackingMixin', 'SelectionMode']

import warnings
from typing import Optional, Union, Any, Tuple, Sequence, List, Dict
from enum import IntEnum

from PySide2 import QtCore
from pyqtgraph import ViewBox, PlotDataItem, ImageItem, PlotCurveItem, ScatterPlotItem
from pyqtgraph import LinearRegionItem as _LinearRegionItem
from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent, MouseDragEvent
from qudi.util.widgets.plotting.marker import Rectangle, InfiniteCrosshairRectangle
from qudi.util.widgets.plotting.marker import InfiniteLine, LinearRegion, InfiniteCrosshair


class SelectionMode(IntEnum):
    Disabled = 0
    X = 1
    Y = 2
    XY = 3


class MouseTrackingMixin:
    """ Extension for pg.ViewBox to tap into mouse move/click/drag events and emit signals.

    x-y-positions emitted will be in real world data coordinates.
    """

    # start_position (x, y), current_position (x, y), MouseDragEvent
    sigMouseDragged = QtCore.Signal(tuple, tuple, object)
    # position (x, y), MouseClickEvent
    sigMouseClicked = QtCore.Signal(tuple, object)

    def __init__(self,
                 allow_tracking_outside_data: Optional[bool] = False,
                 **kwargs) -> None:
        super().__init__(**kwargs)
        self.allow_tracking_outside_data = bool(allow_tracking_outside_data)

    def mouseClickEvent(self, ev: MouseClickEvent) -> None:
        if self.allow_tracking_outside_data or self.pointer_on_data(ev.scenePos()):
            pos = self.mapToView(ev.pos())
            self.sigMouseClicked.emit((pos.x(), pos.y()), ev)
        if not ev.isAccepted():
            super().mouseClickEvent(ev)

    def mouseDragEvent(self, ev: MouseDragEvent, axis: Optional[int] = None) -> None:
        if self.allow_tracking_outside_data or self.pointer_on_data(ev.buttonDownScenePos()):
            start = self.mapToView(ev.buttonDownPos())
            current = self.mapToView(ev.pos())
            self.sigMouseDragged.emit((start.x(), start.y()), (current.x(), current.y()), ev)
        if not ev.isAccepted():
            super().mouseDragEvent(ev, axis)

    def pointer_on_data(self, scene_pos: QtCore.QPointF) -> bool:
        scene = self.scene()
        if scene is not None:
            for item in scene.items(scene_pos):
                if isinstance(item, (PlotDataItem, ImageItem, PlotCurveItem, ScatterPlotItem)):
                    return True
        return False


class DataSelectionMixin:
    """ Expands MouseTrackingViewBox with data selection functionality.

    You can select:
        - linear region in x or y
        - xy ROIs
        - x, y or xy data markers

    Public methods will generally emit signals if they result in a selection change. The
    corresponding "protected" methods do not emit.
    """

    SelectionMode = SelectionMode

    sigMarkerSelectionChanged = QtCore.Signal(dict)
    sigRegionSelectionChanged = QtCore.Signal(dict)

    def __init__(self,
                 selection_bounds: Optional[Sequence[Tuple[Union[None, float], Union[None, float]]]] = None,
                 selection_pen: Optional[Any] = None,
                 selection_hover_pen: Optional[Any] = None,
                 selection_brush: Optional[Any] = None,
                 selection_hover_brush: Optional[Any] = None,
                 xy_region_selection_crosshair: Optional[bool] = False,
                 xy_region_selection_handles: Optional[bool] = True,
                 xy_region_min_size_percentile: Optional[float] = None,
                 **kwargs
                 ) -> None:
        super().__init__(**kwargs)
        self._selection_bounds = None if selection_bounds is None else list(selection_bounds)
        self._selection_pen = selection_pen
        self._selection_hover_pen = selection_hover_pen
        self._selection_brush = selection_brush
        self._selection_hover_brush = selection_hover_brush
        self._xy_region_selection_crosshair = bool(xy_region_selection_crosshair)
        self._xy_region_selection_handles = bool(xy_region_selection_handles)
        self._region_selection_mode = self.SelectionMode.Disabled
        self._marker_selection_mode = self.SelectionMode.Disabled
        self._selection_mutable = True
        if (xy_region_min_size_percentile is not None) and (xy_region_min_size_percentile > 0):
            self._xy_region_min_size_percentile = xy_region_min_size_percentile
            self.sigRangeChanged.connect(self._update_xy_region_min_size)
        else:
            self._xy_region_min_size_percentile = None

        self.__regions = list()
        self.__markers = list()

    def _update_xy_region_min_size(self, viewbox, new_range, changed) -> None:
        min_size = [
            self._xy_region_min_size_percentile * abs(rang[1] - rang[0]) for rang in new_range
        ]
        for region in self.__regions:
            region.set_min_size(min_size)

    def mouseClickEvent(self, ev: MouseClickEvent) -> None:
        if self.allow_tracking_outside_data or self.pointer_on_data(ev.scenePos()):
            selection_enabled = self._marker_selection_mode != self.SelectionMode.Disabled
            if selection_enabled and (ev.button() == QtCore.Qt.LeftButton) and not ev.double():
                ev.accept()
                pos = self.mapToView(ev.pos())
                self.add_marker_selection((pos.x(), pos.y()))
        return super().mouseClickEvent(ev)

    def mouseDragEvent(self, ev: MouseDragEvent, axis: Optional[int] = None) -> None:
        if not ev.isAccepted():
            selection_enabled = self._region_selection_mode != self.SelectionMode.Disabled
            no_mod = ev.modifiers() == QtCore.Qt.NoModifier
            is_left_button = ev.button() == QtCore.Qt.LeftButton
            data_valid = self.allow_tracking_outside_data or self.pointer_on_data(
                ev.buttonDownScenePos()
            )
            if selection_enabled and no_mod and (axis is None) and is_left_button and data_valid:
                ev.accept()
                start = self.mapToView(ev.buttonDownPos())
                end = self.mapToView(ev.pos())
                span = ((start.x(), end.x()), (start.y(), end.y()))
                if ev.isStart():
                    self._add_region_selection(span)
                else:
                    try:
                        self._move_region_selection(span, index=-1)
                    except IndexError:
                        pass
                if ev.isFinish():
                    self._emit_region_change()
        return super().mouseDragEvent(ev, axis)

    @property
    def region_selection_mode(self) -> SelectionMode:
        return self._region_selection_mode

    def set_region_selection_mode(self, mode: Union[SelectionMode, int]) -> None:
        self._region_selection_mode = self.SelectionMode(mode)

    @property
    def marker_selection_mode(self) -> SelectionMode:
        return self._marker_selection_mode

    def set_marker_selection_mode(self, mode: Union[SelectionMode, int]) -> None:
        self._marker_selection_mode = self.SelectionMode(mode)

    @property
    def selection_mutable(self) -> bool:
        return self._selection_mutable

    def set_selection_mutable(self, mutable: bool) -> None:
        mutable = bool(mutable)
        if mutable is not self._selection_mutable:
            for m in self.__markers:
                m.set_movable(mutable)
            for r in self.__regions:
                r.set_movable(mutable)
                try:
                    r.set_resizable(mutable)
                except AttributeError:
                    pass
            self._selection_mutable = mutable

    @property
    def selection_bounds(self) -> Union[None, List[Union[None, Tuple[float, float]]]]:
        try:
            return self._selection_bounds.copy()
        except AttributeError:
            return self._selection_bounds

    def set_selection_bounds(self,
                             bounds: Union[None, List[Union[None, Tuple[float, float]]]]
                             ) -> None:
        old_bounds = self.selection_bounds
        if bounds != old_bounds:
            self._selection_bounds = bounds
            try:
                self._apply_selection_bounds()
            except:
                self._selection_bounds = old_bounds
                raise

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
        if mode == self.SelectionMode.XY:
            x_min, x_max = sorted(span[0])
            y_min, y_max = sorted(span[1])
            x_span = x_max - x_min
            y_span = y_max - y_min
            if self._xy_region_selection_crosshair:
                item_type = InfiniteCrosshairRectangle
            else:
                item_type = Rectangle
            item = item_type(
                viewbox=self,
                position=(x_min + x_span / 2, y_min + y_span / 2),
                size=(x_span, y_span),
                edge_handles=self.selection_mutable and self._xy_region_selection_handles,
                corner_handles=False,
                bounds=self.selection_bounds,
                movable=self.selection_mutable,
                resizable=self.selection_mutable,
                pen=self._selection_pen,
                hover_pen=self._selection_hover_pen
            )
        else:
            if mode == self.SelectionMode.X:
                orientation = QtCore.Qt.Vertical
                bounds = None if self._selection_bounds is None else self._selection_bounds[0]
                values = span[0]
            else:
                orientation = QtCore.Qt.Horizontal
                bounds = None if self._selection_bounds is None else self._selection_bounds[1]
                values = span[1]
            item = LinearRegion(viewbox=self,
                                orientation=orientation,
                                span=values,
                                bounds=bounds,
                                movable=self.selection_mutable,
                                pen=self._selection_pen,
                                hover_pen=self._selection_hover_pen,
                                brush=self._selection_brush,
                                hover_brush=self._selection_hover_brush)
        item.sigAreaChanged.connect(self._emit_region_change)
        item.set_z_value(10)
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
            item = InfiniteCrosshair(viewbox=self,
                                     position=position,
                                     bounds=self.selection_bounds,
                                     movable=self.selection_mutable,
                                     pen=self._selection_pen,
                                     hover_pen=self._selection_hover_pen)
        else:
            if mode == self.SelectionMode.X:
                orientation = QtCore.Qt.Vertical
                bounds = None if self._selection_bounds is None else self._selection_bounds[0]
                pos = position[0]
            else:
                orientation = QtCore.Qt.Horizontal
                bounds = None if self._selection_bounds is None else self._selection_bounds[1]
                pos = position[1]
            item = InfiniteLine(viewbox=self,
                                orientation=orientation,
                                position=pos,
                                bounds=bounds,
                                movable=self.selection_mutable,
                                pen=self._selection_pen,
                                hover_pen=self._selection_hover_pen)
        item.sigPositionChanged.connect(self._emit_marker_change)
        item.set_z_value(11)
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
        if isinstance(item, LinearRegion):
            if item.orientation == QtCore.Qt.Vertical:
                item.set_area(sorted(span[0]))
            else:
                item.set_area(sorted(span[1]))
        elif isinstance(item, Rectangle):
            x_min, x_max = sorted(span[0])
            y_min, y_max = sorted(span[1])
            size = (x_max - x_min, y_max - y_min)
            position = (x_min + size[0] / 2, y_min + size[1] / 2)
            item.set_area(position, size)
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
            item.set_position(position[0 if item.orientation == QtCore.Qt.Vertical else 1])
        elif isinstance(item, InfiniteCrosshair):
            item.set_position(position)
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
        item.sigPositionChanged.disconnect()
        item.hide()
        item.setParent(None)

    def hide_marker_selections(self) -> None:
        for marker in self.__markers:
            marker.hide()

    def show_marker_selections(self) -> None:
        for marker in self.__markers:
            marker.show()

    def hide_marker_selection(self, index: int) -> None:
        self.__markers[index].hide()

    def show_marker_selection(self, index: int) -> None:
        self.__markers[index].show()

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
        item.sigAreaChanged.disconnect()
        item.hide()
        item.setParent(None)

    def hide_region_selections(self) -> None:
        for region in self.__regions:
            region.hide()

    def show_region_selections(self) -> None:
        for region in self.__regions:
            region.show()

    def hide_region_selection(self, index: int) -> None:
        self.__regions[index].hide()

    def show_region_selection(self, index: int) -> None:
        self.__regions[index].show()

    @property
    def marker_selection(self) -> Dict[SelectionMode, List[Union[float, Tuple[float, float]]]]:
        return {
            self.SelectionMode.X: [
                m.position for m in self.__markers if
                isinstance(m, InfiniteLine) and m.orientation == QtCore.Qt.Vertical
            ],
            self.SelectionMode.Y: [
                m.position for m in self.__markers if
                isinstance(m, InfiniteLine) and m.orientation == QtCore.Qt.Horizontal
            ],
            self.SelectionMode.XY: [
                m.position for m in self.__markers if isinstance(m, InfiniteCrosshair)
            ]
        }

    @property
    def region_selection(self) -> Dict[SelectionMode, List[tuple]]:
        return {
            self.SelectionMode.X: [
                r.area for r in self.__regions if
                isinstance(r, LinearRegion) and r.orientation == QtCore.Qt.Vertical
            ],
            self.SelectionMode.Y: [
                r.area for r in self.__regions if
                isinstance(r, LinearRegion) and r.orientation == QtCore.Qt.Horizontal
            ],
            self.SelectionMode.XY: [r.area for r in self.__regions if isinstance(r, Rectangle)]
        }

    def _emit_marker_change(self) -> None:
        self.sigMarkerSelectionChanged.emit(self.marker_selection)

    def _emit_region_change(self) -> None:
        self.sigRegionSelectionChanged.emit(self.region_selection)

    def _apply_selection_bounds(self) -> None:
        if self._selection_bounds is None:
            x_bounds = y_bounds = None
        else:
            x_bounds, y_bounds = self._selection_bounds
        for m in self.__markers:
            if isinstance(m, InfiniteLine):
                m.set_bounds(x_bounds if m.orientation == QtCore.Qt.Vertical else y_bounds)
            elif isinstance(m, InfiniteCrosshair):
                m.set_bounds((x_bounds, y_bounds))
        for r in self.__regions:
            if isinstance(r, LinearRegion):
                r.set_bounds(x_bounds if r.orientation == QtCore.Qt.Vertical else y_bounds)
            elif isinstance(r, Rectangle):
                r.set_bounds((x_bounds, y_bounds))


class RubberbandZoomMixin:
    """
    """
    SelectionMode = SelectionMode

    sigZoomAreaApplied = QtCore.Signal(QtCore.QRectF)

    # FIXME: Introduce general dependency checking during qudi startup to avoid cluttering with
    #  checks like the one below
    try:
        from pyqtgraph import __version__ as __pyqtgraph_version
        if __pyqtgraph_version == '0.12.4':
            raise RuntimeError(
                'You are using an unupported version of pyqtgraph. Please re-install qudi-core '
                'using pip or update pyqtgraph to a version != 0.12.4 manually.'
            )
    except ImportError:
        pass

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._rubberband_zoom_selection_mode = self.SelectionMode.Disabled
        self._x_zoom_region = _LinearRegionItem(orientation='vertical',
                                                brush=kwargs.get('brush', None),
                                                pen=kwargs.get('pen', None),
                                                hoverBrush=kwargs.get('hover_brush', None),
                                                hoverPen=kwargs.get('hover_pen', None),
                                                movable=False)
        self._y_zoom_region = _LinearRegionItem(orientation='horizontal',
                                                brush=kwargs.get('brush', None),
                                                pen=kwargs.get('pen', None),
                                                hoverBrush=kwargs.get('hover_brush', None),
                                                hoverPen=kwargs.get('hover_pen', None),
                                                movable=False)

    @property
    def rubberband_zoom_selection_mode(self) -> SelectionMode:
        return self._rubberband_zoom_selection_mode

    def set_rubberband_zoom_selection_mode(self, mode: SelectionMode) -> None:
        """ Set selection mode for automatic zooming into a rubberband selection when dragging the
        mouse cursor.
        """
        self._rubberband_zoom_selection_mode = self.SelectionMode(mode)

    def mouseDragEvent(self, ev, axis=None):
        """ Additional mouse drag event handling to implement rubber band selection and zooming.
        """
        if not ev.isAccepted():
            no_mod = ev.modifiers() == QtCore.Qt.NoModifier
            is_left_button = ev.button() == QtCore.Qt.LeftButton
            mode = self._rubberband_zoom_selection_mode
            zoom_enabled = mode != self.SelectionMode.Disabled

            if zoom_enabled and is_left_button and no_mod:
                ev.accept()
                super().mouseDragEvent(ev, axis)
                start_pos = self.mapToView(ev.buttonDownPos())
                current_pos = self.mapToView(ev.pos())
                zoom_rect = QtCore.QRectF(start_pos, current_pos)
                if mode == self.SelectionMode.XY:
                    self.updateScaleBox(ev.buttonDownPos(), ev.pos())
                    if ev.isFinish():
                        self.rbScaleBox.hide()
                        self.setRange(rect=zoom_rect, padding=0)
                        self.sigZoomAreaApplied.emit(zoom_rect)
                elif mode == self.SelectionMode.X:
                    self._x_zoom_region.setRegion((start_pos.x(), current_pos.x()))
                    if ev.isStart():
                        self.addItem(self._x_zoom_region)
                    elif ev.isFinish():
                        self.removeItem(self._x_zoom_region)
                        self.setRange(xRange=self._x_zoom_region.getRegion(), padding=0)
                        zoom_rect.setHeight(0)
                        self.sigZoomAreaApplied.emit(zoom_rect)
                elif mode == self.SelectionMode.Y:
                    self._y_zoom_region.setRegion((start_pos.y(), current_pos.y()))
                    if ev.isStart():
                        self.addItem(self._y_zoom_region)
                    elif ev.isFinish():
                        self.removeItem(self._y_zoom_region)
                        self.setRange(yRange=self._y_zoom_region.getRegion(), padding=0)
                        zoom_rect.setWidth(0)
                        self.sigZoomAreaApplied.emit(zoom_rect)
            else:
                super().mouseDragEvent(ev, axis)


class MouseTrackingViewBox(MouseTrackingMixin, ViewBox):
    pass


class DataSelectionViewBox(DataSelectionMixin, MouseTrackingMixin, ViewBox):
    pass


class RubberbandZoomViewBox(RubberbandZoomMixin, MouseTrackingMixin, ViewBox):
    pass


class RubberbandZoomSelectionViewBox(RubberbandZoomMixin, DataSelectionMixin, MouseTrackingMixin, ViewBox):
    pass
