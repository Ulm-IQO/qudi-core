# -*- coding: utf-8 -*-

"""
This file contains a modified pyqtgraph ViewBox for qudi to track mouse activity inside data plots.

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

__all__ = ['MouseTrackingViewBox']

from typing import Optional
from PySide2 import QtCore
from pyqtgraph import ViewBox, SignalProxy
from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent, MouseDragEvent


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
                slot=self._mouse_moved
            )

    def _mouse_moved(self, args) -> None:
        pos = self.mapSceneToView(args[0])
        self.sigMouseMoved.emit((pos.x(), pos.y()))

    def mouseClickEvent(self, ev: MouseClickEvent) -> None:
        pos = self.mapToView(ev.pos())
        self.sigMouseClicked.emit((pos.x(), pos.y()), ev)
        return super().mouseClickEvent(ev)

    def mouseDragEvent(self, ev: MouseDragEvent, axis: Optional[int] = None) -> None:
        start = self.mapToView(ev.buttonDownPos())
        current = self.mapToView(ev.pos())
        self.sigMouseDragged.emit((start.x(), start.y()), (current.x(), current.y()), ev)
        return super().mouseDragEvent(ev, axis)
