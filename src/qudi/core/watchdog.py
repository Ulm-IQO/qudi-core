# -*- coding: utf-8 -*-

"""
This file contains the qudi application watchdog.
Derived from the ACQ4 project.

Copyright (c) 2010, Luke Campagnola.

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

__all__ = ['AppWatchdog']

import os
import sys
import signal
from PySide6 import QtCore
from qudi.core.parentpoller import ParentPollerWindows, ParentPollerUnix
from qudi.core.logger import get_logger

logger = get_logger(__name__)


class AppWatchdog(QtCore.QObject):
    """This class periodically runs a function for debugging and handles application exit.
    """

    def __init__(self, quit_function):
        super().__init__()
        # Run python code periodically to allow interactive debuggers to interrupt the qt event loop
        self.__timer = QtCore.QTimer()
        self.__timer.timeout.connect(self.do_nothing)
        self.__timer.start(1000)

        # Listen to SIGINT and terminate
        if sys.platform == 'win32':
            signal.signal(signal.SIGINT, lambda *args: quit_function())

        if 'QUDI_PARENT_PID' not in os.environ:
            self.parent_handle = None
            self.parent_poller = None
            logger.warning('Qudi running unsupervised. Restart will not work. Instead Qudi will '
                           'exit with exitcode 42.')
        else:
            self.parent_handle = int(os.environ['QUDI_PARENT_PID'])
            if sys.platform == 'win32':
                self.parent_poller = ParentPollerWindows(self.parent_handle, quit_function)
            else:
                self.parent_poller = ParentPollerUnix(quit_function)
            self.parent_poller.start()
        return

    @QtCore.Slot()
    def do_nothing(self):
        """This function does nothing for debugging purposes.
        """
        x = 0
        for i in range(100):
            x += i
        return

    def terminate(self) -> None:
        try:
            self.parent_poller.stop()
            self.parent_poller.join()
        except AttributeError:
            pass
        finally:
            self.parent_poller = None
            self.parent_handle = None

        try:
            self.__timer.timeout.disconnect()
            self.__timer.stop()
        finally:
            self.__timer = None

