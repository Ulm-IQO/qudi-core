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

__all__ = ['module_url', 'ModuleStateError', 'ModuleBase', 'ModuleState', 'ModuleStateMachine',
           'Base', 'LogicBase', 'GuiBase']

import os
import warnings
from abc import abstractmethod
from enum import Enum
from uuid import uuid4, UUID
from PySide2 import QtCore, QtGui, QtWidgets
from typing import Any, Mapping, Optional, Union, Dict, Final, MutableMapping, final

from qudi.core.statusvariable import StatusVar
from qudi.util.paths import get_daily_directory, get_default_data_dir
from qudi.core.object import QudiObject
from qudi.core.logger import get_logger
from qudi.util.helpers import current_is_native_thread


def module_url(module: str, class_name: str, name: str) -> str:
    """ The unique URL of a qudi module. It is composed of 3 parts:
    - Containing Python module URL, e.g. "qudi.logic.my_logic_module"
    - Class name within the Python module, e.g. "MyLogicModule"
    - Unique module name as defined in the user configuration, e.g. "userlogic"
    So the complete URL spells "<module>.<class name>::<config name>", e.g.
    "qudi.logic.my_logic_module.MyLogicModule::userlogic"
    """
    return f'{module}.{class_name}::{name}'


class ModuleStateError(RuntimeError):
    pass


class ModuleState(Enum):
    """ Qudi modules state enum with name strings as values and convenient state checking properties
    """
    DEACTIVATED = 'deactivated'
    IDLE = 'idle'
    LOCKED = 'locked'

    @property
    def deactivated(self) -> bool:
        return self is self.DEACTIVATED

    @property
    def activated(self) -> bool:
        return self is not self.DEACTIVATED

    @property
    def idle(self) -> bool:
        return self is self.IDLE

    @property
    def locked(self) -> bool:
        return self is self.LOCKED


class ModuleBase(Enum):
    """ Qudi modules base type enum with name strings as values """
    HARDWARE = 'hardware'
    LOGIC = 'logic'
    GUI = 'gui'


class _ThreadedDescriptor:
    """ Read-only class descriptor representing the owners private class attribute <_threaded> value
    """
    def __get__(self, instance, owner=None) -> bool:
        try:
            return owner._threaded
        except AttributeError:
            return type(instance)._threaded

    def __delete__(self, instance):
        raise AttributeError('Can not delete')

    def __set__(self, instance, value):
        raise AttributeError('Read-Only')


class _ModuleBaseDescriptor:
    """ Read-only class descriptor representing the owners qudi module base type enum """
    def __get__(self, instance, owner=None) -> ModuleBase:
        if owner is None:
            owner = type(instance)
        if issubclass(owner, GuiBase):
            return ModuleBase.GUI
        if issubclass(owner, LogicBase):
            return ModuleBase.LOGIC
        if issubclass(owner, Base):
            return ModuleBase.HARDWARE
        raise TypeError(
            f'{owner.__module__}.{owner.__name__} is not a subclass of {Base.__module__}.Base'
        )

    def __delete__(self, instance):
        raise AttributeError('Can not delete')

    def __set__(self, instance, value):
        raise AttributeError('Read-Only')


class ModuleStateMachine(QtCore.QObject):
    """ QObject providing FSM state control handling activation, deactivation, locking and
    unlocking of qudi modules.
    State transitions must only ever be triggered from the native thread of the respective module
    (the parent qudi module).

                                     ------<------
                                     |           ^
                                     v           |
        [*] ----> deactivated ----> idle ----> locked
                      ^              |           |
                      |              v           v
                      -------<-------------<------
    """
    sigStateChanged = QtCore.Signal(ModuleState)  # new ModuleState

    def __init__(self, module_instance: 'Base'):
        super().__init__(parent=module_instance)
        self._current_state = ModuleState.DEACTIVATED
        self.__warned = False

    def __getattr__(self, item):
        """ Make convenience state checking properties of ModuleState enum available through
        ModuleStateMachine
        """
        try:
            return getattr(self._current_state, item)
        except AttributeError:
            pass
        raise AttributeError

    @property
    def current(self) -> ModuleState:
        """ Read-only property representing the current ModuleState enum """
        return self._current_state

    def __call__(self) -> str:
        """ For backwards compatibility """
        if not self.__warned:
            warnings.warn(
                'Being able to call ModuleStateMachine to get a string representation of the '
                'ModuleState Enum is deprecated and will be removed in the future. Please compare '
                '("==") ModuleStateMachine directly with ModuleState or use '
                'ModuleStateMachine.current.value if you must have the string representation.',
                DeprecationWarning,
                stacklevel=2
            )
            self.__warned = True
        return self.current.value

    def __eq__(self, other) -> bool:
        """ Enables comparison with ModuleState Enum and other ModuleStateControl instances.
        Compare enum values directly to avoid problems with multiprocessing.
        """
        if isinstance(other, ModuleState):
            return self._current_state.value == other.value
        elif isinstance(other, ModuleStateMachine):
            return self._current_state.value == other._current_state.value
        return False

    @QtCore.Slot()
    def activate(self) -> None:
        """ Restore status variables first and invoke on_activate method afterward """
        self._check_caller_thread()
        module = self.parent()
        try:
            if self._current_state == ModuleState.DEACTIVATED:
                try:
                    module.load_status_variables()
                    module.on_activate()
                except Exception as err:
                    raise ModuleStateError('Exception during module activation') from err
                else:
                    self._current_state = ModuleState.IDLE
            else:
                raise ModuleStateError(
                    f'Module can only be activated from "{ModuleState.DEACTIVATED.value}" state. '
                    f'Current state is "{self._current_state.value}".'
                )
        except ModuleStateError:
            if module.module_threaded:
                logger = get_logger(f'{self.__module__}.{self.__class__.__name__}')
                logger.exception('Exception during threaded activation:')
            raise
        finally:
            self.sigStateChanged.emit(self._current_state)

    @QtCore.Slot()
    def deactivate(self) -> None:
        """ Invoke on_deactivate method first and dump status variables afterward.
        State transition will always happen, even if an exception is raised.
        """
        self._check_caller_thread()
        module = self.parent()
        try:
            if self._current_state != ModuleState.DEACTIVATED:
                try:
                    try:
                        module.on_deactivate()
                    finally:
                        # save status variables even if deactivation failed
                        module.dump_status_variables()
                except Exception as err:
                    raise ModuleStateError('Exception during module deactivation') from err
            else:
                raise ModuleStateError(f'Module already in state "{self._current_state.value}"')
        except ModuleStateError:
            if module.is_module_threaded:
                module.log.exception('Exception during threaded deactivation:')
            raise
        finally:
            self._current_state = ModuleState.DEACTIVATED
            self.sigStateChanged.emit(self._current_state)

    @QtCore.Slot()
    def lock(self) -> None:
        """ Sets the state to "locked"/"busy" """
        try:
            if self._current_state == ModuleState.IDLE:
                self._current_state = ModuleState.LOCKED
            else:
                raise ModuleStateError(
                    f'Module can only be locked from "{ModuleState.IDLE.value}" state. Current '
                    f'state is "{self._current_state.value}".'
                )
        finally:
            self.sigStateChanged.emit(self._current_state)

    @QtCore.Slot()
    def unlock(self) -> None:
        try:
            if self._current_state == ModuleState.LOCKED:
                self._current_state = ModuleState.IDLE
            else:
                raise ModuleStateError(
                    f'Module can only be unlocked from "{ModuleState.LOCKED.value}" state. '
                    f'Current state is "{self._current_state.value}".'
                )
        finally:
            self.sigStateChanged.emit(self._current_state)

    def _check_caller_thread(self) -> None:
        if not current_is_native_thread(self):
            raise ModuleStateError('Module activation and deactivation can only be triggered by '
                                   'the modules native thread')


class Base(QudiObject):
    """ Base class for all loadable modules. Hardware interface classes must inherit this
    (or hardware modules that do not inherit an interface).

    Does not run its own Qt event loop by default. In the rare case a hardware module needs its
    own event loop, overwrite and set the class attribute "_threaded = True" in the hardware
    implementation class.

    Each module name will be assigned a UUID which will remain the same for multiple instantiations
    with the same module name.
    """
    _threaded: bool = False

    module_threaded = _ThreadedDescriptor()
    module_base = _ModuleBaseDescriptor()

    __url_uuid_map: Final[Dict[str, UUID]] = dict()  # Same module url will result in same UUID

    def __init__(self,
                 qudi_main: Any,
                 name: str,
                 options: Optional[Mapping[str, Any]] = None,
                 connections: Optional[MutableMapping[str, Any]] = None):
        """ Initialize Base instance. Set up its state machine, initializes ConfigOption meta
        attributes from given config and connects activated module dependencies.
        """
        mod_url = module_url(self.__class__.__module__, self.__class__.__name__, name)
        try:
            uuid = self.__url_uuid_map[mod_url]
        except KeyError:
            uuid = uuid4()
            self.__url_uuid_map[mod_url] = uuid
        super().__init__(
            options=options,
            connections=connections,
            nametag=name,
            uuid=uuid
        )

        # Keep reference to qudi main instance
        self.__qudi_main = qudi_main
        # Add additional module info
        self.__module_url = mod_url
        # Initialize module state
        self.module_state = ModuleStateMachine(module_instance=self)
        self.__warned = False

    @property
    @final
    def _qudi_main(self) -> Any:
        return self.__qudi_main

    @property
    @final
    def module_url(self) -> str:
        """ The unique URL of this qudi module. It is composed of 3 parts:
        - Containing Python module URL, e.g. "qudi.logic.my_logic_module"
        - Class name within the Python module, e.g. "MyLogicModule"
        - Unique module name as defined in the user configuration, e.g. "userlogic"
        So the complete URL spells "<module>.<class name>::<config name>", e.g.
        "qudi.logic.my_logic_module.MyLogicModule::userlogic"
        """
        return self.__module_url

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
        return self.nametag

    @property
    def module_uuid(self) -> UUID:
        """ Backwards compatibility. To be removed. """
        if not self.__warned:
            warnings.warn(
                'Base.module_uuid is deprecated and will be removed in the future. '
                'Please use Base.uuid instead.',
                DeprecationWarning,
                stacklevel=2
            )
            self.__warned = True
        return self.uuid

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
        data_root = os.path.expanduser(data_root)
        if config['daily_data_dirs']:
            data_dir = os.path.join(get_daily_directory(root=data_root), self.module_name)
        else:
            data_dir = os.path.join(data_root, self.module_name)
        return data_dir

    @final
    def _send_balloon_message(self,
                              title: str,
                              message: str,
                              time: Optional[float] = None,
                              icon: Optional[QtGui.QIcon] = None) -> None:
        if self.__qudi_main.gui is None:
            log = get_logger('balloon-message')
            log.warning(f'{title}:\n{message}')
            return
        self.__qudi_main.gui.balloon_message(title, message, time, icon)

    @final
    def _send_pop_up_message(self, title: str, message: str) -> None:
        if self.__qudi_main.gui is None:
            log = get_logger('pop-up-message')
            log.warning(f'{title}:\n{message}')
            return
        self.__qudi_main.gui.pop_up_message(title, message)

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
    """ Base class for all qudi logic modules. Logic module implementations must inherit this.
    Runs its own thread with a Qt event loop, so setting "_threaded = False" is NOT allowed.
    """
    _threaded: Final[bool] = True


class GuiBase(Base):
    """ This is the base class for all qudi GUI modules. GUI modules always run in the main Qt
    event loop, so setting "_threaded = True" is NOT allowed.
    """
    _threaded: Final[bool] = False

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
