# -*- coding: utf-8 -*-
"""
This file contains the Qudi thread manager singleton class.

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

import weakref
from functools import partial
from PySide2 import QtCore
from typing import List, Dict, Any, Optional, Union, Tuple, final

from qudi.util.mutex import Mutex
from qudi.core.logger import get_logger

_logger = get_logger(__name__)


# @final
class ThreadManager(QtCore.QAbstractListModel):
    """ This class keeps track of all the QThreads that are used throughout qudi. Always use this
    singleton to create and destroy threads and do not create threads manually.

    Using this class is thread-safe.
    """
    _instance = None
    _lock = Mutex()

    _threads: List[QtCore.QThread]
    _names: List[str]
    _name_to_index: Dict[str, int]

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if (cls._instance is None) or (cls._instance() is None):
                obj = super().__new__(cls, *args, **kwargs)
                cls._instance = weakref.ref(obj)
                return obj
            raise TypeError(
                'Only one ThreadManager instance per process possible (Singleton). Please use '
                'ThreadManager.instance() to get a reference to the already created instance.'
            )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._threads = list()
        self._names = list()
        self._name_to_index = dict()

    @classmethod
    def instance(cls):
        with cls._lock:
            try:
                return cls._instance()
            except TypeError:
                return None

    @property
    def thread_names(self) -> List[str]:
        with self._lock:
            return self._names.copy()

    def get_new_thread(self, name: str) -> QtCore.QThread:
        """ Create and return a new QThread with objectName <name> """
        with self._lock:
            if name in self._names:
                raise ValueError(f'Thread with name "{name}" has already been created')
            thread = QtCore.QThread()
            _logger.debug(f'Created new thread: "{name}"')
            self._register_thread(name, thread)
            return thread

    def register_thread(self, name: str, thread: QtCore.QThread) -> None:
        """ Add existing QThread to ThreadManager data model. Try to avoid this method and use
        "get_new_thread" instead of creating your own QThread instances.
        """
        with self._lock:
            return self._register_thread(name, thread)

    def unregister_thread(self, name: str) -> None:
        """ Remove QThread from ThreadManager data model if present. Fails if the thread in
        question is still running.
        """
        with self._lock:
            return self._unregister_thread(name)

    def quit_thread(self, name: str) -> None:
        """ Stop event loop of QThread """
        with self._lock:
            return self._quit_thread(name)

    def join_thread(self, name: str, timeout: Optional[float] = None) -> None:
        """ Wait for event loop of QThread to stop. Call "quit_thread" beforehand.
        An optional timeout in seconds can be set. If the thread does not terminate before this
        time runs out, a TimeoutError is raised.
        """
        with self._lock:
            return self._join_thread(name, timeout)

    def quit_all_threads(self) -> None:
        """ Stop event loops of all QThreads """
        with self._lock:
            for name in self._names:
                self._quit_thread(name)

    def join_all_threads(self, timeout: Optional[float] = None) -> None:
        """ Wait for event loops of all registered QThreads to stop. Call "quit_all_threads"
        beforehand.
        An optional timeout in seconds can be set. If an individual thread does not terminate
        before this time runs out, a TimeoutError is raised. """
        with self._lock:
            for name in self._names:
                self._join_thread(name, timeout)

    def get_thread(self, name: str) -> QtCore.QThread:
        """ Get registered QThread instance by its name """
        with self._lock:
            return self._get_thread(name)[0]

    # Non-threadsafe private methods below
    def _register_thread(self, name: str, thread: QtCore.QThread) -> None:
        """ Add existing QThread to ThreadManager data model """
        # Check if thread has already been registered
        try:
            row = self._name_to_index[name]
        except KeyError:
            pass
        else:
            if self._threads[row] is thread:
                # Thread already registered
                return
            raise ValueError(f'Different thread with name "{name}" already registered') from None

        row = len(self._threads)
        self.beginInsertRows(QtCore.QModelIndex(), row, row)
        thread.setObjectName(name)
        self._threads.append(thread)
        self._names.append(name)
        self._name_to_index[name] = row
        _logger.debug(f'Registered thread: "{name}"')
        self.endInsertRows()

    def _unregister_thread(self, name: str) -> None:
        """ Remove QThread from ThreadManager data model if present. Fails if the thread in
        question is still running.
        """
        try:
            thread, row = self._get_thread(name)
        except ValueError:
            return

        if thread.isRunning():
            raise RuntimeError(f'QThread "{name}" is still running')

        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        del self._threads[row]
        del self._names[row]
        del self._name_to_index[name]
        for name in self._names[row:]:
            self._name_to_index[name] -= 1
        _logger.debug(f'Unregistered thread: "{name}"')
        self.endRemoveRows()

    def _quit_thread(self, name: str) -> None:
        """ Stop event loop of QThread """
        thread, _ = self._get_thread(name)
        thread.quit()
        _logger.debug(f'Quit thread: "{name}"')

    def _join_thread(self, name: str, timeout: Optional[float] = None) -> None:
        """ Wait for event loop of QThread to stop. Call "quit_thread" beforehand.
        An optional timeout in seconds can be set. If the thread does not terminate before this
        time runs out, a TimeoutError is raised.
        """
        thread, _ = self._get_thread(name)
        _logger.debug(f'Joining thread: "{name}"')
        if timeout is None:
            thread.wait()
        elif not thread.wait(int(round(1000 * timeout))):
            raise TimeoutError(f'Joining thread "{name}" timed out after {timeout:.3f} seconds')
        self._unregister_thread(name)

    def _get_thread(self, name: str) -> Tuple[QtCore.QThread, int]:
        """ Get registered QThread instance and row index by its name """
        try:
            row = self._name_to_index[name]
        except KeyError:
            raise ValueError(f'No thread with name "{name}" registered') from None
        return self._threads[row], row

    # QAbstractListModel interface methods follow below
    def rowCount(self, parent=None, *args, **kwargs):
        """
        Gives the number of threads registered.

        @return int: number of threads
        """
        return len(self._threads)

    def headerData(self,
                   section: int,
                   orientation: QtCore.Qt.Orientation,
                   role: Optional[QtCore.Qt.ItemDataRole] = QtCore.Qt.DisplayRole
                   ) -> Union[str, None]:
        """ Data for the list view header """
        if (role == QtCore.Qt.DisplayRole) and (orientation == QtCore.Qt.Horizontal):
            return 'Thread Name'
        return None

    def data(self,
             index: QtCore.QModelIndex,
             role: Optional[QtCore.Qt.ItemDataRole] = QtCore.Qt.DisplayRole) -> Union[str, None]:
        """ Get data from model for a given cell. Data can have a role that affects display. """
        if index.isValid() and (role == QtCore.Qt.DisplayRole):
            row = index.row()
            try:
                return self._names[row]
            except IndexError:
                pass
        return None

    def flags(self, index: QtCore.QModelIndex) -> Union[QtCore.Qt.ItemFlags, QtCore.Qt.ItemFlag]:
        """ Determines what can be done with entry cells in the table view """
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
