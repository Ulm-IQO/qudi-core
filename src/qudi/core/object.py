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

__all__ = ['ABCQObjectMixin', 'QudiQObjectMixin', 'QudiQObjectFileHandlerFactory']

import os
import copy
import logging
from uuid import uuid4, UUID
from typing import MutableMapping, Mapping, Optional, Any, final, Union, Dict
from PySide2.QtCore import Slot, QCoreApplication

from qudi.core import StatusVar
from qudi.core.logger import get_logger
from qudi.core.meta import ABCQObjectMeta, QudiQObjectMeta
from qudi.util.yaml import YamlFileHandler
from qudi.util.helpers import call_slot_from_native_thread, current_is_native_thread
from qudi.util.paths import get_appdata_dir


class QudiQObjectFileHandlerFactory:
    """ YamlFileHandler factory for QudiQObjectMixin """

    def __init__(self, class_name: str) -> None:
        super().__init__()
        self.class_name: str = class_name

    def __call__(self, nametag: str) -> YamlFileHandler:
        if nametag:
            filename = f'status-{self.class_name}-{nametag}.cfg'
        else:
            filename = f'status-{self.class_name}.cfg'
        return YamlFileHandler(os.path.join(get_appdata_dir(), filename))


class _QudiQObjectAppDataDescriptor:
    """ Descriptor object for AppData handlers of QudiObject classes """

    def __get__(self, instance, owner=None) -> Union[QudiQObjectFileHandlerFactory, YamlFileHandler]:
        if owner is None:
            owner = type(instance)
        if instance is None:
            return QudiQObjectFileHandlerFactory(owner.__name__)
        else:
            return QudiQObjectFileHandlerFactory(owner.__name__)(instance.nametag)

    def __delete__(self, instance):
        raise AttributeError('Can not delete')

    def __set__(self, instance, value):
        raise AttributeError('Read-Only')


class _ThreadedDescriptor:
    """ Read-only class descriptor representing the owners private class attribute <_threaded> value
    """
    def __get__(self, instance, owner) -> bool:
        try:
            return owner._threaded
        except AttributeError:
            return type(instance)._threaded

    def __delete__(self, instance):
        raise AttributeError('Can not delete')

    def __set__(self, instance, value):
        raise AttributeError('Read-Only')


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

    appdata_handler = _QudiQObjectAppDataDescriptor()

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
        """
        appdata = dict()
        for attr_name, status_variable in self._meta['status_variables'].items():
            try:
                appdata[status_variable.name] = status_variable.represent(self)
            except:
                self.log.exception(
                    f'Error while representing status variable "{status_variable.name}" from '
                    f'attribute "{attr_name}". This variable will not be saved.'
                )
        self.__dump_appdata(appdata)

    @final
    def load_status_variables(self) -> None:
        """ Loads status variables from file (if present) and tries to initialize the instance
        meta-attributes with them. If a variable is not found in AppData or fails to initialize,
        the default initialization is used instead.
        """
        appdata = self.__load_appdata()
        for attr_name, status_variable in self._meta['status_variables'].items():
            try:
                self.__construct_status_variable(status_variable, appdata)
            except Exception as err:
                raise RuntimeError(
                    f'Default initialization of status variable "{status_variable.name}" as '
                    f'attribute "{attr_name}" failed'
                ) from err

    def __dump_appdata(self, data: Mapping[str, Any]) -> None:
        try:
            self.appdata_handler.dump(data)
        except:
            object_descr = f' for "{self.nametag}"' if self.nametag else ''
            self.log.exception(
                f'Error dumping status variables to file{object_descr}. Status not saved.'
            )

    def __load_appdata(self) -> Dict[str, Any]:
        try:
            data = self.appdata_handler.load(ignore_missing=True)
        except:
            data = dict()
            object_descr = f' for "{self.nametag}"' if self.nametag else ''
            self.log.exception(
                f'Error loading status variables from disk{object_descr}. '
                f'Falling back to default values.'
            )
        return data

    def __construct_status_variable(self,
                                    status_variable: StatusVar,
                                    appdata: MutableMapping[str, Any]) -> None:
        if status_variable.name in appdata:
            value = appdata.pop(status_variable.name)
            try:
                status_variable.construct(self, value)
            except:
                self.log.exception(
                    f'Error while constructing status variable "{status_variable.name}" from '
                    f'stored value "{value}". Falling back to default value.'
                )
            else:
                status_variable.construct(self)
        else:
            status_variable.construct(self)
