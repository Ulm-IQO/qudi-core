# -*- coding: utf-8 -*-
"""
Parent poller mechanism from IPython.

Copyright (c) 2015, IPython Development Team

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

__all__ = ['ParentPollerUnix', 'ParentPollerWindows']

import ctypes
import os
import platform
import time
from threading import Thread
import logging

logger = logging.getLogger(__name__)


class ParentPollerUnix(Thread):
    """ A Unix-specific daemon thread that terminates the program immediately
    when the parent process no longer exists.
    """

    def __init__(self, quit_function=None):
        """ Create the parentpoller.

            @param callable quitfunction: function to run before exiting
        """
        if quit_function is None:
            pass
        elif not callable(quit_function):
            raise TypeError('argument quit_function must be a callable.')
        super().__init__()
        self.daemon = True
        self.quit_function = quit_function

    def run(self):
        """ Run the parentpoller.
        """
        # We cannot use os.waitpid because it works only for child processes.
        from errno import EINTR
        while True:
            try:
                if os.getppid() == 1:
                    if self.quit_function is None:
                        logger.critical('Parent process died!')
                    else:
                        logger.critical('Parent process died! Qudi shutting down...')
                        self.quit_function()
                    return
            except OSError as e:
                if e.errno == EINTR:
                    continue
                raise
            time.sleep(1)


class ParentPollerWindows(Thread):
    """ A Windows-specific daemon thread that listens for a special event that signals an interrupt
    and, optionally, terminates the program immediately when the parent process no longer exists.
    """

    def __init__(self, parent_handle, quit_function=None):
        """ Create the parent poller.

        @param callable quit_function: Function to call for shutdown if parent process is dead.
        @param int parent_handle: The program will terminate immediately when this handle is
                                  signaled.
        """
        if quit_function is None:
            pass
        elif not callable(quit_function):
            raise TypeError('argument quit_function must be a callable.')
        super().__init__()
        self.daemon = True
        self.quit_function = quit_function
        self.parent_handle = parent_handle
        self._stop_requested = False

    def run(self):
        """ Run the poll loop. This method never returns.
        """
        try:
            from _winapi import WAIT_OBJECT_0, INFINITE
        except ImportError:
            from _subprocess import WAIT_OBJECT_0, INFINITE

        # Build the list of handle to listen on.
        handle_list = [self.parent_handle]
        arch = platform.architecture()[0]
        c_int = ctypes.c_int64 if arch.startswith('64') else ctypes.c_int

        # Listen forever.
        while True:
            # Return if stop has been requested
            if self._stop_requested:
                return

            result = ctypes.windll.kernel32.WaitForMultipleObjects(
                len(handle_list),                           # nCount
                (c_int * len(handle_list))(*handle_list),   # lpHandles
                False,                                      # bWaitAll
                1000)                                       # dwMilliseconds

            if result >= len(handle_list):
                # Nothing happened. Probably timed out.
                continue
            elif result < WAIT_OBJECT_0:
                # wait failed, just give up and stop polling.
                logger.critical("Parent poll failed!!!!!")
                return
            else:
                handle = handle_list[result - WAIT_OBJECT_0]
                if handle == self.parent_handle:
                    if self.quit_function is None:
                        logger.critical('Parent process died!')
                    else:
                        logger.critical('Parent process died! Qudi shutting down...')
                        self.quit_function()
                    return

    def stop(self) -> None:
        self._stop_requested = True

    def start(self) -> None:
        self._stop_requested = False
        return super().start()
