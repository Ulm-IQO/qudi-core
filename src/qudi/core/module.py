# -*- coding: utf-8 -*-
"""
This file contains the Qudi module base class.

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
import os
import copy
import uuid
from enum import Enum
from abc import abstractmethod
from uuid import uuid4
from fysom import Fysom, FysomError
from PySide2 import QtCore, QtGui, QtWidgets
from typing import Any, Mapping, MutableMapping, Optional, Union, Dict, Callable

from qudi.core.configoption import MissingAction
from qudi.core.statusvariable import StatusVar
from qudi.core.connector import ModuleConnectionError, Connector
from qudi.util.paths import get_module_app_data_path, get_daily_directory, get_default_data_dir
from qudi.util.yaml import yaml_load, yaml_dump, YamlFileHandler
from qudi.util.helpers import call_slot_from_native_thread
from qudi.core.meta import QudiObject
from qudi.core.logger import get_logger


class ModuleStateError(RuntimeError):
    pass


class ModuleState(Enum):
    DEACTIVATED = 'deactivated'
    IDLE = 'idle'
    LOCKED = 'locked'


class ModuleBase(Enum):
    HARDWARE = 'hardware'
    LOGIC = 'logic'
    GUI = 'gui'


class Base(QudiObject):
    """ Base class for all loadable modules

    * Ensure that the program will not die during the load of modules
    * Initialize modules
    * Provides a self identification of the used module
    * per-module logging facility
    * Provides a self de-initialization of the used module
    * Get your own configuration (for save)
    * Get name of status variables
    * Get status variables
    * Reload module data (from saved variables)
    """
    _threaded = False

    @classmethod
    def module_threaded(cls) -> bool:
        """ Returns whether the module shall be started in its own thread """
        return cls._threaded

    @classmethod
    def module_base(cls) -> ModuleBase:
        if issubclass(cls, GuiBase):
            return ModuleBase.GUI
        if issubclass(cls, LogicBase):
            return ModuleBase.LOGIC
        return ModuleBase.HARDWARE

    def __init__(self,
                 qudi_main: Any,
                 name: str,
                 options: Optional[Mapping[str, Any]] = None,
                 connections: Optional[MutableMapping[str, Any]] = None,
                 **kwargs):
        """ Initialize Base instance. Set up its state machine, initializes ConfigOption meta
        attributes from given config and connects activated module dependencies.

        @param object self: the object being initialized
        @param str name: unique name for this module instance
        @param dict configuration: parameters from the configuration file
        @param dict callbacks: dict specifying functions to be run on state machine transitions
        """
        super().__init__(**kwargs)

        if options is None:
            options = dict()
        if connections is None:
            connections = dict()

        # Keep weak reference to qudi main instance
        self.__qudi_main = qudi_main

        # Create logger instance for module
        self.__logger = get_logger(f'{self.__module__}.{self.__class__.__name__}::{name}')

        # Add additional module info
        self.__module_name = name
        self.__module_uuid = uuid4()

        # set instance attributes according to ConfigOption meta-objects
        self.__init_config_options(options)
        # connect other modules according to Connector meta-objects
        self.__init_connectors(connections)

        # Initialize module state
        self.module_state = ModuleStateControl(module_instance=self,
                                               status_variables=self._meta['status_variables'],
                                               connectors=self._meta['connectors'])

    def __init_config_options(self, option_values: Optional[Mapping[str, Any]]) -> None:
        for attr_name, cfg_opt in self._meta['config_options'].items():
            try:
                value = option_values[cfg_opt.name]
            except KeyError:
                if not cfg_opt.optional:
                    raise ValueError(
                        f'Required ConfigOption "{cfg_opt.name}" not given in module configuration '
                        f'options:\n{option_values}'
                    )
                cfg_opt.construct(self)
                msg = f'No ConfigOption "{cfg_opt.name}" configured, using default value ' \
                      f'"{cfg_opt.default}" instead.'
                if cfg_opt.missing_action == MissingAction.WARN:
                    self.log.warning(msg)
                elif cfg_opt.missing_action == MissingAction.INFO:
                    self.log.info(msg)
            else:
                cfg_opt.construct(self, copy.deepcopy(value))

    def __init_connectors(self, connections: MutableMapping[str, Any]) -> None:
        """ Connects given modules (values) to their respective Connector (keys). """
        try:
            # Iterate through all module connectors and try to connect them to targets
            for connector in self._meta['connectors'].values():
                target = connections.pop(connector.name, None)
                if target is None:
                    if not connector.optional:
                        raise ModuleConnectionError(
                            f'Mandatory module connector "{connector.name}" not configured.'
                        )
                else:
                    connector.connect(self, target)
        except Exception:
            self.__disconnect_modules()
            raise

        # Warn if too many connections have been configured
        if connections:
            self.log.warning(
                f'Module config contains additional connectors that are ignored. Please remove '
                f'the following connections from the configuration: {list(connections)}'
            )

    def __eq__(self, other):
        if isinstance(other, Base):
            return self.module_uuid == other.module_uuid
        return super().__eq__(other)

    def __hash__(self):
        return self.module_uuid.int

    @QtCore.Slot()
    def move_to_main_thread(self) -> None:
        """ Method that will move this module into the main/manager thread.
        """
        if call_slot_from_native_thread(self, 'move_to_main_thread', blocking=True):
            self.moveToThread(QtCore.QCoreApplication.instance().thread())

    @property
    def module_name(self) -> str:
        """ Read-only property returning the module name of this module instance as specified in the
        config.
        """
        return self.__module_name

    @property
    def module_uuid(self) -> uuid.UUID:
        """ Read-only property returning a unique uuid for this module instance.
        """
        return self.__module_uuid

    @property
    def module_default_data_dir(self) -> str:
        """ Read-only property returning the generic default directory in which to save data.
        Module implementations can overwrite this property with a custom path but should only do so
        with a very good reason.
        """
        config = self._qudi_main.configuration
        data_root = config['default_data_dir']
        if data_root is None:
            data_root = get_default_data_dir()
        if config['daily_data_dirs']:
            data_dir = os.path.join(get_daily_directory(root=data_root), self.module_name)
        else:
            data_dir = os.path.join(data_root, self.module_name)
        return data_dir

    @property
    def _qudi_main(self) -> Any:
        return self.__qudi_main

    @property
    def log(self) -> logging.Logger:
        """ Returns the module logger instance
        """
        return self.__logger

    def _send_balloon_message(self, title: str, message: str, time: Optional[float] = None,
                              icon: Optional[QtGui.QIcon] = None) -> None:
        if self._qudi_main.gui is None:
            log = get_logger('balloon-message')
            log.warning(f'{title}:\n{message}')
            return
        self._qudi_main.gui.balloon_message(title, message, time, icon)

    def _send_pop_up_message(self, title: str, message: str):
        if self._qudi_main.gui is None:
            log = get_logger('pop-up-message')
            log.warning(f'{title}:\n{message}')
            return
        self._qudi_main.gui.pop_up_message(title, message)

    @abstractmethod
    def on_activate(self) -> None:
        """ Method called when module is activated. Must be implemented by actual qudi module.
        """
        raise NotImplementedError('Please implement and specify the activation method.')

    @abstractmethod
    def on_deactivate(self) -> None:
        """ Method called when module is deactivated. Must be implemented by actual qudi module.
        """
        raise NotImplementedError('Please implement and specify the deactivation method.')


class LogicBase(Base):
    """
    """
    _threaded = True


class GuiBase(Base):
    """This is the GUI base class. It provides functions that every GUI module should have.
    """
    _threaded = False
    __window_geometry = StatusVar(name='_GuiBase__window_geometry', default=None)
    __window_state = StatusVar(name='_GuiBase__window_state', default=None)

    @abstractmethod
    def show(self) -> None:
        raise NotImplementedError('Every GUI module needs to implement the show() method!')

    def _save_window_geometry(self, window: QtWidgets.QMainWindow) -> None:
        try:
            self.__window_geometry = window.saveGeometry().toHex().data().decode('utf-8')
        except:
            self.log.exception('Unable to save window geometry:')
            self.__window_geometry = None
        try:
            self.__window_state = window.saveState().toHex().data().decode('utf-8')
        except:
            self.log.exception('Unable to save window geometry:')
            self.__window_state = None

    def _restore_window_geometry(self, window: QtWidgets.QMainWindow) -> bool:
        if isinstance(self.__window_geometry, str):
            try:
                encoded = QtCore.QByteArray(self.__window_geometry.encode('utf-8'))
                window.restoreGeometry(QtCore.QByteArray.fromHex(encoded))
            except:
                self.log.exception('Unable to restore window geometry:')
        if isinstance(self.__window_state, str):
            try:
                encoded = QtCore.QByteArray(self.__window_state.encode('utf-8'))
                return window.restoreState(QtCore.QByteArray.fromHex(encoded))
            except:
                self.log.exception('Unable to restore window state:')
        return False


class ModuleStateFileHandler(YamlFileHandler):
    """ Helper object to facilitate file handling for module app status files
    """
    def __init__(self, module_base: Union[str, ModuleBase], class_name: str, module_name: str):
        module_base = ModuleBase(module_base)
        super().__init__(get_module_app_data_path(class_name, module_base.value, module_name))


class ModuleStateMachine(Fysom):
    """
    FIXME
    """
    def __init__(self, callbacks=None, **kwargs):
        if callbacks is None:
            callbacks = dict()

        # State machine definition. The abbreviations for the event list are the following:
        #   name:   event name,
        #   src:    source state,
        #   dst:    destination state
        fsm_cfg = {'initial': 'deactivated',
                   'events': [{'name': 'activate', 'src': 'deactivated', 'dst': 'idle'},
                              {'name': 'deactivate', 'src': 'idle', 'dst': 'deactivated'},
                              {'name': 'deactivate', 'src': 'locked', 'dst': 'deactivated'},
                              {'name': 'lock', 'src': 'idle', 'dst': 'locked'},
                              {'name': 'unlock', 'src': 'locked', 'dst': 'idle'}],
                   'callbacks': callbacks}

        # Initialise state machine:
        super().__init__(cfg=fsm_cfg, **kwargs)


class ModuleStateControl(QtCore.QObject):
    """ Handler class to control qudi module state transitions and appstatus """

    sigStateChanged = QtCore.Signal(object)

    def __init__(self,
                 module_instance: Base,
                 status_variables: Mapping[str, StatusVar],
                 connectors: Mapping[str, Connector]):
        if not isinstance(module_instance, Base):
            raise TypeError('Parameter "module_instance" of ModuleStateControl.__init__ '
                            'expects qudi.core.module.Base instance.')
        if not all(isinstance(name, str) and isinstance(var, StatusVar) for name, var in
                   status_variables.items()):
            raise TypeError('Parameter "status_variables" of ModuleStateControl.__init__ must be '
                            'mapping with str keys and StatusVar values.')
        if not all(isinstance(name, str) and isinstance(conn, Connector) for name, conn in
                   connectors.items()):
            raise TypeError('Parameter "connectors" of ModuleStateControl.__init__ must be '
                            'mapping with str keys and Connector values.')
        super().__init__(parent=module_instance)
        self._status_variables = status_variables
        self._connectors = connectors
        self._appdata_filehandler = ModuleStateFileHandler(
            module_base=module_instance.module_base(),
            class_name=module_instance.__class__.__name__,
            module_name=module_instance.module_name
        )
        self._fsm = ModuleStateMachine(
            callbacks={'on_before_activate'  : self.__activation_callback,
                       'on_before_deactivate': self.__deactivation_callback})
        self._fsm.on_change_state = self._state_change_callback

    @property
    def current(self) -> ModuleState:
        return ModuleState(self._fsm.current)

    def __call__(self) -> str:
        return self.current.value

    def _state_change_callback(self, event) -> None:
        self.sigStateChanged.emit(ModuleState(event.dst))

    @QtCore.Slot()
    def activate(self) -> None:
        try:
            self._fsm.activate()
        except Exception as err:
            raise ModuleStateError('Module activation failed') from err

    @QtCore.Slot()
    def deactivate(self) -> None:
        try:
            self._fsm.deactivate()
        except Exception as err:
            raise ModuleStateError('Module deactivation failed') from err

    @QtCore.Slot()
    def lock(self) -> None:
        try:
            self._fsm.lock()
        except Exception as err:
            raise ModuleStateError('Module locking failed') from err

    @QtCore.Slot()
    def unlock(self) -> None:
        try:
            self._fsm.unlock()
        except Exception as err:
            raise ModuleStateError('Module unlocking failed') from err

    @property
    def has_appdata(self) -> bool:
        return self._appdata_filehandler.exists

    @QtCore.Slot()
    def clear_appdata(self) -> None:
        self._appdata_filehandler.clear()

    @QtCore.Slot()
    def dump_appdata(self) -> None:
        module = self.parent()
        data = dict()
        for var in self._status_variables.values():
            try:
                data[var.name] = var.represent(module)
            except Exception as err:
                raise ModuleStateError(
                    f'Error while representing status variable "{var.name}"'
                ) from err
        try:
            self._appdata_filehandler.dump(data)
        except Exception as err:
            raise ModuleStateError(f'Error while dumping status variables to file') from err

    @QtCore.Slot()
    def load_appdata(self) -> None:
        module = self.parent()
        try:
            data = self._appdata_filehandler.load(raise_missing=False)
        except Exception as err:
            raise ModuleStateError(f'Error while loading status variables for module '
                                   f'"{module.module_name}" from file') from err

        for var in self._status_variables.values():
            try:
                try:
                    value = data[var.name]
                except KeyError:
                    var.construct(module)
                else:
                    var.construct(module, value)
            except Exception as err:
                raise ModuleStateError(f'Error while constructing status variable "{var.name}" for '
                                       f'module"{module.module_name}"') from err

    def __disconnect_modules(self) -> None:
        """ Disconnects all Connector instances for this module. """
        module = self.parent()
        for connector in self._connectors.values():
            connector.disconnect(module)

    def __activation_callback(self, event=None) -> bool:
        """ Restore status variables before activation and invoke on_activate method.
        """
        module = self.parent()
        try:
            self.load_appdata()
            module.on_activate()
        except Exception:
            module.log.exception('Exception during activation:')
            raise
        return True

    def __deactivation_callback(self, event=None) -> bool:
        """ Invoke on_deactivate method and save status variables afterwards even if deactivation
        fails.
        """
        module = self.parent()
        try:
            try:
                module.on_deactivate()
            finally:
                # save status variables even if deactivation failed
                try:
                    self.dump_appdata()
                finally:
                    # self.__disconnect_modules()
                    pass
        except Exception:
            module.log.exception('Exception during deactivation:')
        return True
