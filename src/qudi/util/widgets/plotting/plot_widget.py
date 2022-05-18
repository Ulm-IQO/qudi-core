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

__all__ = ['MouseTrackingPlotWidget', 'RubberbandZoomPlotWidget', 'DataSelectionPlotWidget',
           'RubberbandZoomSelectionPlotWidget', 'MouseTrackingMixin', 'RubberbandZoomMixin',
           'DataSelectionMixin']

from typing import Union, Tuple, List
from PySide2 import QtCore
from pyqtgraph import PlotWidget as _PlotWidget
import qudi.util.widgets.plotting.view_box as _vb


class MouseTrackingMixin:
    """ Extend the PlotWidget class with mouse tracking and signalling """
    def __init__(self, **kwargs):
        if not isinstance(kwargs.get('viewBox', None), _vb.MouseTrackingViewBox):
            kwargs['viewBox'] = _vb.MouseTrackingViewBox()  # Use custom pg.ViewBox subclass
        super().__init__(**kwargs)

    @property
    def sigMouseMoved(self) -> QtCore.Signal:
        return self.getViewBox().sigMouseMoved

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
            kwargs['viewBox'] = _vb.RubberbandZoomViewBox()  # Use custom pg.ViewBox subclass
        super().__init__(**kwargs)
        self.set_rubberband_zoom_selection_mode = self.getViewBox().set_rubberband_zoom_selection_mode

    @property
    def rubberband_zoom_selection_mode(self) -> SelectionMode:
        return self.getViewBox().rubberband_zoom_selection_mode


class DataSelectionMixin:
    """ Extend the PlotWidget class with mouse tracking and signalling as well as mouse pointer
    data selection tools.
    """
    SelectionMode = _vb.SelectionMode

    def __init__(self, **kwargs):
        if not isinstance(kwargs.get('viewBox', None), _vb.DataSelectionViewBox):
            kwargs['viewBox'] = _vb.DataSelectionViewBox()  # Use custom pg.ViewBox subclass
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

    @property
    def sigMarkerSelectionChanged(self) -> QtCore.Signal:
        return self.getViewBox().sigMarkerSelectionChanged

    @property
    def sigRegionSelectionChanged(self) -> QtCore.Signal:
        return self.getViewBox().sigRegionSelectionChanged

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


class MouseTrackingPlotWidget(MouseTrackingMixin, _PlotWidget):
    """ Extend the PlotWidget class with mouse tracking and signalling """
    pass


class RubberbandZoomPlotWidget(RubberbandZoomMixin, MouseTrackingMixin, _PlotWidget):
    """ Extend the PlotWidget class with mouse tracking and signalling as well as a rubberband zoom
    tool.
    """
    pass


class DataSelectionPlotWidget(DataSelectionMixin, MouseTrackingMixin, _PlotWidget):
    """ Extend the PlotWidget class with mouse tracking and signalling as well as mouse pointer
    data selection tools.
    """
    pass


class RubberbandZoomSelectionPlotWidget(RubberbandZoomMixin, DataSelectionMixin, MouseTrackingMixin, _PlotWidget):
    """ Extend the PlotWidget class with mouse tracking and signalling as well as mouse pointer
    data selection tools and rubberband zoom feature.
    """
    def __init__(self, **kwargs):
        has_selection = isinstance(kwargs.get('viewBox', None), _vb.DataSelectionViewBox)
        has_rubberband = isinstance(kwargs.get('viewBox', None), _vb.RubberbandZoomMixin)
        if not has_selection or not has_rubberband:
            kwargs['viewBox'] = _vb.RubberbandZoomSelectionViewBox()
        super().__init__(**kwargs)
