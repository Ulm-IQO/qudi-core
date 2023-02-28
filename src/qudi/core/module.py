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
from abc import abstractmethod
from uuid import uuid4
from fysom import Fysom
from PySide2 import QtCore, QtGui, QtWidgets
from typing import Any, Mapping, MutableMapping, Optional, Union, Dict

from qudi.core.configoption import MissingAction
from qudi.core.statusvariable import StatusVar
from qudi.core.connector import ModuleConnectionError
from qudi.util.paths import get_module_app_data_path, get_daily_directory, get_default_data_dir
from qudi.util.yaml import yaml_load, yaml_dump
from qudi.core.meta import QudiObjectMeta
from qudi.core.logger import get_logger


class ModuleStateMachine(Fysom, QtCore.QObject):
    """
    FIXME
    """
    # do not copy declaration of trigger(self, event, *args, **kwargs), just apply Slot decorator
    trigger = QtCore.Slot(str, result=bool)(Fysom.trigger)

    # signals
    sigStateChanged = QtCore.Signal(object)  # Fysom event

    def __init__(self, callbacks=None, parent=None, **kwargs):
        if callbacks is None:
            callbacks = dict()

        # State machine definition
        # the abbreviations for the event list are the following:
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
        super().__init__(parent=parent, cfg=fsm_cfg, **kwargs)

    def __call__(self) -> str:
        """
        Returns the current state.
        """
        return self.current

    def on_change_state(self, e: Any) -> None:
        """
        Fysom callback for all state transitions.

        @param object e: Fysom event object passed through all state transition callbacks
        """
        self.sigStateChanged.emit(e)

    @QtCore.Slot()
    def activate(self) -> None:
        super().activate()

    @QtCore.Slot()
    def deactivate(self) -> None:
        super().deactivate()

    @QtCore.Slot()
    def lock(self) -> None:
        super().lock()

    @QtCore.Slot()
    def unlock(self) -> None:
        super().unlock()


class Base(QtCore.QObject, metaclass=QudiObjectMeta):
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

    # FIXME: This __new__ implementation has the sole purpose to circumvent a known PySide2(6) bug.
    #  See https://bugreports.qt.io/browse/PYSIDE-1434 for more details.
    def __new__(cls, *args, **kwargs):
        abstract = getattr(cls, '__abstractmethods__', frozenset())
        if abstract:
            raise TypeError(f'Can\'t instantiate abstract class "{cls.__name__}" '
                            f'with abstract methods {set(abstract)}')
        return super().__new__(cls, *args, **kwargs)

    def __init__(self,
                 qudi_main_weakref: Any,
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
        self.__qudi_main_weakref = qudi_main_weakref

        # Create logger instance for module
        self.__logger = get_logger(f'{self.__module__}.{self.__class__.__name__}')

        # Add additional module info
        self.__module_name = name
        self.__module_uuid = uuid4()
        if isinstance(self, GuiBase):
            self.__module_base = 'gui'
        elif isinstance(self, LogicBase):
            self.__module_base = 'logic'
        else:
            self.__module_base = 'hardware'

        # Initialize module FSM
        fsm_callbacks = {'on_before_activate'  : self.__activation_callback,
                         'on_before_deactivate': self.__deactivation_callback}
        self.module_state = ModuleStateMachine(parent=self, callbacks=fsm_callbacks)

        # set instance attributes according to ConfigOption meta-objects
        self.__init_config_options(options)
        # connect other modules according to Connector meta-objects
        self.__connect_modules(connections)

    def __init_config_options(self, option_values: Optional[Mapping[str, Any]]) -> None:
        for attr_name, cfg_opt in self._meta['config_options'].items():
            try:
                value = option_values[cfg_opt.name]
            except KeyError:
                if cfg_opt.missing_action == MissingAction.ERROR:
                    raise ValueError(
                        f'Required ConfigOption "{cfg_opt.name}" not given in module configuration '
                        f'options:\n{option_values}'
                    )
                msg = f'No ConfigOption "{cfg_opt.name}" configured, using default value ' \
                      f'"{cfg_opt.default}" instead.'
                if cfg_opt.missing_action == MissingAction.WARN:
                    self.log.warning(msg)
                elif cfg_opt.missing_action == MissingAction.INFO:
                    self.log.info(msg)
            else:
                cfg_opt.construct(self, copy.deepcopy(value))

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
        if QtCore.QThread.currentThread() != self.thread():
            QtCore.QMetaObject.invokeMethod(self,
                                            'move_to_main_thread',
                                            QtCore.Qt.BlockingQueuedConnection)
        else:
            self.moveToThread(QtCore.QCoreApplication.instance().thread())

    @property
    def module_thread(self) -> Union[QtCore.QThread, None]:
        """ Read-only property returning the current module QThread instance if the module is
        threaded. Returns None otherwise.
        """
        if self._threaded:
            return self.thread()
        return None

    @property
    def module_name(self) -> str:
        """ Read-only property returning the module name of this module instance as specified in the
        config.
        """
        return self.__module_name

    @property
    def module_base(self) -> str:
        """ Read-only property returning the module base of this module instance
        ('hardware' 'logic' or 'gui')
        """
        return self.__module_base

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
    def module_status_variables(self) -> Dict[str, Any]:
        return {var.name: var.represent(self) for var in self._meta['status_variables'].values()}

    @property
    def _qudi_main(self) -> Any:
        qudi_main = self.__qudi_main_weakref()
        if qudi_main is None:
            raise RuntimeError(
                'Unexpected missing qudi main instance. It has either been deleted or garbage '
                'collected.'
            )
        return qudi_main

    @property
    def log(self) -> logging.Logger:
        """ Returns the module logger instance
        """
        return self.__logger

    @property
    def is_module_threaded(self) -> bool:
        """ Returns whether the module shall be started in its own thread.
        """
        return self._threaded

    def __activation_callback(self, event=None) -> bool:
        """ Restore status variables before activation and invoke on_activate method.
        """
        try:
            self._load_status_variables()
            self.on_activate()
        except:
            self.log.exception('Exception during activation:')
            return False
        return True

    def __deactivation_callback(self, event=None) -> bool:
        """ Invoke on_deactivate method and save status variables afterwards even if deactivation
        fails.
        """
        try:
            self.on_deactivate()
        except:
            self.log.exception('Exception during deactivation:')
        finally:
            # save status variables even if deactivation failed
            self._dump_status_variables()
            self.__disconnect_modules()
        return True

    def _load_status_variables(self) -> None:
        """ Load status variables from app data directory on disc.
        """
        # Load status variables from app data directory
        file_path = get_module_app_data_path(self.__class__.__name__,
                                             self.module_base,
                                             self.module_name)
        try:
            variables = yaml_load(file_path, ignore_missing=True)
        except:
            variables = dict()
            self.log.exception('Failed to load status variables:')

        # Set instance attributes according to StatusVar meta-objects
        if variables:
            for var in self._meta['status_variables'].values():
                try:
                    value = variables[var.name]
                except KeyError:
                    continue
                try:
                    var.construct(self, value)
                except:
                    self.log.exception(f'Error while restoring status variable "{var.name}":')

    def _dump_status_variables(self) -> None:
        """ Dump status variables to app data directory on disc.

        This method can also be used to manually dump status variables independent of the automatic
        dump during module deactivation.
        """
        file_path = get_module_app_data_path(self.__class__.__name__,
                                             self.module_base,
                                             self.module_name)
        # collect StatusVar values into dictionary
        try:
            variables = self.module_status_variables
        except:
            self.log.exception('Error while representing status variables for saving:')
            variables = dict()

        # Save to file if any StatusVars have been found
        if variables:
            try:
                yaml_dump(file_path, variables)
            except:
                self.log.exception('Failed to save status variables:')

    def _send_balloon_message(self, title: str, message: str, time: Optional[float] = None,
                              icon: Optional[QtGui.QIcon] = None) -> None:
        qudi_main = self.__qudi_main_weakref()
        if qudi_main is None:
            return
        if qudi_main.gui is None:
            log = get_logger('balloon-message')
            log.warning(f'{title}:\n{message}')
            return
        qudi_main.gui.balloon_message(title, message, time, icon)

    def _send_pop_up_message(self, title: str, message: str):
        qudi_main = self.__qudi_main_weakref()
        if qudi_main is None:
            return
        if qudi_main.gui is None:
            log = get_logger('pop-up-message')
            log.warning(f'{title}:\n{message}')
            return
        qudi_main.gui.pop_up_message(title, message)

    def __connect_modules(self, connections: MutableMapping[str, Any]) -> None:
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

    def __disconnect_modules(self) -> None:
        """ Disconnects all Connector instances for this module. """
        for connector in self._meta['connectors'].values():
            connector.disconnect(self)

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
