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

import os
import warnings
from enum import Enum
from abc import abstractmethod
from fysom import Fysom
from PySide2 import QtCore, QtGui, QtWidgets
from typing import Any, Mapping, MutableMapping, Optional, Callable, final, Final

from qudi.core.statusvariable import StatusVar
from qudi.util.paths import get_daily_directory, get_default_data_dir, get_module_appdata_path
from qudi.util.helpers import current_is_native_thread
from qudi.core.object import QudiObject
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
    def __get__(self, instance, owner=None) -> bool:
        if owner is None:
            owner = type(instance)
        return owner._threaded

    def __delete__(self, instance):
        raise AttributeError('Can not delete')

    def __set__(self, instance, value):
        raise AttributeError('Read-Only')


class ModuleBaseDescriptor:
    def __get__(self, instance, owner=None) -> ModuleBase:
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
    """ Base class for all loadable modules. Hardware interface classes must inherit this
    (or hardware modules that do not inherit an interface).

    Does not run its own Qt event loop by default. In the rare case a hardware module needs its
    own event loop, overwrite and set the class attribute "_threaded = True" in the hardware
    implementation class.
    """
    _threaded: bool = False

    module_threaded = ThreadedDescriptor()
    module_base = ModuleBaseDescriptor()

    sigStateChanged = QtCore.Signal(ModuleState)

    def __init__(self,
                 qudi_main: Any,
                 name: str,
                 options: Optional[Mapping[str, Any]] = None,
                 connections: Optional[MutableMapping[str, Any]] = None):
        """ Initialize Base instance. Set up its state machine, initializes ConfigOption meta
        attributes from given config and connects activated module dependencies.
        """
        super().__init__(
            options=options,
            connections=connections,
            appdata_filepath=get_module_appdata_path(cls_name=self.__class__.__name__,
                                                     module_base=self.module_base.value,
                                                     module_name=name),
            logger_nametag=name
        )

        # Keep reference to qudi main instance
        self.__qudi_main = qudi_main
        # Add additional module info
        self.__module_name = name
        # Initialize module state
        self.__module_state_control = ModuleStateControl(module_instance=self)

    @property
    @final
    def _qudi_main(self) -> Any:
        return self.__qudi_main

    @property
    @final
    def module_state(self) -> 'ModuleStateControl':
        return self.__module_state_control

    @property
    @final
    def module_name(self) -> str:
        """ Read-only property returning the module name of this module instance as specified in the
        config.
        """
        return self.__module_name

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
    def _send_balloon_message(self,
                              title: str,
                              message: str,
                              time: Optional[float] = None,
                              icon: Optional[QtGui.QIcon] = None) -> None:
        if self._qudi_main.gui is None:
            log = get_logger('balloon-message')
            log.warning(f'{title}:\n{message}')
        else:
            self._qudi_main.gui.balloon_message(title, message, time, icon)

    @final
    def _send_pop_up_message(self, title: str, message: str) -> None:
        if self._qudi_main.gui is None:
            log = get_logger('pop-up-message')
            log.warning(f'{title}:\n{message}')
        else:
            self._qudi_main.gui.pop_up_message(title, message)

    @abstractmethod
    def on_activate(self) -> None:
        """ Method called when module is activated. Must be implemented by actual qudi module. """
        raise NotImplementedError('Please implement and specify the activation method.')

    @abstractmethod
    def on_deactivate(self) -> None:
        """ Method called when module is deactivated. Must be implemented by actual qudi module. """
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


class ModuleStateControl(QtCore.QObject):
    """ QObject providing FSM state control handling activation, deactivation, locking and
    unlocking of qudi modules.
    State transitions must only ever be triggered from the native thread of the respective module
    (the parent).

                                     ------<------
                                     |           ^
                                     v           |
        [*] ----> deactivated ----> idle ----> locked
                      ^              |           |
                      |              v           v
                      -------<-------------<------
    """
    def __init__(self, module_instance: Base):
        if not isinstance(module_instance, Base):
            raise TypeError('Parameter "module_instance" expects qudi.core.module.Base instance')
        super().__init__(parent=module_instance)
        self._current_state = ModuleState.DEACTIVATED

    @property
    def state(self) -> ModuleState:
        return self._current_state

    @property
    def deactivated(self) -> bool:
        return self._current_state == ModuleState.DEACTIVATED

    @property
    def idle(self) -> bool:
        return self._current_state == ModuleState.IDLE

    @property
    def locked(self) -> bool:
        return self._current_state == ModuleState.LOCKED

    def __call__(self) -> str:
        """ For backwards compatibility """
        warnings.warn(
            'Being able to call ModuleStateControl to get a string representation of the '
            'ModuleState Enum is deprecated and will be removed in the future. Please compare '
            '("==") ModuleStateControl directly with ModuleState or use '
            'ModuleStateControl.state.value if you must have the string representation.',
            DeprecationWarning,
            stacklevel=2
        )
        return self.state.value

    def __eq__(self, other) -> bool:
        """ Enables comparison with ModuleState Enum and other ModuleStateControl instances """
        if isinstance(other, ModuleState):
            return self._current_state.value == other.value
        elif isinstance(other, ModuleStateControl):
            return self.state.value == other.state.value
        return False

    @QtCore.Slot()
    def activate(self) -> None:
        """ Restore status variables first and invoke on_activate method afterward """
        assert current_is_native_thread(self), ('Module state changes can only be triggered by the '
                                                'modules native thread')
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
                module.log.exception('Exception during threaded activation:')
            raise
        finally:
            module.sigStateChanged.emit(self._current_state)

    @QtCore.Slot()
    def deactivate(self) -> None:
        """ Invoke on_deactivate method first and dump status variables afterward.
        State transition will always happen, even if an exception is raised.
        """
        assert current_is_native_thread(self), ('Module state changes can only be triggered by the '
                                                'modules native thread')
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
            if module.module_threaded:
                module.log.exception('Exception during threaded deactivation:')
            raise
        finally:
            self._current_state = ModuleState.DEACTIVATED
            module.sigStateChanged.emit(self._current_state)

    @QtCore.Slot()
    def lock(self) -> None:
        """ Sets the state to "locked"/"busy" """
        assert current_is_native_thread(self), ('Module state changes can only be triggered by the '
                                                'modules native thread')
        try:
            if self._current_state == ModuleState.IDLE:
                self._current_state = ModuleState.LOCKED
            else:
                raise ModuleStateError(
                    f'Module can only be locked from "{ModuleState.IDLE.value}" state. Current '
                    f'state is "{self._current_state.value}".'
                )
        finally:
            self.parent().sigStateChanged.emit(self._current_state)

    @QtCore.Slot()
    def unlock(self) -> None:
        assert current_is_native_thread(self), ('Module state changes can only be triggered by the '
                                                'modules native thread')
        try:
            if self._current_state == ModuleState.LOCKED:
                self._current_state = ModuleState.IDLE
            else:
                raise ModuleStateError(
                    f'Module can only be unlocked from "{ModuleState.LOCKED.value}" state. '
                    f'Current state is "{self._current_state.value}".'
                )
        finally:
            self.parent().sigStateChanged.emit(self._current_state)
