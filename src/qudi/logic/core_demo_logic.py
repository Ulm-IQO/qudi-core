# -*- coding: utf-8 -*-
"""
FIXME

Copyright (c) 2022, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-iqo-modules/>

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

import numpy as np
from time import perf_counter, sleep
from PySide2 import QtCore

from qudi.core.module import LogicBase
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.statusvariable import StatusVar
from qudi.util.mutex import Mutex


class CoreDemoLogic(LogicBase):
    """ FIXME
    """

    _follow_min_step_interval = ConfigOption(name='follow_min_step_interval', default=0.1, missing='warn')
    _follow_hardware_delay = ConfigOption(name='follow_hardware_delay', default=0, missing='warn')

    _follow_velocity = StatusVar(name='follow_velocity', default=0.0002)

    sigFollowPositionChanged = QtCore.Signal(tuple)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._thread_lock = Mutex()
        self._follow_target_pos = np.array([0.0, 0.0])
        self._follow_current_pos = np.array([0.0, 0.0])
        self.__follow_timer = None
        self.__last_follow = None

    def on_activate(self):
        """ Activate module
        """
        self._follow_target_pos = np.array([0.0, 0.0])
        self._follow_current_pos = np.array([0.0, 0.0])
        self.__last_follow = None
        self.__follow_timer = QtCore.QTimer(parent=self)
        self.__follow_timer.setSingleShot(True)
        self.__follow_timer.timeout.connect(self.__follow_loop_body, QtCore.Qt.QueuedConnection)

    def on_deactivate(self):
        """ Deactivate module
        """
        self.__follow_timer.stop()
        self.__follow_timer.timeout.disconnect()
        self.__follow_timer.setParent(None)
        self.__follow_timer = None
        self.__last_follow = None

    @property
    def follow_velocity(self):
        with self._thread_lock:
            return self._follow_velocity

    @follow_velocity.setter
    def follow_velocity(self, val):
        with self._thread_lock:
            self._follow_velocity = float(val)

    @property
    def target_follow_pos(self):
        with self._thread_lock:
            return tuple(self._follow_target_pos)

    @property
    def current_follow_pos(self):
        with self._thread_lock:
            return tuple(self._follow_current_pos)

    def set_follow_target_pos(self, pos):
        with self._thread_lock:
            self._follow_target_pos[:] = pos
            self.__start_loop()

    def __start_loop(self):
        if self.__last_follow is None:
            if self.thread() is not QtCore.QThread.currentThread():
                QtCore.QMetaObject.invokeMethod(self,
                                                '__start_loop',
                                                QtCore.Qt.BlockingQueuedConnection)
            else:
                self.__last_follow = perf_counter()
                self.__follow_timer.start(0)
                print('====> loop started!')

    def __follow_loop_body(self):
        with self._thread_lock:
            # Terminate follow loop if target is reached
            if np.array_equal(self._follow_target_pos, self._follow_current_pos):
                self.__last_follow = None
                print('====> loop finished!')
                return

            # Determine delta t and update timestamp for next iteration
            now = perf_counter()
            delta_t = now - self.__last_follow
            self.__last_follow = now

            # Calculate new position to go to
            max_step_distance = delta_t * self._follow_velocity
            connecting_vec = self._follow_target_pos - self._follow_current_pos
            distance_to_target = np.linalg.norm(connecting_vec)
            if max_step_distance < distance_to_target:
                direction_vec = connecting_vec / distance_to_target
                self._follow_current_pos += max_step_distance * direction_vec
            else:
                self._follow_current_pos[:] = self._follow_target_pos[:]
            sleep(self._follow_hardware_delay)
            self.sigFollowPositionChanged.emit(tuple(self._follow_current_pos))

            # Start single-shot timer to call this follow loop again after some wait time
            overhead = perf_counter() - now
            self.__follow_timer.start(
                int(round(1000 * max(0, self._follow_min_step_interval - overhead)))
            )


