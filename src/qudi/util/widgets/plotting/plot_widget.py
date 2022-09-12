# -*- coding: utf-8 -*-

"""
This file contains modified pyqtgraph plot widgets for advanced interactive plotting.

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

__all__ = ['PlotWidget', 'MouseTrackingPlotWidget', 'RubberbandZoomPlotWidget',
           'DataSelectionPlotWidget', 'RubberbandZoomSelectionPlotWidget', 'MouseTrackingMixin',
           'RubberbandZoomMixin', 'DataSelectionMixin']

from typing import Union, Tuple, List, Dict, Optional, Any, Sequence
from PySide2 import QtCore
from pyqtgraph import PlotWidget as _PlotWidget
from pyqtgraph import SignalProxy as _SignalProxy
import qudi.util.widgets.plotting.view_box as _vb


class MouseTrackingMixin:
    """ Extend the PlotWidget class with mouse tracking and signalling """

    # position (x, y)
    sigMouseMoved = QtCore.Signal(tuple)

    def __init__(self,
                 allow_tracking_outside_data: Optional[bool] = False,
                 max_mouse_pos_update_rate: Optional[float] = None,
                 **kwargs
                 ) -> None:
        if not isinstance(kwargs.get('viewBox', None), _vb.MouseTrackingMixin):
            # Use custom pg.ViewBox subclass
            kwargs['viewBox'] = _vb.MouseTrackingViewBox(
                allow_tracking_outside_data=allow_tracking_outside_data
            )

        super().__init__(**kwargs)

        if max_mouse_pos_update_rate is not None and max_mouse_pos_update_rate > 0.:
            self._mouse_position_signal_proxy = _SignalProxy(
                signal=self.scene().sigMouseMoved,
                rateLimit=max_mouse_pos_update_rate,
                delay=2 / max_mouse_pos_update_rate,  # Must be larger than 1/rateLimit
                slot=self.__mouse_moved
            )

    def __mouse_moved(self, args) -> None:
        pos = self.getViewBox().mapSceneToView(args[0])
        self.sigMouseMoved.emit((pos.x(), pos.y()))

    @property
    def sigMouseDragged(self) -> QtCore.Signal:
        return self.getViewBox().sigMouseDragged

    @property
    def sigMouseClicked(self) -> QtCore.Signal:
        return self.getViewBox().sigMouseClicked


class RubberbandZoomMixin:

    SelectionMode = _vb.SelectionMode

    def __init__(self, **kwargs):
        if not isinstance(kwargs.get('viewBox', None), _vb.RubberbandZoomMixin):
            # Use custom pg.ViewBox subclass
            kwargs['viewBox'] = _vb.RubberbandZoomViewBox()
        super().__init__(**kwargs)
        self.set_rubberband_zoom_selection_mode = self.getViewBox().set_rubberband_zoom_selection_mode

    @property
    def sigZoomAreaApplied(self) -> QtCore.Signal:
        return self.getViewBox().sigZoomAreaApplied

    @property
    def rubberband_zoom_selection_mode(self) -> SelectionMode:
        return self.getViewBox().rubberband_zoom_selection_mode


class DataSelectionMixin:
    """ Extend the PlotWidget class with mouse tracking and signalling as well as mouse pointer
    data selection tools.
    """
    SelectionMode = _vb.SelectionMode

    def __init__(self,
                 selection_bounds: Optional[Sequence[Tuple[Union[None, float], Union[None, float]]]] = None,
                 selection_pen: Optional[Any] = None,
                 selection_hover_pen: Optional[Any] = None,
                 selection_brush: Optional[Any] = None,
                 selection_hover_brush: Optional[Any] = None,
                 xy_region_selection_crosshair: Optional[bool] = False,
                 xy_region_selection_handles: Optional[bool] = True,
                 **kwargs
                 ) -> None:
        if not isinstance(kwargs.get('viewBox', None), _vb.DataSelectionMixin):
            # Use custom pg.ViewBox subclass
            kwargs['viewBox'] = _vb.DataSelectionViewBox(
                selection_bounds=selection_bounds,
                selection_pen=selection_pen,
                selection_hover_pen=selection_hover_pen,
                selection_brush=selection_brush,
                selection_hover_brush=selection_hover_brush,
                xy_region_selection_crosshair=xy_region_selection_crosshair,
                xy_region_selection_handles=xy_region_selection_handles
            )
        super().__init__(**kwargs)
        vb = self.getViewBox()
        self.set_region_selection_mode = vb.set_region_selection_mode
        self.set_marker_selection_mode = vb.set_marker_selection_mode
        self.set_selection_mutable = vb.set_selection_mutable
        self.set_selection_bounds = vb.set_selection_bounds
        self.add_region_selection = vb.add_region_selection
        self.add_marker_selection = vb.add_marker_selection
        self.move_region_selection = vb.move_region_selection
        self.move_marker_selection = vb.move_marker_selection
        self.clear_marker_selections = vb.clear_marker_selections
        self.delete_marker_selection = vb.delete_marker_selection
        self.clear_region_selections = vb.clear_region_selections
        self.delete_region_selection = vb.delete_region_selection
        self.hide_marker_selections = vb.hide_marker_selections
        self.show_marker_selections = vb.show_marker_selections
        self.hide_marker_selection = vb.hide_marker_selection
        self.show_marker_selection = vb.show_marker_selection
        self.hide_region_selections = vb.hide_region_selections
        self.show_region_selections = vb.show_region_selections
        self.hide_region_selection = vb.hide_region_selection
        self.show_region_selection = vb.show_region_selection

    @property
    def sigMarkerSelectionChanged(self) -> QtCore.Signal:
        return self.getViewBox().sigMarkerSelectionChanged

    @property
    def sigRegionSelectionChanged(self) -> QtCore.Signal:
        return self.getViewBox().sigRegionSelectionChanged

    @property
    def marker_selection(self) -> Dict[SelectionMode, List[Union[float, Tuple[float, float]]]]:
        return self.getViewBox().marker_selection

    @property
    def region_selection(self) -> Dict[SelectionMode, List[Tuple[Tuple[float, float], Tuple[float, float]]]]:
        return self.getViewBox().region_selection

    @property
    def region_selection_mode(self) -> SelectionMode:
        return self.getViewBox().region_selection_mode

    @property
    def marker_selection_mode(self) -> SelectionMode:
        return self.getViewBox().marker_selection_mode

    @property
    def selection_mutable(self) -> bool:
        return self.getViewBox().selection_mutable

    @property
    def selection_bounds(self) -> Union[None, List[Union[None, Tuple[float, float]]]]:
        return self.getViewBox().selection_bounds


class PlotWidget(_PlotWidget):
    """ Make blockSignals also un-/mute signals from the viewbox """
    def blockSignals(self, block: bool) -> None:
        super().blockSignals(block)
        self.getViewBox().blockSignals(block)


class MouseTrackingPlotWidget(MouseTrackingMixin, PlotWidget):
    """ Extend the PlotWidget class with mouse tracking and signalling """
    pass


class RubberbandZoomPlotWidget(RubberbandZoomMixin, MouseTrackingMixin, PlotWidget):
    """ Extend the PlotWidget class with mouse tracking and signalling as well as a rubberband zoom
    tool.
    """
    pass


class DataSelectionPlotWidget(DataSelectionMixin, MouseTrackingMixin, PlotWidget):
    """ Extend the PlotWidget class with mouse tracking and signalling as well as mouse pointer
    data selection tools.
    """
    pass


class RubberbandZoomSelectionPlotWidget(RubberbandZoomMixin, DataSelectionMixin, MouseTrackingMixin, PlotWidget):
    """ Extend the PlotWidget class with mouse tracking and signalling as well as mouse pointer
    data selection tools and rubberband zoom feature.
    """
    def __init__(self,
                 allow_tracking_outside_data: Optional[bool] = False,
                 selection_bounds: Optional[Sequence[Tuple[Union[None, float], Union[None, float]]]] = None,
                 selection_pen: Optional[Any] = None,
                 selection_hover_pen: Optional[Any] = None,
                 selection_brush: Optional[Any] = None,
                 selection_hover_brush: Optional[Any] = None,
                 xy_region_selection_crosshair: Optional[bool] = False,
                 xy_region_selection_handles: Optional[bool] = True,
                 **kwargs
                 ) -> None:
        has_selection = isinstance(kwargs.get('viewBox', None), _vb.DataSelectionMixin)
        has_rubberband = isinstance(kwargs.get('viewBox', None), _vb.RubberbandZoomMixin)
        if not has_selection or not has_rubberband:
            kwargs['viewBox'] = _vb.RubberbandZoomSelectionViewBox(
                allow_tracking_outside_data=allow_tracking_outside_data,
                selection_bounds=selection_bounds,
                selection_pen=selection_pen,
                selection_hover_pen=selection_hover_pen,
                selection_brush=selection_brush,
                selection_hover_brush=selection_hover_brush,
                xy_region_selection_crosshair=xy_region_selection_crosshair,
                xy_region_selection_handles=xy_region_selection_handles
            )
        super().__init__(**kwargs)
