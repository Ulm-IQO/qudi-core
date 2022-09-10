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
from typing import Optional, Mapping, Any, Dict, Tuple, Union
from pyqtgraph import mkColor, mkPen

from qudi.util.widgets.scientific_spinbox import ScienDSpinBox
from qudi.util.widgets.separator_lines import VerticalLine
from qudi.util.widgets.plotting.axis import label_nudged_plot_widget
from qudi.util.widgets.plotting.plot_widget import RubberbandZoomSelectionPlotWidget


PlotWidget = label_nudged_plot_widget(RubberbandZoomSelectionPlotWidget)


class PlotEditorWidget(QtWidgets.QWidget):
    """
    """

    sigAutoRangeClicked = QtCore.Signal(bool, bool)
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
        self.x_lower_limit_spinBox.valueChanged.connect(self.__x_limits_changed)
        self.x_upper_limit_spinBox.valueChanged.connect(self.__x_limits_changed)
        self.y_lower_limit_spinBox.valueChanged.connect(self.__y_limits_changed)
        self.y_upper_limit_spinBox.valueChanged.connect(self.__y_limits_changed)
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
        return (self.x_lower_limit_spinBox.value(), self.x_upper_limit_spinBox.value()), \
               (self.y_lower_limit_spinBox.value(), self.y_upper_limit_spinBox.value())

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
            self.x_lower_limit_spinBox.blockSignals(True)
            self.x_upper_limit_spinBox.blockSignals(True)
            try:
                self.x_lower_limit_spinBox.setValue(lower)
                self.x_upper_limit_spinBox.setValue(upper)
            finally:
                self.x_lower_limit_spinBox.blockSignals(False)
                self.x_upper_limit_spinBox.blockSignals(False)
        if y is not None:
            lower, upper = sorted(y)
            self.y_lower_limit_spinBox.blockSignals(True)
            self.y_upper_limit_spinBox.blockSignals(True)
            try:
                self.y_lower_limit_spinBox.setValue(lower)
                self.y_upper_limit_spinBox.setValue(upper)
            finally:
                self.y_lower_limit_spinBox.blockSignals(False)
                self.y_upper_limit_spinBox.blockSignals(False)

    def __x_limits_changed(self) -> None:
        self.sigLimitsChanged.emit(self.limits[0], None)

    def __y_limits_changed(self) -> None:
        self.sigLimitsChanged.emit(None, self.limits[1])

    def __x_label_changed(self) -> None:
        self.sigLabelsChanged.emit(self.labels[0], None)

    def __y_label_changed(self) -> None:
        self.sigLabelsChanged.emit(None, self.labels[1])

    def __x_unit_changed(self) -> None:
        self.sigUnitsChanged.emit(self.units[0], None)

    def __y_unit_changed(self) -> None:
        self.sigUnitsChanged.emit(None, self.units[1])


class PlotSelectorWidget(QtWidgets.QWidget):
    """
    """
    sigSelectionChanged = QtCore.Signal(dict)  # selection

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent=parent)

        self._stretch = QtWidgets.QSpacerItem(
            0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self._selector_layout = QtWidgets.QVBoxLayout()
        self._selector_layout.addItem(self._stretch)
        self.setLayout(self._selector_layout)

        self._selectors = dict()

    @property
    def selection(self) -> Dict[str, bool]:
        return {name: selector.isChecked() for name, selector in self._selectors.items()}

    def set_selection(self, selection: Mapping[str, bool]) -> None:
        for name, select in selection.items():
            self._selectors[name].setChecked(select)

    def add_selector(self,
                     name: str,
                     color: Optional[Any] = None,
                     selected: Optional[bool] = False) -> None:
        if name in self._selectors:
            raise ValueError(f'Selector with name "{name}" already present in plot selector')
        selector = self._create_selector(name, color)
        selector.setChecked(selected)
        selector.clicked.connect(self._selection_changed)
        self._selector_layout.removeItem(self._stretch)
        self._selector_layout.addWidget(selector)
        self._selector_layout.addItem(self._stretch)
        self._selectors[name] = selector

    def remove_selector(self, name: str) -> None:
        widgets = list(self._selectors.values())
        selector = self._selectors.pop(name, None)
        if selector is None:
            raise ValueError(f'Selector with name "{name}" not found in plot selector')
        remove_index = widgets.index(selector)
        widgets = widgets[remove_index + 1:]
        self._selector_layout.removeItem(self._stretch)
        for widget in reversed(widgets):
            self._selector_layout.removeWidget(widget)
        self._selector_layout.removeWidget(selector)
        for widget in widgets:
            self._selector_layout.addWidget(widget)
        self._selector_layout.addItem(self._stretch)
        selector.clicked.disconnect()
        selector.setParent(None)

    def _selection_changed(self) -> None:
        self.sigSelectionChanged.emit(self.selection)

    @staticmethod
    def _create_selector(name: str, color: Optional[Any] = None) -> QtWidgets.QCheckBox:
        checkbox = QtWidgets.QCheckBox(name)
        if color is not None:
            color_str = mkColor(color).name()
            checkbox.setStyleSheet('QCheckBox { color: ' + color_str + ' }')
        return checkbox


class InteractiveCurvesWidget(QtWidgets.QWidget):
    """
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent=parent)

        self.plot_widget = PlotWidget()
        self.plot_legend = self.plot_widget.addLegend()
        self.plot_legend.hide()
        self.plot_editor = PlotEditorWidget()
        self.plot_selector = PlotSelectorWidget()

        self.plot_editor.layout().setContentsMargins(0, 0, 0, 0)
        self.plot_selector.layout().setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.plot_widget, 0, 0)
        layout.addWidget(self.plot_editor, 1, 0, 1, 2)
        layout.addWidget(self.plot_selector, 0, 1)
        layout.setColumnStretch(0, 1)
        layout.setRowStretch(0, 1)
        self.setLayout(layout)

        self.plot_selector.sigSelectionChanged.connect(self._update_plot_selection)
        self.plot_editor.sigUnitsChanged.connect(self.__units_changed)
        self.plot_editor.sigLabelsChanged.connect(self.__labels_changed)
        self.plot_editor.sigLimitsChanged.connect(self.__limits_changed)
        self.plot_editor.sigAutoRangeClicked.connect(self.set_auto_range)
        self.plot_widget.sigRangeChanged.connect(self.__plot_widget_limits_changed)

        self.set_limits = self.plot_editor.set_limits
        self.set_units = self.plot_editor.set_units
        self.set_labels = self.plot_editor.set_labels
        self.set_selection = self.plot_selector.set_selection

        self.__labels_changed(*self.labels)
        self.__units_changed(*self.units)
        self.set_auto_range(True, True)

        self._plot_items = dict()

        # Disable bugged pyqtgraph interactive mouse menu options to avoid a myriad of
        # user-induced errors.
        for action in self.plot_widget.getPlotItem().ctrlMenu.actions():
            if action.text() not in ('Alpha', 'Grid', 'Points'):
                action.setEnabled(False)
                action.setVisible(False)
        for axis_ctrl in self.plot_widget.getPlotItem().vb.menu.ctrl:
            axis_ctrl.autoPanCheck.setEnabled(False)
            axis_ctrl.visibleOnlyCheck.setEnabled(False)
            axis_ctrl.linkCombo.setEnabled(False)
            axis_ctrl.label.setEnabled(False)
            axis_ctrl.autoPanCheck.setVisible(False)
            axis_ctrl.visibleOnlyCheck.setVisible(False)
            axis_ctrl.linkCombo.setVisible(False)
            axis_ctrl.label.setVisible(False)

    @property
    def labels(self) -> Tuple[str, str]:
        return self.plot_editor.labels

    @property
    def units(self) -> Tuple[str, str]:
        return self.plot_editor.units

    @property
    def limits(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        return self.plot_editor.limits

    @property
    def selection(self) -> Dict[str, bool]:
        return self.plot_selector.selection

    def plot(self, name: str, **kwargs) -> None:
        # Delete old plot if present
        if name in self._plot_items:
            self.remove_plot(name)
        # Add new plot
        item = self.plot_widget.plot(name=name, **kwargs)
        self._plot_items[name] = item
        try:
            color = mkPen(item.opts['pen']).color()
        except (KeyError, AttributeError, TypeError, ValueError):
            color = None
        self.plot_selector.add_selector(name=name, color=color, selected=True)

    def remove_plot(self, name: str) -> None:
        item = self._plot_items.pop(name, None)
        if item in self.plot_widget.items():
            self.plot_widget.removeItem(item)
        try:
            self.plot_selector.remove_selector(name)
        except ValueError:
            pass

    def toggle_plot_selection(self, enable: bool) -> None:
        self.plot_selector.setVisible(enable)
        self.plot_legend.setVisible(not enable)

    def toggle_plot_editor(self, enable: bool) -> None:
        self.plot_editor.setVisible(enable)

    def set_auto_range(self, x: Optional[bool] = None, y: Optional[bool] = None) -> None:
        if x is not None:
            self.plot_widget.enableAutoRange(axis='x', enable=x)
        if y is not None:
            self.plot_widget.enableAutoRange(axis='y', enable=y)

    def _update_plot_selection(self, selection: Mapping[str, bool]) -> None:
        for name, selected in selection.items():
            try:
                item = self._plot_items[name]
            except KeyError:
                continue
            item_in_plot = item in self.plot_widget.items()
            if selected and not item_in_plot:
                self.plot_widget.addItem(item)
            elif not selected and item_in_plot:
                self.plot_widget.removeItem(item)

    def __units_changed(self, x: Optional[str] = None, y: Optional[str] = None) -> None:
        x_label, y_label = self.labels
        if x is not None:
            self.plot_widget.setLabel('bottom', x_label, units=x)
        if y is not None:
            self.plot_widget.setLabel('left', y_label, units=y)

    def __labels_changed(self, x: Optional[str] = None, y: Optional[str] = None) -> None:
        x_unit, y_unit = self.units
        if x is not None:
            self.plot_widget.setLabel('bottom', x, units=x_unit)
        if y is not None:
            self.plot_widget.setLabel('left', y, units=y_unit)

    def __limits_changed(self,
                         x: Optional[Tuple[float, float]] = None,
                         y: Optional[Tuple[float, float]] = None
                         ) -> None:
        if x is not None:
            self.plot_widget.enableAutoRange(axis='x', enable=False)
            self.plot_widget.setXRange(*x, padding=0)
        if y is not None:
            self.plot_widget.enableAutoRange(axis='y', enable=False)
            self.plot_widget.setYRange(*y, padding=0)

    def __plot_widget_limits_changed(self,
                                     _,
                                     limits: Tuple[Tuple[float, float], Tuple[float, float]]
                                     ) -> None:
        self.plot_editor.set_limits(*limits)
