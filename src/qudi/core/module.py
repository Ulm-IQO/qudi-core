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

__all__ = ['ModuleState', 'ModuleBase', 'ModuleStateError', 'Base', 'LogicBase', 'GuiBase']

import logging
import os
import copy
import uuid
import warnings
from enum import Enum
from abc import abstractmethod
from uuid import uuid4
from fysom import Fysom
from PySide2 import QtCore, QtGui, QtWidgets
from typing import Any, Mapping, MutableMapping, Optional, Union, Callable, final

from qudi.core.configoption import MissingAction
from qudi.core.statusvariable import StatusVar
from qudi.core.connector import ModuleConnectionError
from qudi.util.paths import get_module_app_data_path, get_daily_directory, get_default_data_dir
from qudi.util.yaml import YamlFileHandler
from qudi.util.helpers import call_slot_from_native_thread, current_is_native_thread
from qudi.core.meta import QudiObject
from qudi.core.logger import get_logger


class ModuleStateError(RuntimeError):
    pass


class ModuleState(Enum):
    DEACTIVATED = 'deactivated'
    IDLE = 'idle'
    LOCKED = 'locked'

    def __call__(self) -> str:
        """ For backwards compatibility """
        if not hasattr(self.__class__, '__warning_sent__'):
            warnings.warn(
                'Being able to call ModuleState Enum to get a string representation is deprecated '
                'and will be removed in the future. Please use ModuleState directly or use '
                'ModuleState.value if you must have the string representation (not recommended).',
                DeprecationWarning,
                stacklevel=2
            )
            self.__class__.__warning_sent__ = True
        return self.value


class ModuleBase(Enum):
    HARDWARE = 'hardware'
    LOGIC = 'logic'
    GUI = 'gui'


class ThreadedDescriptor:
    def __get__(self, instance, owner):
        if owner is None:
            owner = type(instance)
        return owner._threaded

    def __delete__(self, instance):
        raise AttributeError('Can not delete')

    def __set__(self, instance, value):
        raise AttributeError('Read-Only')


class ModuleBaseDescriptor:
    def __get__(self, instance, owner):
        if owner is None:
            owner = type(instance)
        if issubclass(owner, GuiBase):
            return ModuleBase.GUI
        if issubclass(owner, LogicBase):
            return ModuleBase.LOGIC
        return ModuleBase.HARDWARE

    def __delete__(self, instance):
        raise AttributeError('Can not delete')

    def __set__(self, instance, value):
        raise AttributeError('Read-Only')


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
    module_threaded = ThreadedDescriptor()
    module_base = ModuleBaseDescriptor()

    sigModuleStateChanged = QtCore.Signal(ModuleState)
    sigModuleAppDataChanged = QtCore.Signal(bool)  # has_appdata

    def __init__(self,
                 qudi_main: Any,
                 name: str,
                 options: Optional[Mapping[str, Any]] = None,
                 connections: Optional[MutableMapping[str, Any]] = None):
        """ Initialize Base instance. Set up its state machine, initializes ConfigOption meta
        attributes from given config and connects activated module dependencies.

        @param object self: the object being initialized
        @param str name: unique name for this module instance
        @param dict configuration: parameters from the configuration file
        @param dict callbacks: dict specifying functions to be run on state machine transitions
        """
        super().__init__()

        if options is None:
            options = dict()
        if connections is None:
            connections = dict()

        # Keep reference to qudi main instance
        self.__qudi_main = qudi_main
        # Add additional module info
        self.__module_name = name
        self.__module_uuid = uuid4()  # unique module identifier
        # Create logger instance for module
        self.__logger = get_logger(f'{self.__module__}.{self.__class__.__name__}::{name}')
        # Create file handler for module AppData
        self.__appdata_filehandler = ModuleStateFileHandler(self.module_name,
                                                            self.module_base,
                                                            self.__class__.__name__)

        # Initialize ConfigOption and Connector meta-attributes (descriptors)
        self.__init_config_options(options)
        self.__init_connectors(connections)

        # Initialize module state
        self.module_state_control = ModuleStateControl(
            module_instance=self,
            activation_callback=self.__activation_callback,
            deactivation_callback=self.__deactivation_callback,
            state_change_callback=self.__state_change_callback
        )

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

        # Warn if too many connections have been configured
        if connections:
            self.log.warning(
                f'Module config contains additional connectors that are ignored. Please remove '
                f'the following connections from the configuration: {list(connections)}'
            )

    def __clear_connectors(self) -> None:
        for connector in self._meta['connectors'].values():
            connector.disconnect(self)

    def __eq__(self, other):
        if isinstance(other, Base):
            return self.module_uuid.int == other.module_uuid.int
        return False

    def __hash__(self):
        return self.module_uuid.int

    @property
    @final
    def _qudi_main(self) -> Any:
        return self.__qudi_main

    @property
    @final
    def module_state(self):
        return self.module_state_control.state

    @property
    @final
    def module_name(self) -> str:
        """ Read-only property returning the module name of this module instance as specified in the
        config.
        """
        return self.__module_name

    @property
    @final
    def module_uuid(self) -> uuid.UUID:
        """ Read-only property returning a unique uuid for this module instance.
        """
        return self.__module_uuid

    @property
    def module_has_appdata(self) -> bool:
        """ Read-only property indicating if the module has AppData stored on disk (True) or not
        (False)
        """
        return self.__appdata_filehandler.exists

    @property
    def log(self) -> logging.Logger:
        """ Returns the module logger instance
        """
        return self.__logger

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

    @final
    @QtCore.Slot()
    def move_to_main_thread(self) -> None:
        """ Method that will move this module into the main/manager thread.
        """
        if current_is_native_thread(self):
            self.moveToThread(QtCore.QCoreApplication.instance().thread())
        else:
            call_slot_from_native_thread(self, 'move_to_main_thread', blocking=True)

    @final
    def _lock_module(self) -> None:
        self.module_state_control.lock()

    @final
    def _unlock_module(self) -> None:
        self.module_state_control.unlock()

    @final
    def _dump_status_variables(self) -> None:
        data = dict()
        for attr_name, var in self._meta['status_variables'].items():
            try:
                data[var.name] = var.represent(self)
            except Exception:
                self.log.exception(
                    f'Error while representing status variable "{var.name}" from '
                    f'"{self.__class__.__name__}.{attr_name}". This variable will not be saved.'
                )
        try:
            self.__appdata_filehandler.dump(data)
        except Exception as err:
            raise ModuleStateError(f'Error while dumping status variables to file') from err
        finally:
            self.sigModuleAppDataChanged.emit(self.module_has_appdata)

    @final
    def _load_status_variables(self) -> None:
        try:
            data = self.__appdata_filehandler.load(raise_missing=False)
        except Exception as err:
            raise ModuleStateError(f'Error while loading status variables for module '
                                   f'"{self.module_name}" from file') from err
        for attr_name, var in self._meta['status_variables'].items():
            if var.name in data:
                value = data[var.name]
                try:
                    var.construct(self, value)
                except Exception:
                    self.log.exception(
                        f'Error while constructing status variable "{var.name}" to '
                        f'"{self.__class__.__name__}.{attr_name}" from loaded value "{value}". '
                        f'Using default initialization instead.'
                    )
                else:
                    continue
            try:
                var.construct(self)
            except Exception as err:
                raise ModuleStateError(f'Default initialization of status variable "{var.name}" to '
                                       f'"{self.__class__.__name__}.{attr_name}" failed') from err

    @final
    def _clear_status_variables(self) -> None:
        try:
            self.__appdata_filehandler.clear()
        finally:
            self.sigModuleAppDataChanged.emit(self.module_has_appdata)

    @final
    def _send_balloon_message(self,
                              title: str,
                              message: str,
                              time: Optional[float] = None,
                              icon: Optional[QtGui.QIcon] = None) -> None:
        if self._qudi_main.gui is None:
            log = get_logger('balloon-message')
            log.warning(f'{title}:\n{message}')
            return
        self._qudi_main.gui.balloon_message(title, message, time, icon)

    @final
    def _send_pop_up_message(self, title: str, message: str) -> None:
        if self._qudi_main.gui is None:
            log = get_logger('pop-up-message')
            log.warning(f'{title}:\n{message}')
            return
        self._qudi_main.gui.pop_up_message(title, message)

    def __activation_callback(self, event=None) -> bool:
        """ Restore status variables before activation and invoke on_activate method.
        DO NOT INVOKE THIS METHOD DIRECTLY!
        """
        try:
            self._load_status_variables()
            self.on_activate()
        except Exception:
            if self.module_threaded:
                self.log.exception('Exception during threaded activation:')
            raise
        return True

    def __deactivation_callback(self, event=None) -> bool:
        """ Invoke on_deactivate method and save status variables afterwards even if deactivation
        fails.
        DO NOT INVOKE THIS METHOD DIRECTLY!
        """
        try:
            try:
                self.on_deactivate()
            finally:
                # save status variables even if deactivation failed
                try:
                    self._dump_status_variables()
                finally:
                    self.__clear_connectors()
        except Exception:
            self.log.exception('Exception during deactivation:')
        # Always return True to allow for state transition
        return True

    def __state_change_callback(self, event=None) -> None:
        try:
            state = ModuleState(event.dst)
        except AttributeError:
            state = self.module_state
        self.sigModuleStateChanged.emit(state)

    @abstractmethod
    def on_activate(self) -> None:
        """ Method called when module is activated. Must be implemented by actual qudi module. """
        raise NotImplementedError('Please implement and specify the activation method.')

    @abstractmethod
    def on_deactivate(self) -> None:
        """ Method called when module is deactivated. Must be implemented by actual qudi module. """
        raise NotImplementedError('Please implement and specify the deactivation method.')


class LogicBase(Base):
    """
    """
    _threaded = True


class GuiBase(Base):
    """This is the GUI base class. It provides functions that every GUI module should have.
    """
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
    def __init__(self, module_name: str, module_base: Union[str, ModuleBase], class_name: str):
        module_base = ModuleBase(module_base)
        super().__init__(
            file_path=get_module_app_data_path(class_name, module_base.value, module_name)
        )


class ModuleStateMachine(Fysom):
    """ Finite state machine controlling the state of a qudi module. Deactivation is possible from
    every other state.

                                     ------<------
                                     |           ^
                                     v           |
        [*] ----> deactivated ----> idle ----> busy
                      ^              |           |
                      |              v           v
                      -------<-------------<------
    """
    def __init__(self,
                 callbacks: Optional[Mapping[str, Callable[[object], bool]]] = None,
                 **kwargs):
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
    """ QObject wrapper for module FSM control """

    def __init__(self,
                 module_instance: Base,
                 activation_callback: Callable[[object], bool],
                 deactivation_callback: Callable[[object], bool],
                 state_change_callback: Callable[[object], None]):
        if not isinstance(module_instance, Base):
            raise TypeError('Parameter "module_instance" of ModuleStateControl.__init__ '
                            'expects qudi.core.module.Base instance.')
        if not (callable(activation_callback) and callable(deactivation_callback) and callable(state_change_callback)):
            raise TypeError(
                'Parameters "activation_callback", "deactivation_callback" and '
                '"state_change_callback" of ModuleStateControl.__init__ must be callables'
            )
        super().__init__(parent=module_instance)
        self._fsm = ModuleStateMachine(
            callbacks={'on_before_activate'  : activation_callback,
                       'on_before_deactivate': deactivation_callback,
                       'on_change_state'     : state_change_callback}
        )

    @property
    def state(self) -> ModuleState:
        return ModuleState(self._fsm.current)

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
