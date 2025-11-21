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

import logging
import weakref
from functools import partial
from PySide6 import QtCore

from qudi.util.mutex import RecursiveMutex
from qudi.core.logger import get_logger

logger = get_logger(__name__)


class ThreadManager(QtCore.QAbstractListModel):
    """This class keeps track of all the QThreads that are needed somewhere.

    Using this class is thread-safe.
    """
    _instance = None
    _lock = RecursiveMutex()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None or cls._instance() is None:
                obj = super().__new__(cls, *args, **kwargs)
                cls._instance = weakref.ref(obj)
                return obj
            raise RuntimeError(
                'Only one ThreadManager instance per process possible (Singleton). Please use '
                'ThreadManager.instance() to get a reference to the already created instance.'
            )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._threads = list()
        self._thread_names = list()

    @classmethod
    def instance(cls):
        with cls._lock:
            if cls._instance is None:
                return None
            return cls._instance()

    @property
    def thread_names(self):
        with self._lock:
            return self._thread_names.copy()

    def get_new_thread(self, name):
        """Create and return a new QThread with objectName <name>.

        Parameters
        ----------
        name : str
            Unique name of the thread.

        Returns
        -------
        QThread
            New thread, or None if creation failed.
        """
        with self._lock:
            logger.debug('Creating thread: "{0}".'.format(name))
            if name in self._thread_names:
                return None
            thread = QtCore.QThread()
            thread.setObjectName(name)
            self.register_thread(thread)
            return thread

    @QtCore.Slot(QtCore.QThread)
    def register_thread(self, thread):
        """Add QThread to ThreadManager.

        Parameters
        ----------
        thread : QtCore.QThread
            Thread to register with a unique objectName.
        """
        with self._lock:
            name = thread.objectName()
            if name in self._thread_names:
                if self.get_thread_by_name(name) is thread:
                    return None
                raise RuntimeError(
                    f'Different thread with name "{name}" already registered in ThreadManager'
                )

            row = len(self._threads)
            self.beginInsertRows(QtCore.QModelIndex(), row, row)
            self._threads.append(thread)
            self._thread_names.append(name)
            thread.finished.connect(
                partial(self.unregister_thread, name=name), QtCore.Qt.ConnectionType.QueuedConnection)
            self.endInsertRows()

    @QtCore.Slot(object)
    def unregister_thread(self, name):
        """Remove thread from ThreadManager.

        Parameters
        ----------
        name : str
            Unique thread name.
        """
        with self._lock:
            if isinstance(name, QtCore.QThread):
                name = name.objectName()
            if name in self._thread_names:
                index = self._thread_names.index(name)
                if self._threads[index].isRunning():
                    self.quit_thread(name)
                    return
                logger.debug('Cleaning up thread {0}.'.format(name))
                self.beginRemoveRows(QtCore.QModelIndex(), index, index)
                del self._threads[index]
                del self._thread_names[index]
                self.endRemoveRows()

    @QtCore.Slot(object)
    def quit_thread(self, name):
        """Stop event loop of QThread.

        Parameters
        ----------
        name : str
            Unique thread name.
        """
        with self._lock:
            if isinstance(name, QtCore.QThread):
                thread = name
            else:
                thread = self.get_thread_by_name(name)
            if thread is None:
                logger.debug('You tried quitting a nonexistent thread {0}.'.format(name))
            else:
                logger.debug('Quitting thread {0}.'.format(name))
                thread.quit()

    @QtCore.Slot(object, int)
    def join_thread(self, name, time=None):
        """Wait for stop of QThread event loop.

        Parameters
        ----------
        name : str
            Unique thread name.
        time : int
            Timeout for waiting in milliseconds.
        """
        with self._lock:
            if isinstance(name, QtCore.QThread):
                thread = name
            else:
                thread = self.get_thread_by_name(name)
            if thread is None:
                logger.debug('You tried waiting for a nonexistent thread {0}.'.format(name))
            else:
                logger.debug('Waiting for thread {0} to end.'.format(name))
                if time is None:
                    thread.wait()
                else:
                    thread.wait(time)

    @QtCore.Slot(int)
    def quit_all_threads(self, thread_timeout=10000):
        """Stop event loop of all QThreads.
        """
        with self._lock:
            logger.debug('Quit all threads.')
            for thread in self._threads:
                thread.quit()
                if not thread.wait(int(thread_timeout)):
                    logger.error('Waiting for thread {0} timed out.'.format(thread.objectName()))

    def get_thread_by_name(self, name):
        """Get registered QThread instance by its objectName.

        Parameters
        ----------
        name : str
            Object name of the QThread to return.

        Returns
        -------
        QThread
            The registered thread object.
        """
        with self._lock:
            try:
                index = self._thread_names.index(name)
                return self._threads[index]
            except ValueError:
                return None

    # QAbstractListModel interface methods follow below
    def rowCount(self, parent=None, *args, **kwargs):
        """Gives the number of threads registered.

        Returns
        -------
        int
            Number of threads.
        """
        with self._lock:
            return len(self._threads)

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
        if role == QtCore.Qt.ItemDataRole.DisplayRole and orientation == QtCore.Qt.Orientation.Horizontal and section == 0:
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
        with self._lock:
            row = index.row()
            if index.isValid() and role == QtCore.Qt.ItemDataRole.DisplayRole and 0 <= row < len(self._threads):
                if index.column() == 0:
                    return self._thread_names[row]
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
        return QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable
