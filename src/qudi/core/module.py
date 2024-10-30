# -*- coding: utf-8 -*-
"""
Contains base classes for all qudi module implementations (gui, logic, hardware) as well as some
related utility functions.

Copyright (c) 2021-2024, the qudi developers. See the AUTHORS.md file at the top-level directory of
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

__all__ = ['module_url', 'validate_module_base', 'import_module_type', 'module_thread_name',
           'ModuleStateError', 'ModuleBase', 'ModuleState', 'ModuleStateMachine', 'Base',
           'HardwareBase', 'LogicBase', 'GuiBase']

import os
import warnings
import importlib
from abc import abstractmethod
from enum import Enum
from uuid import uuid4, UUID
from PySide2 import QtCore, QtWidgets
from typing import Any, Mapping, Optional, Type, Dict, Final, MutableMapping, final

from qudi.core.object import QudiQObject
from qudi.core.statusvariable import StatusVar
from qudi.util.helpers import current_is_native_thread
from qudi.util.paths import get_default_data_dir


class ModuleStateError(RuntimeError):
    """Error type related to qudi module state transitions"""
    pass


class ModuleState(Enum):
    """Qudi modules state enum with name strings as values and convenient state checking properties.
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
    """Qudi modules base type enum with name strings as values"""
    HARDWARE = 'hardware'
    LOGIC = 'logic'
    GUI = 'gui'


class _ThreadedDescriptor:
    """Read-only class descriptor representing the value of the owners private class attribute
    "_threaded".
    """
    def __get__(self, instance, owner=None) -> bool:
        if owner is None:
            return type(instance)._threaded
        else:
            return owner._threaded

    def __delete__(self, instance):
        raise AttributeError('Can not delete')

    def __set__(self, instance, value):
        raise AttributeError('Read-Only')


class _ModuleBaseDescriptor:
    """Read-only class descriptor representing the owners qudi module base type enum"""
    def __get__(self, instance, owner=None) -> ModuleBase:
        if owner is None:
            owner = type(instance)

        if issubclass(owner, GuiBase):
            base = ModuleBase.GUI
        elif issubclass(owner, LogicBase):
            base = ModuleBase.LOGIC
        elif issubclass(owner, Base):
            base = ModuleBase.HARDWARE
        else:
            raise TypeError(
                f'{owner.__module__}.{owner.__name__} is not a subclass of {Base.__module__}.Base'
            )
        return base

    def __delete__(self, instance):
        raise AttributeError('Can not delete')

    def __set__(self, instance, value):
        raise AttributeError('Read-Only')


class ModuleStateMachine(QtCore.QObject):
    """QObject providing FSM state control handling activation, deactivation, locking and
    unlocking of qudi modules.
    State transitions must only ever be triggered from the native thread of the owning module.

                                     ------<------
                                     |           ^
                                     v           |
        [*] ----> deactivated ----> idle ----> locked
                      ^              |           |
                      |              v           v
                      -------<-------------<------

    Parameters
    ----------
    module_instance : qudi.core.module.Base
        Parent qudi module instance.
    """
    sigStateChanged = QtCore.Signal(ModuleState)  # new ModuleState

    def __init__(self, module_instance: 'Base'):
        super().__init__(parent=module_instance)
        self._module_instance = module_instance
        self._current_state = ModuleState.DEACTIVATED
        self.__warned = False

    @property
    def current(self) -> ModuleState:
        """Read-only property representing the current module state"""
        return self._current_state

    @property
    def deactivated(self) -> bool:
        return self.current.deactivated

    @property
    def activated(self) -> bool:
        return self.current.activated

    @property
    def idle(self) -> bool:
        return self.current.idle

    @property
    def locked(self) -> bool:
        return self.current.locked

    def __call__(self) -> str:
        """
        For backwards compatibility only.

        .. deprecated:: 2.0.0
            Being able to call `ModuleStateMachine` to get a string representation of `ModuleState`
            enum will be removed in the future. Please compare (`==`) `ModuleStateMachine` directly
            with `ModuleState` or use `ModuleStateMachine.current.value` if you must have the string
            representation.
        """
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
        """Enables comparison with `ModuleState` enum and other `ModuleStateMachine` instances.
        Compare enum values directly to avoid problems with multiprocessing.
        """
        if isinstance(other, ModuleState):
            return self.current.value == other.value
        elif isinstance(other, ModuleStateMachine):
            return self.current.value == other.current.value
        return False

    @QtCore.Slot()
    def activate(self) -> None:
        """
        Callback for qudi module activation. Load AppData from disk first and invoke `on_activate`
        method afterward.
        Must only ever be called from native module thread.

        Raises
        ------
        ModuleStateError
            If anything goes wrong during activation.
        """
        self._check_caller_thread()
        try:
            if self.deactivated:
                try:
                    self._module_instance.appdata.load()
                    self._module_instance.on_activate()
                except Exception as err:
                    raise ModuleStateError('Exception during module activation') from err
                else:
                    self._current_state = ModuleState.IDLE
            else:
                raise ModuleStateError(
                    f'Module can only be activated from "{ModuleState.DEACTIVATED.value}" state. '
                    f'Current state is "{self.current.value}".'
                )
        except ModuleStateError:
            if self._module_instance.module_threaded:
                self._module_instance.log.exception('Exception during threaded activation:')
            raise
        finally:
            self._emit_state_change()

    @QtCore.Slot()
    def deactivate(self) -> None:
        """
        Callback for qudi module deactivation. Invoke `on_deactivate` method first and dump AppData
        to disk afterward.
        State transition will always happen, even if an exception is raised.
        Must only ever be called from native module thread.

        Raises
        ------
        ModuleStateError
            If anything goes wrong during deactivation.
        """
        self._check_caller_thread()
        try:
            if self.activated:
                try:
                    try:
                        self._module_instance.on_deactivate()
                    finally:
                        # save status variables even if deactivation failed
                        self._module_instance.appdata.dump()
                except Exception as err:
                    raise ModuleStateError('Exception during module deactivation') from err
            else:
                raise ModuleStateError(f'Module already in state "{self.current.value}"')
        except ModuleStateError:
            if self._module_instance.module_threaded:
                self._module_instance.log.exception('Exception during threaded deactivation:')
            raise
        finally:
            self._current_state = ModuleState.DEACTIVATED
            self._emit_state_change()

    @QtCore.Slot()
    def lock(self) -> None:
        """
        Callback for qudi module state transition from `ModuleState.IDLE` to `ModuleState.LOCKED`.

        Raises
        ------
        ModuleStateError
            If anything goes wrong during state transition.
        """
        try:
            if self.idle:
                self._current_state = ModuleState.LOCKED
            else:
                raise ModuleStateError(
                    f'Module can only be locked from "{ModuleState.IDLE.value}" state. Current '
                    f'state is "{self.current.value}".'
                )
        finally:
            self._emit_state_change()

    @QtCore.Slot()
    def unlock(self) -> None:
        """
        Callback for qudi module state transition from `ModuleState.LOCKED` to `ModuleState.IDLE`.

        Raises
        ------
        ModuleStateError
            If anything goes wrong during state transition.
        """
        try:
            if self.locked:
                self._current_state = ModuleState.IDLE
            else:
                raise ModuleStateError(
                    f'Module can only be unlocked from "{ModuleState.LOCKED.value}" state. '
                    f'Current state is "{self.current.value}".'
                )
        finally:
            self._emit_state_change()

    def _emit_state_change(self) -> None:
        self.sigStateChanged.emit(self.current)

    def _check_caller_thread(self) -> None:
        if not current_is_native_thread(self._module_instance):
            raise ModuleStateError('Module activation and deactivation can only be triggered by '
                                   'the modules native thread')


class Base(QudiQObject):
    """
    Base class for all qudi modules.
    Hardware interfaces and hardware modules not implementing an interface must inherit this.

    Does not run its own Qt event loop by default. In the rare case a hardware module needs its
    own event loop, overwrite and set the class attribute `_threaded = True` in the class
    implementation.

    Each module name will be assigned a UUID which will remain the same for multiple instantiations
    with the same module name.

    Parameters
    ----------
    name : str
        Human-readable, unique and non-empty module name string.
    options : dict, optional
        name-value pairs to initialize ConfigOption meta attributes with. Must provide at least as
        many items as there are mandatory ConfigOption attributes in the qudi module.
    connections : dict, optional
        name-value pairs to initialize Connector meta attributes with. Must provide at least as
        many items as there are mandatory Connector attributes in the qudi module.
    """
    _threaded: bool = False

    module_threaded: bool = _ThreadedDescriptor()
    module_base: ModuleBase = _ModuleBaseDescriptor()

    __url_uuid_map: Final[Dict[str, UUID]] = dict()  # Same module url will result in same UUID

    def __init__(self,
                 name: str,
                 options: Optional[Mapping[str, Any]] = None,
                 connections: Optional[MutableMapping[str, Any]] = None):
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
        # Add additional module info
        self.__module_url = mod_url
        # Initialize module state
        self.__module_state = ModuleStateMachine(module_instance=self)
        self.__warned = False

    @property
    @final
    def module_url(self) -> str:
        """Unique URL of this qudi module, e.g. `qudi.logic.my_logic.MyLogicModule::userlogic`"""
        return self.__module_url

    @property
    def module_uuid(self) -> UUID:
        """
        Backwards compatibility only.

        .. deprecated:: 2.0.0
            `Base.module_uuid` is deprecated and will be removed in the future. Please use
            `Base.uuid` instead.
        """
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
    def module_state(self) -> ModuleStateMachine:
        """The module state machine. Can be used to retrieve current state and change state."""
        return self.__module_state

    @property
    def module_default_data_dir(self) -> str:
        """
        Generic default directory in which to save user data for this qudi module.
        Module implementations can overwrite this with a custom path but should only do so with a
        very good reason.
        """
        return os.path.join(get_default_data_dir(), self.nametag)

    @abstractmethod
    def on_activate(self) -> None:
        """
        Method called when module is activated. Must be implemented by actual qudi module subclass.
        """
        raise NotImplementedError('Please implement and specify the activation method.')

    @abstractmethod
    def on_deactivate(self) -> None:
        """
        Method called when module is deactivated. Must be implemented by actual qudi module
        subclass.
        """
        raise NotImplementedError('Please implement and specify the deactivation method.')


HardwareBase = Base  # More verbose naming


class LogicBase(Base):
    """
    Base class for all qudi logic modules. Logic module implementations must inherit this.
    Runs its own thread with a Qt event loop, so setting `_threaded = False` is NOT permitted.
    """
    _threaded: Final[bool] = True


class GuiBase(Base):
    """
    Base class for all qudi GUI modules.
    GUI modules always run in the main Qt event loop, so setting `_threaded = True` is NOT
    permitted.

    ToDo: Enforce standardized QMainWindow handle in module implementations instead of `show`
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


def module_url(module: str, class_name: str, name: str) -> str:
    """
    Unique URL of a qudi module. It is composed of 3 parts:
      - Containing Python module URL, e.g. "qudi.logic.my_logic"
      - Class name within the Python module, e.g. "MyLogicModule"
      - Unique module name as defined in the user configuration, e.g. "userlogic123"
    So the complete URL spells "<module>.<class name>::<config name>",
    e.g. `qudi.logic.my_logic.MyLogicModule::userlogic123`.

    Parameters
    ----------
    module : str
        Import url of the containing python module, e.g. `qudi.logic.my_logic`.
    class_name : str
        Name of the module class, e.g. `MyLogicModule`
    name : str
        Unique module name usually defined by qudi configuration, e.g. `userlogic123`

    Returns
    -------
    str
        Full qudi module URL string, e.g. `qudi.logic.my_logic.MyLogicModule::userlogic123`
    """
    return f'{module}.{class_name}::{name}'


def module_thread_name(name: str, base: ModuleBase) -> str:
    """
    Generic name of the thread associated with a qudi module (logic or hardware).

    Parameters
    ----------
    name : str
        Unique module name usually defined by qudi configuration, e.g. `userlogic123`
    base : qudi.core.module.ModuleBase
        Qudi module base type enum.

    Returns
    -------
    str
        Qudi module thread name, e.g. `mod-logic-userlogic123`
    """
    return f'mod-{base.value}-{name}'


def validate_module_base(module: type, base: ModuleBase) -> None:
    """
    Validate if a certain type is a valid qudi module class of given `ModuleBase`.

    Parameters
    ----------
    module : type
        Type/Class to check for valid qudi module parent class specified by `ModuleBase`.
    base : qudi.core.module.ModuleBase
        Qudi module base type enum to check against.

    Raises
    ------
    TypeError
        If the checked type is no valid qudi module subclass identified by given `ModuleBase`.
    """
    if base == ModuleBase.GUI:
        required_base = GuiBase
    elif base == ModuleBase.LOGIC:
        required_base = LogicBase
    elif base == ModuleBase.HARDWARE:
        required_base = HardwareBase
    else:
        required_base = Base
    if not issubclass(module, required_base):
        raise TypeError(
            f'Type "{module.__module__}.{module.__qualname__}" is no valid qudi {base.value} '
            f'module subclass of "{required_base.__module__}.{required_base.__qualname__}"'
        )


def import_module_type(module: str,
                       cls: str,
                       base: ModuleBase,
                       reload: Optional[bool] = False) -> Type[Base]:
    """
    Helper function to imports a qudi module type by name and module strings. Performs type check
    based on given `ModuleBase` enum.

    Parameters
    ----------
    module : str
        Import url of the containing python module, e.g. `qudi.logic.my_logic`.
    cls : str
        Name of the module class, e.g. `MyLogicModule`.
    base : qudi.core.module.ModuleBase
        Qudi module base type enum to check against.
    reload : bool, optional
        If `True` this flag will force a reload of the python module from disk (defaults to
        `False`). Should generally not be used without a VERY good reason.

    Raises
    ------
    ImportError
        If the imported type is no valid qudi module subclass identified by given `ModuleBase` or
        anything else goes wrong during import.
    """
    # Import module
    try:
        mod = importlib.import_module(module)
        if reload:
            mod = importlib.reload(mod)
    except ImportError:
        raise
    except Exception as err:
        raise ImportError(f'Unable to import module "{module}"') from err

    # Get class from module and validate
    try:
        typ = getattr(mod, cls)
    except AttributeError:
        raise ImportError(f'No class "{cls}" found in module "{module}"') from None
    validate_module_base(module=typ, base=base)
    return typ
