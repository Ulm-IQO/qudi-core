# -*- coding: utf-8 -*-
"""
Definition of various metaclasses

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

__all__ = ['ABCQObjectMeta', 'QObjectMeta', 'QudiObjectMeta', 'ABCQObject', 'QudiObject']

import copy
import logging

from abc import ABCMeta
from uuid import uuid4, UUID
from typing import MutableMapping, Mapping, Optional, Any, final
from PySide2.QtCore import QObject, Signal, Slot, QCoreApplication

from qudi.core.statusvariable import StatusVar
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.logger import get_logger
from qudi.util.yaml import YamlFileHandler
from qudi.util.paths import get_object_appdata_path
from qudi.util.helpers import call_slot_from_native_thread, current_is_native_thread


QObjectMeta = type(QObject)


class ABCQObjectMeta(ABCMeta, QObjectMeta):
    """ Metaclass for abstract QObject subclasses.
    """

    def __new__(mcs, name, bases, attributes):
        cls = super(ABCQObjectMeta, mcs).__new__(mcs, name, bases, attributes)
        # Compute set of abstract method names
        abstracts = {
            attr_name for attr_name, attr in attributes.items() if \
            getattr(attr, '__isabstractmethod__', False)
        }
        for base in bases:
            for attr_name in getattr(base, '__abstractmethods__', set()):
                attr = getattr(cls, attr_name, None)
                if getattr(attr, '__isabstractmethod__', False):
                    abstracts.add(attr_name)
        cls.__abstractmethods__ = frozenset(abstracts)
        return cls


class QudiObjectMeta(ABCQObjectMeta):
    """ General purpose metaclass for abstract QObject subclasses that include qudi meta attributes
    (Connector, StatusVar, ConfigOption).
    Collects all meta attributes in new "_meta" class variable for easier access.
    Also collects QtCore.Signal attribute names for easier maintenance and access.
    """
    def __new__(mcs, name, bases, attributes):
        cls = super().__new__(mcs, name, bases, attributes)

        # Collect qudi module meta attributes (Connector, StatusVar, ConfigOption) and put them
        # in the class variable dict "_meta" for easy bookkeeping and access.
        base_meta = getattr(cls, '_meta', dict())  # extend shallow copy of _meta dicts if existent

        connectors = base_meta.get('connectors', dict()).copy()
        status_vars = base_meta.get('status_variables', dict()).copy()
        config_opt = base_meta.get('config_options', dict()).copy()
        signals = base_meta.get('signals', dict()).copy()
        for attr_name, attr in cls.__dict__.items():
            if isinstance(attr, Connector):
                connectors[attr_name] = attr
            elif isinstance(attr, StatusVar):
                status_vars[attr_name] = attr
            elif isinstance(attr, ConfigOption):
                config_opt[attr_name] = attr
            elif isinstance(attr, Signal):
                signals[attr_name] = attr_name

        cls._meta = {'connectors'      : connectors,
                     'status_variables': status_vars,
                     'config_options'  : config_opt,
                     'signals'         : signals}
        return cls


class ABCQObject(QObject, metaclass=ABCQObjectMeta):
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


class QudiObject(ABCQObject, metaclass=QudiObjectMeta):
    """
    """

    sigAppDataChanged = Signal(bool)  # has_appdata

    def __init__(self,
                 options: Optional[Mapping[str, Any]] = None,
                 connections: Optional[MutableMapping[str, Any]] = None,
                 appdata_nametag: Optional[str] = '',
                 logger_nametag: Optional[str] = '',
                 uuid: Optional[UUID] = None):
        super().__init__()

        # Create unique UUID for this object if needed
        self.__uuid = uuid if isinstance(uuid, UUID) else uuid4()
        # Create logger instance for this object instance
        if logger_nametag:
            logger_name = f'{self.__module__}.{self.__class__.__name__}::{logger_nametag}'
        else:
            logger_name = f'{self.__module__}.{self.__class__.__name__}'
        self.__logger = get_logger(logger_name)
        # Create file handler for AppData of this object instance
        self.__appdata_filehandler = YamlFileHandler(get_object_appdata_path(appdata_nametag))

        # Initialize ConfigOption and Connector meta-attributes (descriptors)
        self.__init_config_options(dict() if options is None else options)
        self.__init_connectors(dict() if connections is None else connections)

    def __eq__(self, other):
        if isinstance(other, QudiObject):
            return self.uuid == other.uuid
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
    def has_appdata(self) -> bool:
        """ Read-only property indicating if this object with the given appdata_nametag has AppData
        stored on mass storage (True) or not (False)
        """
        return self.__appdata_filehandler.exists

    @Slot()
    @final
    def move_to_main_thread(self) -> None:
        """ Method that will move this module into the main thread """
        if current_is_native_thread(self):
            self.moveToThread(QCoreApplication.instance().thread())
        else:
            call_slot_from_native_thread(self, 'move_to_main_thread', blocking=True)

    @final
    def dump_status_variables(self) -> None:
        """ Dumps current values of StatusVar meta-attributes to a file in AppData that is unique
        for each combination of this objects type and the given appdata_nametag.
        Ignores variables that fail to dump either due to exceptions in the respective StatusVar
        representer or any other reason.

        Emits sigAppDataChanged in any case.
        """
        data = dict()
        cls = self.__class__
        for attr_name, var in self._meta['status_variables'].items():
            try:
                data[var.name] = var.represent(self)
            except:
                self.__logger.exception(
                    f'Error while representing status variable "{var.name}" at '
                    f'"{cls.__module__}.{cls.__name__}.{attr_name}". '
                    f'This variable will NOT be saved.'
                )
        try:
            self.__appdata_filehandler.dump(data)
        except Exception as err:
            raise RuntimeError(
                f'Error dumping status variables to file for "{cls.__module__}.{cls.__name__}"'
            ) from err
        finally:
            self.sigAppDataChanged.emit(self.has_appdata)

    @final
    def load_status_variables(self) -> None:
        """ Loads status variables from file (if present) and tries to initialize the instance
        meta-attributes with them. If a variable is not found in AppData or fails to initialize,
        the default initialization is used instead.
        """
        cls = self.__class__
        try:
            data = self.__appdata_filehandler.load(raise_missing=False)
        except Exception as err:
            raise RuntimeError(
                f'Error loading status variables from file for "{cls.__module__}.{cls.__name__}"'
            ) from err
        for attr_name, var in self._meta['status_variables'].items():
            if var.name in data:
                value = data[var.name]
                try:
                    var.construct(self, value)
                except:
                    self.__logger.exception(
                        f'Error while constructing status variable "{var.name}" at '
                        f'"{cls.__module__}.{cls.__name__}.{attr_name}" from value "{value}". '
                        f'Using default initialization instead.'
                    )
                else:
                    continue
            try:
                var.construct(self)
            except Exception as err:
                raise RuntimeError(f'Default initialization of status variable "{var.name}" at '
                                   f'"{cls.__module__}.{cls.__name__}.{attr_name}" failed') from err

    @final
    def clear_status_variables(self) -> None:
        """ Clears the AppStatus of this object with given appdata_nametag (if present).
        Raises no exception if AppData is not found.

        Emits sigAppDataChanged in any case.
        """
        try:
            self.__appdata_filehandler.clear()
        finally:
            self.sigAppDataChanged.emit(self.has_appdata)
