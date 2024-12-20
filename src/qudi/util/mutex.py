# -*- coding: utf-8 -*-
"""
Stand-in extension of Qt's QMutex and QRecursiveMutex classes.
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

__all__ = ['Mutex', 'RecursiveMutex']

from PySide2.QtCore import QMutex as _QMutex
from PySide2.QtCore import QRecursiveMutex as _QRecursiveMutex
from typing import Optional, Union


_RealNumber = Union[int, float]


class Mutex(_QMutex):
    """Extends QMutex which serves as access serialization between threads.

    This class provides:
    * Drop-in replacement for threading.Lock
    * Context management (enter/exit)
    """

    def acquire(self, blocking: Optional[bool] = True, timeout: Optional[_RealNumber] =
-1) -> bool:
        """
        Mimics threading.Lock.acquire() to allow this class as a drop-in replacement.

        Parameters
        ----------
        blocking : bool, optional
            If True, this method will block until the mutex is locked (up to <timeout> seconds).
            If False, this method will return immediately regardless of the lock status. Default is True.
        timeout : float, optional
            Timeout in seconds specifying the maximum wait time for the mutex to be able to lock.
            Negative numbers correspond to infinite wait time. This parameter is ignored if blocking is False.
            Default is -1.0.

        """
        if blocking:
            # Convert to milliseconds for QMutex
            return self.tryLock(max(-1, int(timeout * 1000)))
        return self.tryLock()

    def release(self) -> None:
        """Mimics threading.Lock.release() to allow this class as a drop-in replacement.
        """
        self.unlock()

    def __enter__(self):
        """Enter context.

        Returns
        -------
        Mutex
            This mutex object itself.
        """
        self.lock()
        return self

    def __exit__(self, *args):
        """Exit context.

        Parameters
        ----------
        *args
            Context arguments (type, value, traceback) passed to the method.
        """
        self.unlock()


# Compatibility workaround for PySide2 vs. PySide6. In PySide2 we need to use QMutex with an
# initializer argument to construct a recursive mutex but in PySide6 we need to subclass
# QRecursiveMutex. Check if QRecursiveMutex class has all API members (indicating it's PySide6).
if all(hasattr(_QRecursiveMutex, attr) for attr in ('lock', 'unlock', 'tryLock')):
    class RecursiveMutex(_QRecursiveMutex):
        """Extends QRecursiveMutex which serves as access serialization between threads.

        This class provides:
        * Drop-in replacement for threading.Lock
        * Context management (enter/exit)

        NOTE: A recursive mutex is much more expensive than using a regular mutex. So consider
        refactoring your code to use a simple mutex before using this object.
        """

        def acquire(
            self, blocking: Optional[bool] = True, timeout: Optional[_RealNumber] = -1
        ) -> bool:
            """
            Mimics threading.Lock.acquire() to allow this class as a drop-in replacement.

            Parameters
            ----------
            blocking : bool, optional
                If True, this method will block until the mutex is locked (up to <timeout> seconds).
                If False, this method will return immediately regardless of the lock status. Default is True.
            timeout : float, optional
                Timeout in seconds specifying the maximum wait time for the mutex to be able to lock.
                Negative numbers correspond to infinite wait time. This parameter is ignored if blocking is False.
                Default is -1.0.

            Returns
            -------
            Mutex
                This mutex object itself.

            """
            if blocking:
                # Convert to milliseconds for QMutex
                return self.tryLock(max(-1, int(timeout * 1000)))
            return self.tryLock()

        def release(self) -> None:
            """Mimics threading.Lock.release() to allow this class as a drop-in replacement.
            """
            self.unlock()

        def __enter__(self):
            """
            Enter the context managed by this mutex.

            Returns
            -------
            RecursiveMutex
                This mutex object itself.

            """
            self.lock()
            return self

        def __exit__(self, *args):
            """
            Exit the context managed by this mutex.

            Parameters
            ----------
            *args
                Context arguments (type, value, traceback) passed to the method.

            """
            self.unlock()

else:
    class RecursiveMutex(Mutex):
        """Extends QRecursiveMutex which serves as access serialization between threads.

        This class provides:
        * Drop-in replacement for threading.Lock
        * Context management (enter/exit)

        NOTE: A recursive mutex is much more expensive than using a regular mutex. So consider
        refactoring your code to use a simple mutex before using this object.
        """
        def __init__(self):
            super().__init__(_QMutex.Recursive)
