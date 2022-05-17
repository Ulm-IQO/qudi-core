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
           'ImageWidget', 'MouseTrackingImageWidget', 'RubberbandZoomImageWidget',
           'DataSelectionImageWidget']

from typing import Union, Optional, Tuple, List
from PySide2 import QtCore, QtWidgets
from pyqtgraph import PlotWidget
from qudi.util.widgets.plotting.view_box import RubberbandZoomViewBox, MouseTrackingViewBox
from qudi.util.widgets.plotting.view_box import DataSelectionViewBox
from qudi.util.widgets.plotting.plot_item import DataImageItem
from qudi.util.widgets.plotting.colorbar import ColorBarWidget


class MouseTrackingPlotWidget(PlotWidget):
    """ Extend the PlotWidget class with mouse tracking and signalling.
    """

    def __init__(self, **kwargs):
        if not isinstance(kwargs.get('viewBox', None), MouseTrackingViewBox):
            kwargs['viewBox'] = MouseTrackingViewBox()  # Use custom pg.ViewBox subclass
        super().__init__(**kwargs)
        vb = self.getViewBox()
        self.toggle_rubberband_zoom = vb.toggle_rubberband_zoom

    @property
    def sigMouseMoved(self) -> QtCore.Signal:
        return self.getViewBox().sigMouseMoved

    @property
    def sigMouseDragged(self) -> QtCore.Signal:
        return self.getViewBox().sigMouseDragged

    @property
    def sigMouseClicked(self) -> QtCore.Signal:
        return self.getViewBox().sigMouseClicked

    @property
    def rubberband_zoom(self) -> bool:
        return self.getViewBox().rubberband_zoom


class RubberbandZoomPlotWidget(MouseTrackingPlotWidget):
    """ Extend the PlotWidget class with mouse tracking and signalling as well as a rubberband zoom
    tool.
    """

    def __init__(self, **kwargs):
        if not isinstance(kwargs.get('viewBox', None), RubberbandZoomViewBox):
            kwargs['viewBox'] = RubberbandZoomViewBox()  # Use custom pg.ViewBox subclass
        super().__init__(**kwargs)
        self.toggle_rubberband_zoom = self.getViewBox().toggle_rubberband_zoom

    @property
    def rubberband_zoom(self) -> bool:
        return self.getViewBox().rubberband_zoom


class DataSelectionPlotWidget(MouseTrackingPlotWidget):
    """ Extend the PlotWidget class with mouse tracking and signalling as well as mouse pointer
    data selection tools.
    """
    SelectionMode = DataSelectionViewBox.SelectionMode

    def __init__(self, **kwargs):
        if not isinstance(kwargs.get('viewBox', None), DataSelectionViewBox):
            kwargs['viewBox'] = DataSelectionViewBox()  # Use custom pg.ViewBox subclass
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


class ImageWidget(QtWidgets.QWidget):
    """ Composite widget consisting of a PlotWidget and a colorbar to display 2D image data.
    Provides a convenient image data interface and handles user colorscale interaction.
    """
    _plot_widget_type = PlotWidget

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)

        self.plot_widget = self._plot_widget_type()
        self.image_item = DataImageItem()
        self.plot_widget.addItem(self.image_item)
        # self.plot_widget.setMinimumWidth(100)
        # self.plot_widget.setMinimumHeight(100)
        # self.plot_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
        #                                 QtWidgets.QSizePolicy.Expanding)
        # self.plot_widget.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.plot_widget.setAspectLocked(lock=True, ratio=1.0)

        self.colorbar_widget = ColorBarWidget()
        if self.colorbar_widget.mode == ColorBarWidget.ColorBarMode.PERCENTILE:
            self.image_item.set_percentiles(self.colorbar_widget.percentiles)
        else:
            self.image_item.set_percentiles(None)
        self.colorbar_widget.sigModeChanged.connect(self._colorbar_mode_changed)
        self.colorbar_widget.sigLimitsChanged.connect(self._colorbar_limits_changed)
        self.colorbar_widget.sigPercentilesChanged.connect(self._colorbar_percentiles_changed)

        layout = QtWidgets.QHBoxLayout()
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

    def set_image(self, image) -> None:
        """
        """
        if image is None:
            self.image_item.set_image(image=None, autoLevels=False)
            return

        # Set image with proper colorbar limits
        if self.colorbar_widget.mode == ColorBarWidget.ColorBarMode.PERCENTILE:
            self.image_item.set_image(image=image, autoLevels=False)
            levels = self.image_item.levels
            if levels is not None:
                self.colorbar_widget.set_limits(*levels)
        else:
            self.image_item.set_image(image=image,
                                      autoLevels=False,
                                      levels=self.colorbar_widget.limits)

    def set_axis_label(self, axis, label=None, unit=None):
        return self.plot_widget.setLabel(axis, text=label, units=unit)

    def set_data_label(self, label, unit=None):
        return self.colorbar_widget.set_label(label, unit)

    def _colorbar_mode_changed(self, mode: ColorBarWidget.ColorBarMode) -> None:
        if mode == ColorBarWidget.ColorBarMode.PERCENTILE:
            self._colorbar_percentiles_changed(self.colorbar_widget.percentiles)
        else:
            self._colorbar_limits_changed(self.colorbar_widget.limits)

    def _colorbar_limits_changed(self, limits: Tuple[float, float]) -> None:
        self.image_item.set_percentiles(None)
        self.image_item.setLevels(limits)

    def _colorbar_percentiles_changed(self, percentiles: Tuple[float, float]) -> None:
        self.image_item.set_percentiles(percentiles)
        levels = self.image_item.levels
        if levels is not None:
            self.colorbar_widget.set_limits(*levels)


class MouseTrackingImageWidget(ImageWidget):
    """ Extends the normal qudi ImageWidget with a custom PlotWidget type that tracks mouse
    activity and sends signals.
    """
    _plot_widget_type = MouseTrackingPlotWidget

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)
        self.toggle_rubberband_zoom = self.plot_widget.toggle_rubberband_zoom

    @property
    def sigMouseMoved(self) -> QtCore.Signal:
        return self.plot_widget.sigMouseMoved

    @property
    def sigMouseDragged(self) -> QtCore.Signal:
        return self.plot_widget.sigMouseDragged

    @property
    def sigMouseClicked(self) -> QtCore.Signal:
        return self.plot_widget.sigMouseClicked

    @property
    def rubberband_zoom(self) -> bool:
        return self.plot_widget.rubberband_zoom


class RubberbandZoomImageWidget(MouseTrackingImageWidget):
    """ Extends the qudi MouseTrackingImageWidget with a rubberband zoom tool.
    """
    _plot_widget_type = RubberbandZoomPlotWidget

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)
        self.toggle_rubberband_zoom = self.plot_widget.toggle_rubberband_zoom

    @property
    def rubberband_zoom(self) -> bool:
        return self.plot_widget.rubberband_zoom


class DataSelectionImageWidget(RubberbandZoomImageWidget):
    """ Extends the qudi MouseTrackingImageWidget with data selection tools and signals.
    """
    _plot_widget_type = DataSelectionPlotWidget

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)
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

    @property
    def sigMarkerSelectionChanged(self) -> QtCore.Signal:
        return self.plot_widget.sigMarkerSelectionChanged

    @property
    def sigRegionSelectionChanged(self) -> QtCore.Signal:
        return self.plot_widget.sigRegionSelectionChanged

    @property
    def region_selection_mode(self) -> DataSelectionPlotWidget.SelectionMode:
        return self.plot_widget.region_selection_mode

    @property
    def marker_selection_mode(self) -> DataSelectionPlotWidget.SelectionMode:
        return self.plot_widget.marker_selection_mode

    @property
    def selection_mutable(self) -> bool:
        return self.plot_widget.selection_mutable

    @property
    def selection_bounds(self) -> Union[None, List[Union[None, Tuple[float, float]]]]:
        return self.plot_widget.selection_bounds

