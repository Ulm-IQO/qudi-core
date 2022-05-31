# -*- coding: utf-8 -*-

"""
This file contains custom widgets to facilitate 2D image display with an adjustable colorscale and
various other interactive features.

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

__all__ = ['ImageWidget', 'MouseTrackingImageWidget', 'RubberbandZoomImageWidget',
           'DataSelectionImageWidget', 'RubberbandZoomSelectionImageWidget']

from typing import Union, Optional, Tuple, List, Dict
from PySide2 import QtCore, QtWidgets
from pyqtgraph import PlotWidget as _PlotWidget
from qudi.util.widgets.plotting.plot_item import DataImageItem as _DataImageItem
from qudi.util.widgets.plotting.colorbar import ColorBarWidget as _ColorBarWidget
import qudi.util.widgets.plotting.plot_widget as _pw


class ImageWidget(QtWidgets.QWidget):
    """ Composite widget consisting of a PlotWidget and a colorbar to display 2D image data.
    Provides a convenient image data interface and handles user colorscale interaction.
    """
    _plot_widget_type = _PlotWidget

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, **kwargs):
        super().__init__(parent=parent)

        self.plot_widget = self._plot_widget_type(**kwargs)
        self.image_item = _DataImageItem()
        self.plot_widget.addItem(self.image_item)
        self.plot_widget.setAspectLocked(lock=True, ratio=1.0)

        self.colorbar_widget = _ColorBarWidget()
        if self.colorbar_widget.mode == _ColorBarWidget.ColorBarMode.PERCENTILE:
            self.image_item.set_percentiles(self.colorbar_widget.percentiles)
        else:
            self.image_item.set_percentiles(None)
        self.colorbar_widget.sigModeChanged.connect(self._colorbar_mode_changed)
        self.colorbar_widget.sigLimitsChanged.connect(self._colorbar_limits_changed)
        self.colorbar_widget.sigPercentilesChanged.connect(self._colorbar_percentiles_changed)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setStretch(0, 1)
        layout.addWidget(self.plot_widget)
        layout.addWidget(self.colorbar_widget)
        self.setLayout(layout)

        # monkey-patch attributes from PlotWidget and ImageItem for convenient access
        self.autoRange = self.plot_widget.autoRange
        self.set_percentiles = self.image_item.set_percentiles
        self.set_image_extent = self.image_item.set_image_extent

    @property
    def percentiles(self) -> Union[None, Tuple[float, float]]:
        return self.image_item.percentiles

    @property
    def levels(self) -> Tuple[float, float]:
        return self.image_item.levels

    def set_image(self,
                  image,
                  extent: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None,
                  adjust_for_px_size: Optional[bool] = True
                  ) -> None:
        """
        """
        if image is None:
            self.image_item.set_image(image=None, autoLevels=False)
            return

        # Set image with proper colorbar limits
        if self.colorbar_widget.mode == _ColorBarWidget.ColorBarMode.PERCENTILE:
            self.image_item.set_image(image=image, autoLevels=False)
            levels = self.image_item.levels
            if levels is not None:
                self.colorbar_widget.set_limits(*levels)
        else:
            self.image_item.set_image(image=image,
                                      autoLevels=False,
                                      levels=self.colorbar_widget.limits)
        if extent is not None:
            self.image_item.set_image_extent(extent, adjust_for_px_size)

    def set_axis_label(self, axis, label=None, unit=None):
        return self.plot_widget.setLabel(axis, text=label, units=unit)

    def set_data_label(self, label, unit=None):
        return self.colorbar_widget.set_label(label, unit)

    def _colorbar_mode_changed(self, mode: _ColorBarWidget.ColorBarMode) -> None:
        if mode == _ColorBarWidget.ColorBarMode.PERCENTILE:
            self._colorbar_percentiles_changed(self.colorbar_widget.percentiles)
        else:
            self._colorbar_limits_changed(self.colorbar_widget.limits)

    def _colorbar_limits_changed(self, limits: Tuple[float, float]) -> None:
        self.image_item.set_percentiles(None)
        self.image_item.setLevels(limits)

    def _colorbar_percentiles_changed(self, percentiles: Tuple[float, float]) -> None:
        self.image_item.set_percentiles(percentiles)
        levels = self.levels
        if levels is not None:
            self.colorbar_widget.set_limits(*levels)


class MouseTrackingMixin:
    """ Extends the normal qudi ImageWidget with a custom PlotWidget type that tracks mouse
    activity and sends signals.
    """
    _plot_widget_type = _pw.MouseTrackingPlotWidget

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, **kwargs):
        super().__init__(parent=parent, **kwargs)

    @property
    def sigMouseMoved(self) -> QtCore.Signal:
        return self.plot_widget.sigMouseMoved

    @property
    def sigMouseDragged(self) -> QtCore.Signal:
        return self.plot_widget.sigMouseDragged

    @property
    def sigMouseClicked(self) -> QtCore.Signal:
        return self.plot_widget.sigMouseClicked


class RubberbandZoomMixin:
    """ Extends the qudi MouseTrackingImageWidget with a rubberband zoom tool.
    """
    _plot_widget_type = _pw.RubberbandZoomPlotWidget
    SelectionMode = _pw.RubberbandZoomPlotWidget.SelectionMode

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, **kwargs):
        super().__init__(parent=parent, **kwargs)
        self.set_rubberband_zoom_selection_mode = self.plot_widget.set_rubberband_zoom_selection_mode

    @property
    def sigZoomAreaApplied(self) -> QtCore.Signal:
        return self.plot_widget.sigZoomAreaApplied

    @property
    def rubberband_zoom_selection_mode(self) -> SelectionMode:
        return self.plot_widget.rubberband_zoom_selection_mode


class DataSelectionMixin:
    """ Extends the qudi MouseTrackingImageWidget with data selection tools and signals.
    """
    _plot_widget_type = _pw.DataSelectionPlotWidget
    SelectionMode = _pw.DataSelectionPlotWidget.SelectionMode

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, **kwargs):
        super().__init__(parent=parent, **kwargs)
        self.set_region_selection_mode = self.plot_widget.set_region_selection_mode
        self.set_marker_selection_mode = self.plot_widget.set_marker_selection_mode
        self.set_selection_mutable = self.plot_widget.set_selection_mutable
        self.set_selection_bounds = self.plot_widget.set_selection_bounds
        self.add_region_selection = self.plot_widget.add_region_selection
        self.add_marker_selection = self.plot_widget.add_marker_selection
        self.move_region_selection = self.plot_widget.move_region_selection
        self.move_marker_selection = self.plot_widget.move_marker_selection
        self.clear_marker_selections = self.plot_widget.clear_marker_selections
        self.delete_marker_selection = self.plot_widget.delete_marker_selection
        self.clear_region_selections = self.plot_widget.clear_region_selections
        self.delete_region_selection = self.plot_widget.delete_region_selection
        self.hide_marker_selections = self.plot_widget.hide_marker_selections
        self.show_marker_selections = self.plot_widget.show_marker_selections
        self.hide_marker_selection = self.plot_widget.hide_marker_selection
        self.show_marker_selection = self.plot_widget.show_marker_selection
        self.hide_region_selections = self.plot_widget.hide_region_selections
        self.show_region_selections = self.plot_widget.show_region_selections
        self.hide_region_selection = self.plot_widget.hide_region_selection
        self.show_region_selection = self.plot_widget.show_region_selection

    @property
    def sigMarkerSelectionChanged(self) -> QtCore.Signal:
        return self.plot_widget.sigMarkerSelectionChanged

    @property
    def sigRegionSelectionChanged(self) -> QtCore.Signal:
        return self.plot_widget.sigRegionSelectionChanged

    @property
    def marker_selection(self) -> Dict[SelectionMode, List[Tuple[float, float]]]:
        return self.plot_widget.marker_selection

    @property
    def region_selection(self) -> Dict[SelectionMode, List[Tuple[Tuple[float, float], Tuple[float, float]]]]:
        return self.plot_widget.region_selection

    @property
    def region_selection_mode(self) -> _pw.DataSelectionPlotWidget.SelectionMode:
        return self.plot_widget.region_selection_mode

    @property
    def marker_selection_mode(self) -> _pw.DataSelectionPlotWidget.SelectionMode:
        return self.plot_widget.marker_selection_mode

    @property
    def selection_mutable(self) -> bool:
        return self.plot_widget.selection_mutable

    @property
    def selection_bounds(self) -> Union[None, List[Union[None, Tuple[float, float]]]]:
        return self.plot_widget.selection_bounds


class MouseTrackingImageWidget(MouseTrackingMixin, ImageWidget):
    pass


class RubberbandZoomImageWidget(RubberbandZoomMixin, MouseTrackingMixin, ImageWidget):
    pass


class DataSelectionImageWidget(DataSelectionMixin, MouseTrackingMixin, ImageWidget):
    pass


class RubberbandZoomSelectionImageWidget(RubberbandZoomMixin, DataSelectionMixin, MouseTrackingMixin, ImageWidget):
    _plot_widget_type = _pw.RubberbandZoomSelectionPlotWidget
    SelectionMode = _pw.RubberbandZoomSelectionPlotWidget.SelectionMode
