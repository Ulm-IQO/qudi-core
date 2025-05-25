# -*- coding: utf-8 -*-
"""
Contains the qudi thread manager singleton as well as a Qt list model to represent the thread names
registered in the thread manager.

Copyright (c) 2021-2024, the qudi developers. See the AUTHORS.md file at the top-level directory
of this distribution and on <https://github.com/Ulm-IQO/qudi-core/>.

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

__all__ = ['ThreadManager', 'ThreadManagerListModel']

import weakref
from PySide2 import QtCore
from typing import Dict, List, Union, Optional

from qudi.util.mutex import RecursiveMutex, Mutex
from qudi.core.logger import get_logger


logger = get_logger(__name__)


class ThreadManager(QtCore.QObject):
    """
    Singleton to keep track of all the QThreads that are needed in a qudi process.
    Public methods and attributes can be considered thread-safe.
    The singleton instance can be obtained during runtime via call to `ThreadManager.instance()`.

    Parameters
    ----------
    parent : QtCore.QObject, optional
        Parent QObject passed on to QtCore.QObject.__init__ (defaults to None).
    """

    _instance = None
    _join_lock = RecursiveMutex()
    _main_lock = Mutex()

    sigThreadRegistered = QtCore.Signal(str)  # thread name
    sigThreadUnregistered = QtCore.Signal(str)  # thread name

    @staticmethod
    def _quit_thread(thread: QtCore.QThread) -> None:
        thread.quit()
        logger.debug(f'Quit thread: "{thread.objectName()}"')

    @staticmethod
    def _join_thread(thread: QtCore.QThread, timeout: Optional[Union[int, float]] = None) -> None:
        name = thread.objectName()
        logger.debug(f'Waiting for thread: "{name}"')
        if (timeout is None) or (timeout <= 0):
            thread.wait()
        else:
            if not thread.wait(int(round(timeout * 1000))):
                raise TimeoutError(f'Thread "{name}" has not terminated after {timeout:.2f} sec')
        logger.debug(f'Joined thread: "{name}"')

    @staticmethod
    def _create_thread(name: str) -> QtCore.QThread:
        """Create a new QThread instance"""
        thread = QtCore.QThread()
        thread.setObjectName(name)
        logger.debug(f'Created new thread: "{name}"')
        return thread

    @classmethod
    def instance(cls) -> Union[None, 'ThreadManager']:
        """Returns the only instance (singleton) of this class."""
        try:
            inst = cls._instance()
        except TypeError:
            inst = None
        return inst

    def __new__(cls, *args, **kwargs):
        with cls._main_lock:
            if cls.instance() is not None:
                raise RuntimeError(
                    'Only one ThreadManager instance per process possible (Singleton). Please use '
                    'ThreadManager.instance() to get a reference to the already created instance.'
                )
            obj = super().__new__(cls, *args, **kwargs)
            cls._instance = weakref.ref(obj)
            return obj

    def __init__(self, parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        self._gen_name_counter: int = 0
        self._threads: Dict[str, QtCore.QThread] = dict()

    @property
    def thread_names(self) -> List[str]:
        """
        Returns
        -------
        list of str
            List of registered thread names.
        """
        return list(self._threads)

    def get_new_thread(self, name: Optional[str] = None) -> QtCore.QThread:
        """Get a new QThread instance with given or generic name.

        Parameters
        ----------
        name : str, optional
            unique name of new thread (default will create a generic name).

        Returns
        -------
        QtCore.QThread
            new thread instance.

        Raises
        ------
        ValueError
            If the given name already exists
        """
        with self._main_lock:
            if not name:
                name = self._generate_name()
            elif name in self._threads:
                raise ValueError(f'Thread with name "{name}" already registered')
            thread = self._create_thread(name)
            self._register_thread(name, thread)
            return thread

    def register_thread(self, thread: QtCore.QThread) -> str:
        """Add a QtCore.QThread instance to ThreadManager.
        If the threads objectName is not set, assign it a generic name.

        Parameters
        ----------
        thread : QtCore.QThread
            thread instance to register.

        Returns
        -------
        str
            objectName of the registered thread.

        Raises
        ------
        ValueError
            If the given thread objectName already exists in ThreadManager
        """
        if not isinstance(thread, QtCore.QThread):
            raise TypeError(f'Expected thread instance of type {QtCore.QThread}')
        with self._main_lock:
            name = thread.objectName()
            if not name:
                name = self._generate_name()
                thread.setObjectName(name)
            elif name in self._threads:
                raise ValueError(f'Thread with name "{name}" already registered')
            self._register_thread(name, thread)
            return name

    def unregister_thread(self, thread: Union[str, QtCore.QThread]) -> None:
        """Remove thread from ThreadManager"""
        with self._main_lock:
            if isinstance(thread, QtCore.QThread):
                thread = thread.objectName()
            if thread in self._threads:
                self._unregister_thread(thread)

    def quit_thread(self, name: str) -> None:
        """Signal stop of thread event loop.

        Parameters
        ----------
        name : str
            name of thread to quit.

        Raises
        ------
        ValueError
            If the given thread objectName does not exist in ThreadManager
        """
        with self._join_lock:
            thread = self.get_thread_by_name(name)
            self._quit_thread(thread)

    def join_thread(self, name: str, timeout: Optional[Union[int, float]] = None) -> None:
        """Wait for stop of QThread event loop and unregister afterward

        Parameters
        ----------
        name : str
            name of thread to join.

        timeout : float, optional
            timeout duration in seconds (default will never time out).

        Raises
        ------
        ValueError
            If the given thread objectName does not exist in ThreadManager.

        TimeoutError
            If the joining times out.
        """
        with self._join_lock:
            thread = self.get_thread_by_name(name)
            self._join_thread(thread, timeout)
            with self._main_lock:
                self._unregister_thread(name)

    def get_thread_by_name(self, name: str) -> QtCore.QThread:
        """Get registered QThread instance by its name.

        Parameters
        ----------
        name : str
            name of thread to get.

        Returns
        -------
        QtCore.QThread
            registered thread instance.

        Raises
        ------
        ValueError
            If the given thread objectName does not exist in ThreadManager.
        """
        thread = self._threads.get(name, None)
        if thread is None:
            raise ValueError(f'No thread with name "{name}" registered')
        return thread

    def _generate_name(self) -> str:
        """Get a unique generic name for a thread"""
        while True:
            self._gen_name_counter += 1
            name = f'qudi-thread-{self._gen_name_counter:d}'
            if name not in self._threads:
                break
        return name

    def _register_thread(self, name: str, thread: QtCore.QThread) -> None:
        self._threads[name] = thread
        logger.debug(f'Registered thread: "{name}"')
        self.sigThreadRegistered.emit(name)

    def _unregister_thread(self, name: str) -> None:
        if self._threads.pop(name).isRunning():
            logger.warning(f'Removing running thread: "{name}"')
        logger.debug(f'Unregistered thread: "{name}"')
        self.sigThreadUnregistered.emit(name)


class ThreadManagerListModel(QtCore.QAbstractListModel):
    """
    QAbstractListModel implementation to use with the ThreadManager singleton.

    Parameters
    ----------
    thread_manager : ThreadManager
        The thread manager singleton to use as data source.
    parent : QtCore.QObject, optional
        Parent QObject passed on to QtCore.QObject.__init__ (defaults to None).
    """

    def __init__(self, thread_manager: ThreadManager, parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        self._thread_manager = thread_manager
        self._thread_names = self._thread_manager.thread_names.copy()
        self._thread_manager.sigThreadRegistered.connect(self._thread_registered,
                                                         QtCore.Qt.QueuedConnection)
        self._thread_manager.sigThreadUnregistered.connect(self._thread_unregistered,
                                                           QtCore.Qt.QueuedConnection)

    def rowCount(self, parent=None, *args, **kwargs):
        """Gives the number of threads registered.

        Returns
        -------
        int
            Number of threads.
        """
        return len(self._thread_names)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        """Data for the list view header.

        Parameters
        ----------
        section : int
            Column/row index to get header data for.
        orientation : QtCore.Qt.Orientation
            Orientation of header (horizontal or vertical).
        role : QtCore.ItemDataRole
            Data access role.

        Returns
        -------
        str
            Header data for the given column/row and role.
        """
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal and section == 0:
            return 'Thread Name'
        return None

    def data(self, index, role):
        """Get data from model for a given cell. Data can have a role that affects display.

        Parameters
        ----------
        index : QtCore.QModelIndex
            Cell for which data is requested.
        role : QtCore.Qt.ItemDataRole
            Data access role of the request.

        Returns
        -------
        QVariant
            Data for the given cell and role.
        """
        if index.isValid() and role == QtCore.Qt.DisplayRole and index.column() == 0:
            try:
                return self._thread_names[index.row()]
            except IndexError:
                pass
        return None

    def flags(self, index):
        """Determines what can be done with entry cells in the table view.

        Parameters
        ----------
        index : QModelIndex
            Cell for which the flags are requested.

        Returns
        -------
        Qt.ItemFlags
            Actions allowed for this cell.
        """
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def _thread_registered(self, name: str) -> None:
        row = len(self._thread_names)
        self.beginInsertRows(QtCore.QModelIndex(), row, row)
        self._thread_names.append(name)
        self.endInsertRows()

    def _thread_unregistered(self, name: str) -> None:
        try:
            row = self._thread_names.index(name)
        except ValueError:
            pass
        else:
            self.beginRemoveRows(QtCore.QModelIndex(), row, row)
            del self._thread_names[row]
            self.endRemoveRows()
