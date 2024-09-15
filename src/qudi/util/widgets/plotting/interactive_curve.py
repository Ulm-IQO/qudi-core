# -*- coding: utf-8 -*-

"""
ToDo

Copyright (c) 2022, the qudi developers. See the AUTHORS.md file at the top-level directory of this
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

from PySide2 import QtCore, QtWidgets, QtGui
from typing import Optional, Mapping, Any, Dict, Tuple, Union, List, Sequence
import pyqtgraph as pg

from qudi.util.widgets.scientific_spinbox import ScienDSpinBox
from qudi.util.widgets.separator_lines import VerticalLine
from qudi.util.widgets.plotting.axis import label_nudged_plot_widget
from qudi.util.widgets.plotting.plot_widget import RubberbandZoomSelectionPlotWidget
from qudi.util.units import ScaledFloat


PlotWidget = label_nudged_plot_widget(RubberbandZoomSelectionPlotWidget)


class PlotEditorWidget(QtWidgets.QWidget):
    """
    """

    sigAutoRangeClicked = QtCore.Signal(bool, bool)  # x- and/or y-axis
    sigLabelsChanged = QtCore.Signal(object, object)
    sigUnitsChanged = QtCore.Signal(object, object)
    sigLimitsChanged = QtCore.Signal(object, object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent=parent)

        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        # Generate labels
        x_label = QtWidgets.QLabel('Horizontal Axis:')
        x_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        y_label = QtWidgets.QLabel('Vertical Axis:')
        y_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        label_label = QtWidgets.QLabel('Label')
        label_label.setAlignment(QtCore.Qt.AlignCenter)
        unit_label = QtWidgets.QLabel('Units')
        unit_label.setAlignment(QtCore.Qt.AlignCenter)
        range_label = QtWidgets.QLabel('Range')
        range_label.setAlignment(QtCore.Qt.AlignCenter)
        # Generate editors
        self.x_label_lineEdit = QtWidgets.QLineEdit()
        self.x_label_lineEdit.setMinimumWidth(50)
        self.x_unit_lineEdit = QtWidgets.QLineEdit()
        self.x_unit_lineEdit.setMinimumWidth(50)
        self.x_lower_limit_spinBox = ScienDSpinBox()
        self.x_lower_limit_spinBox.setMinimumWidth(70)
        self.x_upper_limit_spinBox = ScienDSpinBox()
        self.x_upper_limit_spinBox.setMinimumWidth(70)
        self.x_auto_button = QtWidgets.QPushButton('Auto Range')
        self.y_label_lineEdit = QtWidgets.QLineEdit()
        self.y_label_lineEdit.setMinimumWidth(50)
        self.y_unit_lineEdit = QtWidgets.QLineEdit()
        self.y_unit_lineEdit.setMinimumWidth(50)
        self.y_lower_limit_spinBox = ScienDSpinBox()
        self.y_lower_limit_spinBox.setMinimumWidth(70)
        self.y_upper_limit_spinBox = ScienDSpinBox()
        self.y_upper_limit_spinBox.setMinimumWidth(70)
        self.y_auto_button = QtWidgets.QPushButton('Auto Range')

        row = 0
        layout.addWidget(label_label, row, 1)
        layout.addWidget(unit_label, row, 2)
        layout.addWidget(range_label, row, 4, 1, 2)
        row += 1
        layout.addWidget(x_label, row, 0)
        layout.addWidget(self.x_label_lineEdit, row, 1)
        layout.addWidget(self.x_unit_lineEdit, row, 2)
        layout.addWidget(self.x_lower_limit_spinBox, row, 4)
        layout.addWidget(self.x_upper_limit_spinBox, row, 5)
        layout.addWidget(self.x_auto_button, row, 6)
        row += 1
        layout.addWidget(y_label, row, 0)
        layout.addWidget(self.y_label_lineEdit, row, 1)
        layout.addWidget(self.y_unit_lineEdit, row, 2)
        layout.addWidget(self.y_lower_limit_spinBox, row, 4)
        layout.addWidget(self.y_upper_limit_spinBox, row, 5)
        layout.addWidget(self.y_auto_button, row, 6)
        row += 1
        layout.addWidget(VerticalLine(), 0, 3, row, 1)

        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setColumnStretch(4, 3)
        layout.setColumnStretch(5, 3)

        self.x_label_lineEdit.editingFinished.connect(self.__x_label_changed)
        self.y_label_lineEdit.editingFinished.connect(self.__y_label_changed)
        self.x_unit_lineEdit.editingFinished.connect(self.__x_unit_changed)
        self.y_unit_lineEdit.editingFinished.connect(self.__y_unit_changed)
        self.x_lower_limit_spinBox.editingFinished.connect(self.__x_limits_changed)
        self.x_upper_limit_spinBox.editingFinished.connect(self.__x_limits_changed)
        self.y_lower_limit_spinBox.editingFinished.connect(self.__y_limits_changed)
        self.y_upper_limit_spinBox.editingFinished.connect(self.__y_limits_changed)
        self.x_auto_button.clicked.connect(
            lambda: self.sigAutoRangeClicked.emit(True, False)
        )
        self.y_auto_button.clicked.connect(
            lambda: self.sigAutoRangeClicked.emit(False, True)
        )

        self.set_limits((-0.5, 0.5), (-0.5, 0.5))
        self.set_units('arb.u.', 'arb.u.')
        self.set_labels('X', 'Y')

    @property
    def labels(self) -> Tuple[str, str]:
        return self.x_label_lineEdit.text(), self.y_label_lineEdit.text()

    @property
    def units(self) -> Tuple[str, str]:
        return self.x_unit_lineEdit.text(), self.y_unit_lineEdit.text()

    @property
    def limits(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        x_min, x_max = sorted([self.x_lower_limit_spinBox.value(),
                               self.x_upper_limit_spinBox.value()])
        y_min, y_max = sorted([self.y_lower_limit_spinBox.value(),
                               self.y_upper_limit_spinBox.value()])
        return (x_min, x_max), (y_min, y_max)

    def set_labels(self, x: Optional[str] = None, y: Optional[str] = None) -> None:
        if x is not None:
            self.x_label_lineEdit.setText(x)
        if y is not None:
            self.y_label_lineEdit.setText(y)

    def set_units(self, x: Optional[str] = None, y: Optional[str] = None) -> None:
        if x is not None:
            self.x_unit_lineEdit.setText(x)
        if y is not None:
            self.y_unit_lineEdit.setText(y)

    def set_limits(self,
                   x: Optional[Tuple[float, float]] = None,
                   y: Optional[Tuple[float, float]] = None
                   ) -> None:
        if x is not None:
            lower, upper = sorted(x)
            self.x_lower_limit_spinBox.setValue(lower)
            self.x_upper_limit_spinBox.setValue(upper)
        if y is not None:
            lower, upper = sorted(y)
            self.y_lower_limit_spinBox.setValue(lower)
            self.y_upper_limit_spinBox.setValue(upper)

    def __x_limits_changed(self) -> None:
        lower = self.x_lower_limit_spinBox.value()
        upper = self.x_upper_limit_spinBox.value()
        if upper < lower:
            lower, upper = upper, lower
            self.x_lower_limit_spinBox.setValue(lower)
            self.x_upper_limit_spinBox.setValue(upper)
            self.__swap_limits_focus()
        self.sigLimitsChanged.emit((lower, upper), None)

    def __y_limits_changed(self) -> None:
        lower = self.y_lower_limit_spinBox.value()
        upper = self.y_upper_limit_spinBox.value()
        if upper < lower:
            lower, upper = upper, lower
            self.y_lower_limit_spinBox.setValue(lower)
            self.y_upper_limit_spinBox.setValue(upper)
            self.__swap_limits_focus()
        self.sigLimitsChanged.emit(None, self.limits[1])

    def __x_label_changed(self) -> None:
        self.sigLabelsChanged.emit(self.labels[0], None)

    def __y_label_changed(self) -> None:
        self.sigLabelsChanged.emit(None, self.labels[1])

    def __x_unit_changed(self) -> None:
        self.sigUnitsChanged.emit(self.units[0], None)

    def __y_unit_changed(self) -> None:
        self.sigUnitsChanged.emit(None, self.units[1])

    def __swap_limits_focus(self) -> None:
        if self.x_lower_limit_spinBox.hasFocus():
            self.x_upper_limit_spinBox.setFocus()
        elif self.x_upper_limit_spinBox.hasFocus():
            self.x_lower_limit_spinBox.setFocus()
        elif self.y_lower_limit_spinBox.hasFocus():
            self.y_upper_limit_spinBox.setFocus()
        elif self.y_upper_limit_spinBox.hasFocus():
            self.y_lower_limit_spinBox.setFocus()


class PlotLegendIconWidget(QtWidgets.QWidget):
    def __init__(self, item, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent=parent)

        self.setMouseTracking(False)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.setFixedSize(20, 20)

        self._item = item

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        p = QtGui.QPainter(self)

        opts = self._item.opts
        if opts.get('antialias'):
            p.setRenderHint(p.RenderHint.Antialiasing)

        if not isinstance(self._item, pg.ScatterPlotItem):
            p.setPen(pg.mkPen(opts['pen']))
            p.drawLine(0, 11, 20, 11)

            if (opts.get('fillLevel', None) is not None and
                    opts.get('fillBrush', None) is not None):
                p.setBrush(pg.mkBrush(opts['fillBrush']))
                p.setPen(pg.mkPen(opts['pen']))
                p.drawPolygon(QtGui.QPolygonF(
                    [QtCore.QPointF(2, 18), QtCore.QPointF(18, 2),
                     QtCore.QPointF(18, 18)]))

        symbol = opts.get('symbol', None)
        if symbol is not None:
            if isinstance(self._item, pg.PlotDataItem):
                opts = self._item.scatter.opts
            p.translate(10, 10)
            pg.graphicsItems.ScatterPlotItem.drawSymbol(p, symbol, opts['size'], pg.mkPen(opts['pen']), pg.mkBrush(opts['brush']))

        if isinstance(self._item, pg.BarGraphItem):
            p.setBrush(pg.mkBrush(opts['brush']))
            p.drawRect(QtCore.QRectF(2, 2, 18, 18))


class PlotSelectorWidget(QtWidgets.QWidget):
    """
    """
    sigSelectionChanged = QtCore.Signal(dict)  # selection

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent=parent)

        self._stretch = QtWidgets.QSpacerItem(
            0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self._selector_layout = QtWidgets.QGridLayout()
        self._selector_layout.addItem(self._stretch, 0, 0, 1, 2)
        self._selector_layout.setColumnStretch(0, 1)
        self.setLayout(self._selector_layout)

        self._selectors = dict()

    @property
    def selection(self) -> Dict[str, bool]:
        return {name: selector.isChecked() for name, (_, selector) in self._selectors.items()}

    def set_selection(self, selection: Mapping[str, bool]) -> None:
        for name, select in selection.items():
            try:
                self._selectors[name][1].setChecked(select)
            except KeyError:
                pass

    def add_selector(self,
                     name: str,
                     item: Optional[pg.PlotDataItem] = None,
                     selected: Optional[bool] = False) -> None:
        if name in self._selectors:
            raise ValueError(f'Selector with name "{name}" already present in plot selector')
        selector = self._create_selector(name)
        selector.setChecked(selected)
        selector.clicked.connect(self._selection_changed)
        self._selector_layout.removeItem(self._stretch)
        row = len(self._selectors)
        if item is None:
            self._selector_layout.addWidget(selector, row, 0, 1, 2)
            self._selectors[name] = (None, selector)
        else:
            icon = PlotLegendIconWidget(item)
            self._selector_layout.addWidget(icon, row, 0)
            self._selector_layout.addWidget(selector, row, 1)
            self._selectors[name] = (icon, selector)
        self._selector_layout.addItem(self._stretch, row + 1, 0, 1, 2)

    def remove_selector(self, name: str) -> None:
        if name not in self._selectors:
            raise ValueError(f'Selector with name "{name}" not found in plot selector')
        self._selector_layout.removeItem(self._stretch)
        for sel_name, (icon, selector) in reversed(self._selectors.items()):
            self._selector_layout.removeWidget(selector)
            if icon is not None:
                self._selector_layout.removeWidget(icon)
            if sel_name == name:
                break
        after_remove = False
        for row, (sel_name, (icon, selector)) in enumerate(self._selectors.items()):
            if after_remove:
                if icon is None:
                    self._selector_layout.addWidget(selector, row - 1, 0, 1, 2)
                else:
                    self._selector_layout.addWidget(icon, row - 1, 0)
                    self._selector_layout.addWidget(selector, row - 1, 1)
            elif sel_name == name:
                after_remove = True
        icon, selector = self._selectors.pop(name)
        selector.clicked.disconnect()
        selector.setParent(None)
        icon.setParent(None)
        self._selector_layout.addItem(self._stretch, len(self._selectors), 0, 1, 2)

    def _selection_changed(self) -> None:
        self.sigSelectionChanged.emit(self.selection)

    @staticmethod
    def _create_selector(name: str, color: Optional[Any] = None) -> QtWidgets.QCheckBox:
        checkbox = QtWidgets.QCheckBox(name)
        if color is not None:
            color_str = pg.mkColor(color).name()
            checkbox.setStyleSheet('QCheckBox { color: ' + color_str + ' }')
        return checkbox


class CursorPositionLabel(QtWidgets.QLabel):
    """
    """

    def __init__(self,
                 units: Optional[Tuple[str, str]] = None,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)

        self._units = ('', '')
        self._text_template = ''
        self._pos_cache = (0, 0)

        if units is None:
            units = self._units
        self.set_units(*units)

    def set_units(self, x: str, y: str) -> None:
        units = (x if x else '', y if y else '')
        self._update_text_template(units)
        self._units = units
        self.update_position(self._pos_cache)

    def update_position(self, pos: Tuple[float, float]) -> None:
        x = ScaledFloat(pos[0])
        y = ScaledFloat(pos[1])
        self.setText(self._text_template.format(x, y))
        self._pos_cache = pos

    def _update_text_template(self, units: Tuple[str, str]) -> None:
        x_unit, y_unit = units
        self._text_template = f'Cursor: ({{:.3r}}{x_unit}, {{:.3r}}{y_unit})'


class InteractiveCurvesWidget(QtWidgets.QWidget):
    """
    """

    SelectionMode = RubberbandZoomSelectionPlotWidget.SelectionMode
    
    sigPlotParametersChanged = QtCore.Signal()
    sigAutoLimitsApplied = QtCore.Signal(bool, bool)  # in x- and/or y-direction

    def __init__(self,
                 allow_tracking_outside_data: Optional[bool] = False,
                 max_mouse_pos_update_rate: Optional[float] = None,
                 selection_bounds: Optional[Sequence[Tuple[Union[None, float], Union[None, float]]]] = None,
                 selection_pen: Optional[Any] = None,
                 selection_hover_pen: Optional[Any] = None,
                 selection_brush: Optional[Any] = None,
                 selection_hover_brush: Optional[Any] = None,
                 xy_region_selection_crosshair: Optional[bool] = False,
                 xy_region_selection_handles: Optional[bool] = True,
                 **kwargs
                 ) -> None:
        super().__init__(**kwargs)
        if max_mouse_pos_update_rate is None:
            max_mouse_pos_update_rate = 20.

        self._plot_widget = PlotWidget(
            allow_tracking_outside_data=allow_tracking_outside_data,
            max_mouse_pos_update_rate=max_mouse_pos_update_rate,
            selection_bounds=selection_bounds,
            selection_pen=selection_pen,
            selection_hover_pen=selection_hover_pen,
            selection_brush=selection_brush,
            selection_hover_brush=selection_hover_brush,
            xy_region_selection_crosshair=xy_region_selection_crosshair,
            xy_region_selection_handles=xy_region_selection_handles,
        )
        self._plot_legend = self._plot_widget.addLegend()
        self._plot_legend.hide()
        self._plot_editor = PlotEditorWidget()
        self._plot_selector = PlotSelectorWidget()
        self._position_label = CursorPositionLabel(units=self._plot_editor.units)

        self._plot_editor.layout().setContentsMargins(0, 0, 0, 0)
        self._plot_selector.layout().setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self._position_label, 0, 0)
        layout.addWidget(self._plot_widget, 1, 0)
        layout.addWidget(self._plot_editor, 2, 0, 1, 2)
        layout.addWidget(self._plot_selector, 1, 1)
        layout.setColumnStretch(0, 1)
        layout.setRowStretch(1, 1)
        self.setLayout(layout)

        self._plot_selector.sigSelectionChanged.connect(self._update_plot_selection)
        self._plot_editor.sigUnitsChanged.connect(self.__units_changed)
        self._plot_editor.sigLabelsChanged.connect(self.__labels_changed)
        self._plot_editor.sigLimitsChanged.connect(self.__limits_changed)
        self._plot_editor.sigAutoRangeClicked.connect(self.set_auto_range)
        self._plot_widget.sigRangeChanged.connect(self.__plot_widget_limits_changed)
        self._plot_widget.sigMouseMoved.connect(self._position_label.update_position)

        self.__labels_changed(*self.labels)
        self.__units_changed(*self.units)
        self.set_auto_range(True, True)

        # patch attributes of advanced PlotWidget into this widget for easier access and
        # auto-completion
        self.set_rubberband_zoom_selection_mode = self._plot_widget.set_rubberband_zoom_selection_mode
        self.set_region_selection_mode = self._plot_widget.set_region_selection_mode
        self.set_marker_selection_mode = self._plot_widget.set_marker_selection_mode
        self.set_selection_mutable = self._plot_widget.set_selection_mutable
        self.set_selection_bounds = self._plot_widget.set_selection_bounds
        self.add_region_selection = self._plot_widget.add_region_selection
        self.add_marker_selection = self._plot_widget.add_marker_selection
        self.move_region_selection = self._plot_widget.move_region_selection
        self.move_marker_selection = self._plot_widget.move_marker_selection
        self.clear_marker_selections = self._plot_widget.clear_marker_selections
        self.delete_marker_selection = self._plot_widget.delete_marker_selection
        self.hide_marker_selections = self._plot_widget.hide_marker_selections
        self.show_marker_selections = self._plot_widget.show_marker_selections
        self.hide_marker_selection = self._plot_widget.hide_marker_selection
        self.show_marker_selection = self._plot_widget.show_marker_selection
        self.clear_region_selections = self._plot_widget.clear_region_selections
        self.delete_region_selection = self._plot_widget.delete_region_selection
        self.hide_region_selections = self._plot_widget.hide_region_selections
        self.show_region_selections = self._plot_widget.show_region_selections
        self.hide_region_selection = self._plot_widget.hide_region_selection
        self.show_region_selection = self._plot_widget.show_region_selection

        # Disable bugged pyqtgraph interactive mouse menu options to avoid a myriad of
        # user-induced errors.
        for action in self._plot_widget.getPlotItem().ctrlMenu.actions():
            if action.text() not in ('Alpha', 'Grid', 'Points'):
                action.setEnabled(False)
                action.setVisible(False)
        for axis_ctrl in self._plot_widget.getViewBox().menu.ctrl:
            axis_ctrl.autoPanCheck.setEnabled(False)
            axis_ctrl.visibleOnlyCheck.setEnabled(False)
            axis_ctrl.linkCombo.setEnabled(False)
            axis_ctrl.label.setEnabled(False)
            axis_ctrl.autoPanCheck.setVisible(False)
            axis_ctrl.visibleOnlyCheck.setVisible(False)
            axis_ctrl.linkCombo.setVisible(False)
            axis_ctrl.label.setVisible(False)

        # Keep track of PlotItems plotted
        self._plot_items = dict()
        self._fit_plot_items = dict()

    def _get_valid_generic_name(self, index: Optional[int] = 1) -> str:
        name = f'Dataset {index:d}'
        if name in self._plot_items:
            return self._get_valid_generic_name(index + 1)
        return name

    def plot(self, name: Optional[str] = None, **kwargs) -> str:
        # Delete old plot if present
        if name is None:
            name = self._get_valid_generic_name()
        elif name in self._plot_items:
            self.remove_plot(name)
        # Add new plot and enable antialias by default if not explicitly set
        antialias = kwargs.pop('antialias', True)
        item = self._plot_widget.plot(name=name, antialias=antialias, **kwargs)
        self._plot_items[name] = item
        self._plot_selector.add_selector(name=name, item=item, selected=True)
        return name

    def remove_plot(self, name: str) -> None:
        self.remove_fit_plot(name)
        item = self._plot_items.pop(name, None)
        if item in self._plot_widget.getViewBox().addedItems:
            self._plot_widget.removeItem(item)
        try:
            self._plot_selector.remove_selector(name)
        except ValueError:
            pass

    def clear(self) -> None:
        for name in list(self._plot_items):
            self.remove_plot(name)

    def clear_fits(self) -> None:
        for name in list(self._fit_plot_items):
            self.remove_fit_plot(name)

    def plot_fit(self, name: str, **kwargs) -> None:
        if name not in self._plot_items:
            raise ValueError(f'No plot with name "{name}" found to add fit to')
        # Delete old plot if present
        if name in self._fit_plot_items:
            self.remove_fit_plot(name)
        # Add new plot and enable antialias by default if not explicitly set
        antialias = kwargs.pop('antialias', True)
        item = self._plot_widget.plot(name=None, antialias=antialias, **kwargs)
        self._fit_plot_items[name] = item

    def remove_fit_plot(self, name: str) -> None:
        item = self._fit_plot_items.pop(name, None)
        if item in self._plot_widget.getViewBox().addedItems:
            self._plot_widget.removeItem(item)

    def set_data(self, name: str, *args, **kwargs) -> None:
        """ See pyqtgraph.PlotDataItem.__init__ for valid arguments """
        self._plot_items[name].setData(*args, **kwargs)

    def set_fit_data(self, name: str, *args, **kwargs) -> None:
        """ See pyqtgraph.PlotDataItem.__init__ for valid arguments """
        if name not in self._fit_plot_items:
            self.plot_fit(name)
        self._fit_plot_items[name].setData(*args, **kwargs)

    @property
    def plot_names(self) -> List[str]:
        return list(self._plot_items)

    @property
    def plot_selection(self) -> Dict[str, bool]:
        return {name: item.isVisible() for name, item in self._plot_items.items()}

    def set_plot_selection(self, selection: Mapping[str, bool]) -> None:
        self._plot_selector.set_selection(selection)
        self._update_plot_selection(selection)

    def set_auto_range(self, x: Optional[bool] = None, y: Optional[bool] = None) -> None:
        if x is y is None:
            return
        if x is not None:
            self._plot_widget.enableAutoRange(axis='x', enable=x)
        if y is not None:
            self._plot_widget.enableAutoRange(axis='y', enable=y)
        self.sigAutoLimitsApplied.emit(bool(x), bool(y))

    def set_labels(self, x: Optional[str] = None, y: Optional[str] = None) -> None:
        self._plot_editor.set_labels(x, y)
        self.__labels_changed(*self.labels)

    def set_units(self, x: Optional[str] = None, y: Optional[str] = None) -> None:
        self._plot_editor.set_units(x, y)
        self.__units_changed(*self.units)

    def set_limits(self,
                   x: Optional[Tuple[float, float]] = None,
                   y: Optional[Tuple[float, float]] = None
                   ) -> None:
        self._plot_editor.set_limits(x, y)
        self.__limits_changed(*self.limits)

    # Start of attribute/property wrapping of sub-widgets

    @property
    def sigMarkerSelectionChanged(self) -> QtCore.Signal:
        return self._plot_widget.sigMarkerSelectionChanged

    @property
    def sigRegionSelectionChanged(self) -> QtCore.Signal:
        return self._plot_widget.sigRegionSelectionChanged

    @property
    def sigMouseMoved(self) -> QtCore.Signal:
        return self._plot_widget.sigMouseMoved

    @property
    def sigMouseDragged(self) -> QtCore.Signal:
        return self._plot_widget.sigMouseDragged

    @property
    def sigMouseClicked(self) -> QtCore.Signal:
        return self._plot_widget.sigMouseClicked

    @property
    def sigZoomAreaApplied(self) -> QtCore.Signal:
        return self._plot_widget.sigZoomAreaApplied

    @property
    def labels(self) -> Tuple[str, str]:
        return self._plot_editor.labels

    @property
    def units(self) -> Tuple[str, str]:
        return self._plot_editor.units

    @property
    def limits(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        return self._plot_editor.limits

    @property
    def rubberband_zoom_selection_mode(self) -> SelectionMode:
        return self._plot_widget.rubberband_zoom_selection_mode

    @property
    def marker_selection(self) -> Dict[SelectionMode, List[Union[float, Tuple[float, float]]]]:
        return self._plot_widget.marker_selection

    @property
    def region_selection(self) -> Dict[SelectionMode, List[tuple]]:
        return self._plot_widget.region_selection

    @property
    def region_selection_mode(self) -> SelectionMode:
        return self._plot_widget.region_selection_mode

    @property
    def marker_selection_mode(self) -> SelectionMode:
        return self._plot_widget.marker_selection_mode

    @property
    def selection_mutable(self) -> bool:
        return self._plot_widget.selection_mutable

    @property
    def selection_bounds(self) -> Union[None, List[Union[None, Tuple[float, float]]]]:
        return self._plot_widget.selection_bounds

    @property
    def allow_tracking_outside_data(self) -> bool:
        return self._plot_widget.allow_tracking_outside_data

    @allow_tracking_outside_data.setter
    def allow_tracking_outside_data(self, allow: bool) -> None:
        self._plot_widget.allow_tracking_outside_data = bool(allow)

    # Start of methods to show/hide sub-widgets

    def toggle_plot_selector(self, enable: bool) -> None:
        # Sync legend and selector checkboxes
        if not self._plot_selector.isVisible() and enable:
            self._plot_selector.set_selection(self.plot_selection)
        self._plot_selector.setVisible(enable)
        self._plot_legend.setVisible(not enable)

    def toggle_plot_editor(self, enable: bool) -> None:
        self._plot_editor.setVisible(enable)

    def toggle_cursor_position(self, enable: bool) -> None:
        is_enabled = self._position_label.isVisible()
        self._position_label.setVisible(enable)
        if is_enabled and not enable:
            self._plot_widget.sigMouseMoved.disconnect(self._position_label.update_position)
        elif not is_enabled and enable:
            self._plot_widget.sigMouseMoved.connect(self._position_label.update_position)

    # Start of slots for internal updates

    def _update_plot_selection(self, selection: Mapping[str, bool]) -> None:
        for name, selected in selection.items():
            try:
                self._plot_items[name].setVisible(selected)
            except KeyError:
                pass
            else:
                try:
                    self._fit_plot_items[name].setVisible(selected)
                except KeyError:
                    pass

    def __units_changed(self, x: Optional[str] = None, y: Optional[str] = None) -> None:
        if x is y is None:
            return
        x_label, y_label = self.labels
        if x is not None:
            self._plot_widget.setLabel('bottom', x_label, units=x)
        if y is not None:
            self._plot_widget.setLabel('left', y_label, units=y)
        self._position_label.set_units(*self.units)
        self.sigPlotParametersChanged.emit()

    def __labels_changed(self, x: Optional[str] = None, y: Optional[str] = None) -> None:
        if x is y is None:
            return
        x_unit, y_unit = self.units
        if x is not None:
            self._plot_widget.setLabel('bottom', x, units=x_unit)
        if y is not None:
            self._plot_widget.setLabel('left', y, units=y_unit)
        self.sigPlotParametersChanged.emit()

    def __limits_changed(self,
                         x: Optional[Tuple[float, float]] = None,
                         y: Optional[Tuple[float, float]] = None
                         ) -> None:
        if x is y is None:
            return
        if x is not None:
            self._plot_widget.enableAutoRange(axis='x', enable=False)
            self._plot_widget.setXRange(*x, padding=0)
        if y is not None:
            self._plot_widget.enableAutoRange(axis='y', enable=False)
            self._plot_widget.setYRange(*y, padding=0)
        # Signal is emitted once the pyqtgraph plot has actually changed.
        # See: self.__plot_widget_limits_changed

    def __plot_widget_limits_changed(self,
                                     _,
                                     limits: Tuple[Tuple[float, float], Tuple[float, float]]
                                     ) -> None:
        self._plot_editor.set_limits(*limits)
        self.sigPlotParametersChanged.emit()
