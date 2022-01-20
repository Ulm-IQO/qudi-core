# -*- coding: utf-8 -*-

"""
This file contains a custom QWidget to wrap a collapsible widget with expand/collapse animation.

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

__all__ = ['CollapsibleWidget']


from PySide2 import QtCore, QtWidgets
from typing import Optional


class CollapsibleWidget(QtWidgets.QWidget):
    """ ToDo: Document
    """

    sigCollapsedChanged = QtCore.Signal(bool)  # True: Collapsed, False: Expanded

    def __init__(self,
                 widget: QtWidgets.QWidget,
                 title: Optional[str] = '',
                 animation_duration: Optional[float] = 0.2,
                 parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)
        if animation_duration is None:
            animation_duration = 0.2

        self._last_collapsed = True

        self.expand_collapse_button = QtWidgets.QToolButton()
        self.expand_collapse_button.setStyleSheet(
            'QToolButton { border: none; background-color: none; }'
        )
        self.expand_collapse_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.expand_collapse_button.setArrowType(QtCore.Qt.RightArrow)
        self.expand_collapse_button.setText(title if title else '')
        self.expand_collapse_button.setCheckable(True)

        widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        widget.setMaximumHeight(0)
        widget.setMinimumHeight(0)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.expand_collapse_button)
        layout.addWidget(widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Animations to adjust max and min height of this widget and content widget
        self._min_height_animation = QtCore.QPropertyAnimation(self, b"minimumHeight")
        self._max_height_animation = QtCore.QPropertyAnimation(self, b"maximumHeight")
        self._widget_max_height_animation = QtCore.QPropertyAnimation(widget, b"maximumHeight")
        collapsed_height = self.sizeHint().height() - widget.maximumHeight()
        widget_height = widget.sizeHint().height()
        self._min_height_animation.setStartValue(collapsed_height)
        self._min_height_animation.setEndValue(collapsed_height + widget_height)
        self._max_height_animation.setStartValue(collapsed_height)
        self._max_height_animation.setEndValue(collapsed_height + widget_height)
        self._widget_max_height_animation.setStartValue(0)
        self._widget_max_height_animation.setEndValue(widget_height)
        self._animation_group = QtCore.QParallelAnimationGroup()
        self._animation_group.addAnimation(self._min_height_animation)
        self._animation_group.addAnimation(self._max_height_animation)
        self._animation_group.addAnimation(self._widget_max_height_animation)

        self.set_animation_duration(animation_duration)

        self.expand_collapse_button.toggled[bool].connect(self._start_animation)
        self._animation_group.finished.connect(self._animation_finished)

    @property
    def collapsed(self) -> bool:
        if self._min_height_animation.startValue() == self.minimumHeight():
            return True
        if self._min_height_animation.endValue() == self.minimumHeight():
            return False
        return self._last_collapsed

    @property
    def animation_duration(self) -> float:
        return self._min_height_animation.duration() / 1000.

    def set_collapsed(self, collapse: bool) -> None:
        self.expand_collapse_button.setChecked(not collapse)

    def set_animation_duration(self, duration: float) -> None:
        duration_ms = int(round(1000 * duration))
        self._min_height_animation.setDuration(duration_ms)
        self._max_height_animation.setDuration(duration_ms)
        self._widget_max_height_animation.setDuration(duration_ms)

    @QtCore.Slot(bool)
    def _start_animation(self, checked: bool) -> None:
        if checked:
            arrow_type = QtCore.Qt.DownArrow
            direction = QtCore.QAbstractAnimation.Forward
        else:
            arrow_type = QtCore.Qt.RightArrow
            direction = QtCore.QAbstractAnimation.Backward
        self.expand_collapse_button.setArrowType(arrow_type)
        self._animation_group.setDirection(direction)
        self._animation_group.start()

    @QtCore.Slot()
    def _animation_finished(self) -> None:
        collapsed = self.collapsed
        if collapsed != self._last_collapsed:
            self._last_collapsed = collapsed
            self.sigCollapsedChanged.emit(collapsed)
