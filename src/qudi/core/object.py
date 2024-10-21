# -*- coding: utf-8 -*-
"""
Definition of base qudi objects

Copyright (c) 2023, the qudi developers. See the AUTHORS.md file at the top-level directory of this
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

__all__ = ['ABCQObjectMixin', 'QudiQObjectMixin', 'QudiObjectFileHandler']

import os
import copy
import logging
from uuid import uuid4, UUID
from typing import MutableMapping, Mapping, Optional, Any, final, Sequence, Union
from PySide2 import QtCore
from PySide2.QtWinExtras import QtWin

from qudi.core import StatusVar
from qudi.core.logger import get_logger
from qudi.core.meta import ABCQObjectMeta, QudiQObjectMeta
from qudi.util.yaml import YamlFileHandler
from qudi.util.helpers import call_slot_from_native_thread, current_is_native_thread
from qudi.util.paths import get_appdata_dir


class QudiObjectFileHandler(YamlFileHandler):
    """Specialization of YamlFileHandler for QudiQObjectMixin types AppData"""
    def __init__(self, cls_name: str, nametag: str):
        super().__init__(
            file_path=os.path.join(get_appdata_dir(), f'status-{cls_name}-{nametag}.yml')
        )


class QudiObjectAppDataHandler(QtCore.QObject):
    """Handles dumping, loading and deletion of StatusVar meta attributes in QudiQObjectMixin"""

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
        """Indicates if an AppData file exists on disc."""
        return self._file_handler.exists

    @QtCore.Slot()
    def dump(self) -> None:
        """Dumps current values of StatusVar meta-attributes to a file in AppData.
        Ignores variables that fail to dump either due to exceptions in the respective StatusVar
        representer or any other reason.
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
        """Loads status variables from file (if present) and tries to initialize the instance
        meta-attributes with them. If a variable is not found in AppData or fails to initialize,
        the default initialization is used instead.
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
        """Clears status variables file (if present)."""
        if current_is_native_thread(self):
            if self._file_handler.exists:
                self._file_handler.clear()
                self.sigAppDataChanged.emit(False)
        else:
            call_slot_from_native_thread(self, 'clear', blocking=True)

    @QtCore.Slot(object)
    def start_periodic_dump(self, interval: Union[int, float]) -> None:
        if current_is_native_thread(self):
            self._periodic_dumper.start(interval)
        else:
            self._sigStartPeriodicDump.emit(interval)

    @QtCore.Slot()
    def stop_periodic_dump(self):
        if current_is_native_thread(self):
            self._periodic_dumper.stop()
        else:
            call_slot_from_native_thread(self, 'stop_periodic_dump', blocking=True)


class QudiObjectPeriodicAppDataDumper(QtCore.QObject):
    """Helper object to facilitate periodic dumping of AppData in qudi QObjects"""
    def __init__(self, handler: QudiObjectAppDataHandler):
        super().__init__(parent=handler)
        self._handler = handler
        self._stop_requested = True
        self._timer = QtCore.QTimer(parent=self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._dump_callback, QtCore.Qt.QueuedConnection)

    @QtCore.Slot(object)
    def start(self, interval: Union[int, float]) -> None:
        if interval <= 0:
            raise ValueError('Dump interval in seconds must be > 0')
        if self._stop_requested and not self._timer.isActive():
            self._stop_requested = False
            self._timer.setInterval(int(round(1000 * interval)))
            self._timer.start()

    @QtCore.Slot()
    def stop(self) -> None:
        self._stop_requested = True
        self._timer.stop()

    def _dump_callback(self) -> None:
        if not self._stop_requested:
            self._handler.dump()
            print('dumped automatically:', self._handler._instance.nametag)
            self._timer.start()


class ABCQObjectMixin(metaclass=ABCQObjectMeta):
    """ Base class for an abstract QObject.
    This is necessary because of a known bug in PySide2(6).
    See: https://bugreports.qt.io/browse/PYSIDE-1434 for more details
    """
    def __new__(cls, *args, **kwargs):
        abstract = getattr(cls, '__abstractmethods__', frozenset())
        if abstract:
            raise TypeError(f'Can\'t instantiate abstract class "{cls.__name__}" '
                            f'with abstract methods {set(abstract)}')
        return super().__new__(cls, *args, **kwargs)


class QudiQObjectMixin(ABCQObjectMixin, metaclass=QudiQObjectMeta):
    """ Mixin for any qudi QObjects that want to employ meta attribute magic,
    i.e. StatusVar, ConfigOption and Connector.

    Use with QObject types only and make sure this mixin comes before QObject in mro!
    """

    def __init__(self,
                 *args,
                 options: Optional[Mapping[str, Any]] = None,
                 connections: Optional[MutableMapping[str, Any]] = None,
                 nametag: Optional[str] = '',
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
        """ Returns the objects logger instance """
        return self.__logger

    @property
    @final
    def uuid(self) -> UUID:
        """ Read-only property returning a unique uuid for this object instance """
        return self.__uuid

    @property
    @final
    def nametag(self) -> str:
        """ Read-only property returning the nametag for this object instance """
        return self.__nametag

    @property
    @final
    def appdata(self) -> QudiObjectAppDataHandler:
        """Handler for AppData of this object"""
        return self.__appdata_handler
