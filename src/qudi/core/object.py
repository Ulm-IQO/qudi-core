# -*- coding: utf-8 -*-
"""
Base implementation and mixins for abstract QObjects employing qudi meta attribute functionality.

Copyright (c) 2023-2024, the qudi developers. See the AUTHORS.md file at the top-level directory of
this distribution and on <https://github.com/Ulm-IQO/qudi-core/>.

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

__all__ = ['QudiQObject', 'ABCQObjectMixin', 'QudiQObjectMixin', 'QudiObjectFileHandler']

import os
import copy
import logging
from uuid import uuid4, UUID
from typing import MutableMapping, Mapping, Optional, Any, final, Sequence, Union
from PySide2 import QtCore

from qudi.core.statusvariable import StatusVar
from qudi.core.logger import get_logger
from qudi.core.meta import ABCQObjectMeta, QudiQObjectMeta
from qudi.util.yaml import YamlFileHandler
from qudi.util.helpers import call_slot_from_native_thread, current_is_native_thread
from qudi.util.paths import get_appdata_dir


class QudiObjectFileHandler(YamlFileHandler):
    """
    Specialization of qudi.util.yaml.YamlFileHandler for QudiQObjectMixin types AppData.

    Parameters
    ----------
    cls_name : str
        Class name of the qudi QObject (QudiQObjectMixin subclass)
    nametag : str
        Unique module name of the qudi object
    """
    def __init__(self, cls_name: str, nametag: str):
        super().__init__(
            file_path=os.path.join(get_appdata_dir(), f'status-{cls_name}-{nametag}.yml')
        )


class QudiObjectAppDataHandler(QtCore.QObject):
    """
    Handles dumping, loading and deletion of StatusVar meta attributes in qudi objects.
    Includes automatic, periodic dumping functionality that can be enabled/disabled at any time.
    All public methods and attributes can be considered thread-safe.

    Parameters
    ----------
    instance : QudiQObjectMixin
        Class name of the qudi QObject (QudiQObjectMixin subclass)
    status_vars : list
        Sequence of qudi.core.statusvariable.StatusVar meta attribute instances associated with the
        qudi object instance.
    """

    sigAppDataChanged = QtCore.Signal(bool)  # exists
    _sigStartPeriodicDump = QtCore.Signal(object)  # interval

    def __init__(self, instance: 'QudiQObjectMixin', status_vars: Sequence[StatusVar]):
        super().__init__(parent=instance)
        self._status_vars = status_vars
        self._instance = instance
        self._file_handler = QudiObjectFileHandler(cls_name=self._instance.__class__.__name__,
                                                   nametag=self._instance.nametag)
        self._periodic_dumper = QudiObjectPeriodicAppDataDumper(handler=self)
        self._sigStartPeriodicDump.connect(self.start_periodic_dump,
                                           QtCore.Qt.BlockingQueuedConnection)

    @property
    def exists(self) -> bool:
        """
        Indicates if an AppData file exists on disc.

        Returns
        -------
        bool
            AppData file exists flag.
        """
        return self._file_handler.exists

    @QtCore.Slot()
    def dump(self) -> None:
        """
        Dumps current values of StatusVar meta-attributes to a file in AppData. Ignores variables
        that fail to dump either due to exceptions in the respective StatusVar representer or any
        other reason.
        Can be considered thread-safe.
        """
        if current_is_native_thread(self):
            appdata = dict()
            for status_variable in self._status_vars:
                try:
                    appdata[status_variable.name] = status_variable.represent(self._instance)
                except:
                    self._instance.log.exception(
                        f'Error while representing status variable "{status_variable.name}". '
                        f'This variable will not be saved.'
                    )
            try:
                self._file_handler.dump(appdata)
                self.sigAppDataChanged.emit(True)
            except:
                self.log.exception('Error dumping status variables to file. Status not saved.')
        else:
            call_slot_from_native_thread(self, 'dump', blocking=True)

    @QtCore.Slot()
    def load(self) -> None:
        """
        Loads status variables from file (if present) and tries to initialize the instance
        meta-attributes with them. If a variable is not found in AppData or fails to initialize,
        the default initialization is used instead.
        Can be considered thread-safe.
        """
        if current_is_native_thread(self):
            appdata = self._file_handler.load(ignore_missing=True)
            for status_variable in self._status_vars:
                try:
                    if status_variable.name in appdata:
                        value = appdata[status_variable.name]
                        try:
                            status_variable.construct(self._instance, value)
                        except:
                            self.log.exception(
                                f'Error while constructing status variable "{status_variable.name}"'
                                f' from stored value "{value}". Falling back to default value.'
                            )
                            status_variable.construct(self._instance)
                    else:
                        status_variable.construct(self._instance)
                except Exception as err:
                    raise RuntimeError(
                        f'Default initialization of status variable "{status_variable.name}" failed'
                    ) from err
        else:
            call_slot_from_native_thread(self, 'load', blocking=True)

    @QtCore.Slot()
    def clear(self) -> None:
        """
        Clears status variables file (if present).
        Can be considered thread-safe.
        """
        if current_is_native_thread(self):
            if self._file_handler.exists:
                self._file_handler.clear()
                self.sigAppDataChanged.emit(False)
        else:
            call_slot_from_native_thread(self, 'clear', blocking=True)

    @QtCore.Slot(object)
    def start_periodic_dump(self, interval: Union[int, float]) -> None:
        """
        Start automatic, periodic dumping of status variables.
        Can be considered thread-safe.

        Parameters
        ----------
        interval : float
            Interval in seconds for dumping. Does not include the execution time of the dump call.
        """
        if current_is_native_thread(self):
            self._periodic_dumper.start(interval)
        else:
            self._sigStartPeriodicDump.emit(interval)

    @QtCore.Slot()
    def stop_periodic_dump(self):
        """
        Stop automatic, periodic dumping of status variables. Ignored if no timer is running.
        Can be considered thread-safe.
        """
        if current_is_native_thread(self):
            self._periodic_dumper.stop()
        else:
            call_slot_from_native_thread(self, 'stop_periodic_dump', blocking=True)


class QudiObjectPeriodicAppDataDumper(QtCore.QObject):
    """
    Helper object to facilitate periodic dumping of AppData in qudi QObjects.

    Parameters
    ----------
    handler : QudiObjectAppDataHandler
        Parent AppData handler instance.
    """
    def __init__(self, handler: QudiObjectAppDataHandler):
        super().__init__(parent=handler)
        self._handler = handler
        self._stop_requested = True
        self._timer = QtCore.QTimer(parent=self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._dump_callback, QtCore.Qt.QueuedConnection)

    @QtCore.Slot(object)
    def start(self, interval: Union[int, float]) -> None:
        """
        Start automatic, periodic dumping of AppData.

        Parameters
        ----------
        interval : float
            Interval in seconds for dumping. Does not include the execution time of the dump call.

        Raises
        ------
        ValueError
            If the dump interval is <= 0.
        """
        if interval <= 0:
            raise ValueError('Dump interval in seconds must be > 0')
        if self._stop_requested and not self._timer.isActive():
            self._stop_requested = False
            self._timer.setInterval(int(round(1000 * interval)))
            self._timer.start()

    @QtCore.Slot()
    def stop(self) -> None:
        """
        Stop automatic, periodic dumping of AppData. Ignored if no timer is running.
        """
        self._stop_requested = True
        self._timer.stop()

    def _dump_callback(self) -> None:
        """Body of the timed loop."""
        if not self._stop_requested:
            self._handler.dump()
            self._timer.start()


class ABCQObjectMixin(metaclass=ABCQObjectMeta):
    """
    Base class for an abstract QObject. This is necessary because of a known bug in PySide2(6).
    See https://bugreports.qt.io/browse/PYSIDE-1434 for more details
    """
    def __new__(cls, *args, **kwargs):
        abstract = getattr(cls, '__abstractmethods__', frozenset())
        if abstract:
            raise TypeError(f'Can\'t instantiate abstract class "{cls.__name__}" '
                            f'with abstract methods {set(abstract)}')
        return super().__new__(cls, *args, **kwargs)


class QudiQObjectMixin(ABCQObjectMixin, metaclass=QudiQObjectMeta):
    """
    Mixin for any qudi QObject that wants to employ meta attribute magic, i.e. StatusVar,
    ConfigOption and Connector.
    Also adds logging.Logger, nametag and UUID attributes and ABC metaclass functionality.

    Use with QObject/QWidget types only and make sure this is placed before QObject/QWidget in mro!

    Parameters
    ----------
    nametag : str, optional
        Human-readable string identifier for the object instance (defaults to empty string).
    options : dict, optional
        name-value pairs to initialize ConfigOption meta attributes with. Must provide at least as
        many items as there are mandatory ConfigOption attributes in the qudi object.
    connections : dict, optional
        name-value pairs to initialize Connector meta attributes with. Must provide at least as
        many items as there are mandatory Connector attributes in the qudi object.
    uuid : uuid.UUID, optional
        Universal unique identifier object for this object instance (defaults to creating one
        with uuid.uuid4 if not provided).
    *args
        Positional arguments will be passed down the MRO (possibly to QObject)
    **kwargs
        Additional keyword arguments will be passed down the MRO (possibly to QObject)
    """
    def __init__(self,
                 *args,
                 nametag: Optional[str] = '',
                 options: Optional[Mapping[str, Any]] = None,
                 connections: Optional[MutableMapping[str, Any]] = None,
                 uuid: Optional[UUID] = None,
                 **kwargs):
        # Create unique UUID for this object if needed
        self.__uuid: UUID = uuid if isinstance(uuid, UUID) else uuid4()
        self.__nametag: str = nametag
        # Create logger instance for this object instance
        if nametag:
            logger_name = f'{self.__module__}.{self.__class__.__name__}::{nametag}'
        else:
            logger_name = f'{self.__module__}.{self.__class__.__name__}'
        self.__logger = get_logger(logger_name)

        super().__init__(*args, **kwargs)

        # Initialize ConfigOption and Connector meta-attributes (descriptors)
        self.__init_config_options(dict() if options is None else options)
        self.__init_connectors(dict() if connections is None else connections)
        # Initialize AppData handler
        self.__appdata_handler = QudiObjectAppDataHandler(
            instance=self,
            status_vars=list(self._meta['status_variables'].values())
        )


    def __eq__(self, other):
        if isinstance(other, QudiQObjectMixin):
            return self.__uuid == other.uuid
        return False

    def __hash__(self):
        return self.__uuid.int

    def __init_config_options(self, option_values: Optional[Mapping[str, Any]]) -> None:
        for attr_name, cfg_opt in self._meta['config_options'].items():
            if cfg_opt.name in option_values:
                cfg_opt.construct(self, copy.deepcopy(option_values[cfg_opt.name]))
            else:
                cfg_opt.construct(self)

    def __init_connectors(self, connections: MutableMapping[str, Any]) -> None:
        """ Connects given modules (values) to their respective Connector (keys). """
        # Iterate through all connectors and try to connect them to targets
        for connector in self._meta['connectors'].values():
            connector.connect(self, connections.pop(connector.name, None))
        # Warn if too many connections have been configured
        if len(connections) > 0:
            self.log.warning(
                f'Configuration contains additional connectors that are ignored. Please remove '
                f'the following connections from the configuration: {list(connections)}'
            )

    @property
    @final
    def log(self) -> logging.Logger:
        """Logger of this object instance."""
        return self.__logger

    @property
    @final
    def uuid(self) -> UUID:
        """Unique uuid of this object instance."""
        return self.__uuid

    @property
    @final
    def nametag(self) -> str:
        """Nametag of this object instance."""
        return self.__nametag

    @property
    @final
    def appdata(self) -> QudiObjectAppDataHandler:
        """Handler for AppData of this object instance."""
        return self.__appdata_handler


class QudiQObject(QudiQObjectMixin, QtCore.QObject):
    """Expands QObject class with qudi meta attribute magic, i.e. StatusVar, ConfigOption and
    Connector.
    Also adds logging.Logger, nametag and UUID attributes and ABC metaclass functionality.

    Use with QObject/QWidget types only and make sure this is placed before QObject/QWidget in mro!

    Parameters
    ----------
    parent : QtCore.QObject, optional
        Parent QObject passed on to QtCore.QObject.__init__ (defaults to None).
    nametag : str, optional
        Human-readable string identifier for the object instance (defaults to empty string).
    options : dict, optional
        name-value pairs to initialize ConfigOption meta attributes with. Must provide at least as
        many items as there are mandatory ConfigOption attributes in the qudi object.
    connections : dict, optional
        name-value pairs to initialize Connector meta attributes with. Must provide at least as
        many items as there are mandatory Connector attributes in the qudi object.
    uuid : uuid.UUID, optional
        Universal unique identifier object for this object instance (defaults to creating one
        with uuid.uuid4 if not provided).
    """
    def __init__(self,
                 parent: Optional[QtCore.QObject] = None,
                 nametag: Optional[str] = '',
                 options: Optional[Mapping[str, Any]] = None,
                 connections: Optional[MutableMapping[str, Any]] = None,
                 uuid: Optional[UUID] = None):
        super().__init__(parent=parent,
                         nametag=nametag,
                         options=options,
                         connections=connections,
                         uuid=uuid)
