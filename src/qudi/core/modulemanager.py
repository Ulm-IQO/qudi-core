# -*- coding: utf-8 -*-
"""
This file contains the Qudi Manager class.

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

import os
import importlib
import copy
import weakref
import fysom

from enum import Enum
from typing import Set, Tuple, Mapping, Any, Union, MutableMapping, Dict, Optional, List
from functools import partial
from PySide2 import QtCore
from abc import abstractmethod

from qudi.util.mutex import Mutex, acquire_timeout
from qudi.util.helpers import call_slot_from_native_thread, called_from_native_thread
from qudi.core.logger import get_logger
from qudi.core.servers import get_remote_module_instance
from qudi.core.meta import ABCQObject
from qudi.core.module import Base, ModuleState, ModuleBase, ModuleStateFileHandler, ModuleStateError
from qudi.core.config.validator import validate_local_module_config, validate_remote_module_config
from qudi.core.config.validator import ValidationError


logger = get_logger(__name__)


class ModuleManager(QtCore.QObject):
    """
    """
    _instance = None  # Only class instance created will be stored here as weakref

    # name, base, state, has_appdata
    sigModuleStateChanged = QtCore.Signal(str, object)
    sigManagedModulesChanged = QtCore.Signal(dict)

    def __new__(cls, *args, **kwargs):
        try:
            if QtCore.QThread.currentThread() != QtCore.QCoreApplication.instance().thread():
                raise RuntimeError('ModuleManager can only be instantiated by main/GUI thread.')
        except AttributeError:
            pass
        if cls.instance() is None:
            obj = super().__new__(cls, *args, **kwargs)
            cls._instance = weakref.ref(obj)
            return obj
        raise RuntimeError(
            'ModuleManager is a singleton. An instance has already been created in this '
            'process. Please use ModuleManager.instance() instead.'
        )

    @classmethod
    def instance(cls):
        try:
            return cls._instance()
        except TypeError:
            return None

    def __init__(self, *args, qudi_main, **kwargs):
        super().__init__(*args, **kwargs)
        self._qudi_main = qudi_main
        self._modules = dict()

    def __contains__(self, item: str) -> bool:
        return item in self._modules

    @property
    def module_count(self) -> int:
        return len(self._modules)

    @property
    def module_names(self) -> List[str]:
        return list(self._modules)

    @property
    def module_states(self) -> Dict[str, Tuple[ModuleBase, ModuleState, bool]]:
        return {
            name: (mod.base, mod.state, mod.has_app_data) for name, mod in self._modules.items()
        }

    @property
    def module_instances(self) -> Dict[str, Base]:
        return {name: mod.instance for name, mod in self._modules.items()}

    def module_state(self, name: str) -> Tuple[ModuleBase, ModuleState, bool]:
        try:
            module = self._modules[name]
        except KeyError:
            raise KeyError(f'No module named "{name}" found in managed qudi modules. '
                           f'Can not check for module state.') from None
        return module.base, module.state, module.has_app_data

    def remove_module(self,
                      name: str,
                      ignore_missing: Optional[bool] = False,
                      emit_change: Optional[bool] = True) -> None:
        if not called_from_native_thread(self):
            raise RuntimeError(f'"remove_module" can only be called from main/GUI thread')
        try:
            self.deactivate_module(name)
        except KeyError:
            if not ignore_missing:
                raise
        finally:
            if emit_change:
                self.sigManagedModulesChanged.emit(self.module_states)

    def add_module(self,
                   name: str,
                   base: Union[str, ModuleBase],
                   configuration: Mapping[str, Any],
                   allow_overwrite: Optional[bool] = False,
                   emit_change: Optional[bool] = True) -> None:
        if not called_from_native_thread(self):
            raise RuntimeError(f'"add_module" can only be called from main/GUI thread')
        if allow_overwrite:
            self.remove_module(name, ignore_missing=True)
        elif name in self._modules:
            raise KeyError(f'Module with name "{name}" already registered.')
        if self._is_remote_module(configuration):
            module = RemoteManagedModule(self._qudi_main, self, name, base, configuration)
        else:
            module = LocalManagedModule(self._qudi_main, self, name, base, configuration)
        self._modules[name] = module
        self._update_module_dependencies()
        if emit_change:
            self.sigManagedModulesChanged.emit(self.module_states)

    def activate_module(self, name: str) -> None:
        try:
            module = self._modules[name]
        except KeyError:
            raise KeyError(f'No module named "{name}" found in managed qudi modules. '
                           f'Module activation aborted.') from None
        if call_slot_from_native_thread(module, 'activate', blocking=True):
            module.activate()

    def deactivate_module(self, name: str) -> None:
        try:
            module = self._modules[name]
        except KeyError:
            raise KeyError(f'No module named "{name}" found in managed qudi modules. '
                           f'Module deactivation aborted.') from None
        if call_slot_from_native_thread(module, 'deactivate', blocking=True):
            module.deactivate()

    def reload_module(self, name: str) -> None:
        try:
            module = self._modules[name]
        except KeyError:
            raise KeyError(f'No module named "{name}" found in managed qudi modules. '
                           f'Module reload aborted.') from None
        if call_slot_from_native_thread(module, 'reload', blocking=True):
            module.reload()

    def clear_module_app_data(self, name: str) -> None:
        try:
            module = self._modules[name]
        except KeyError:
            raise KeyError(f'No module named "{name}" found in managed qudi modules. '
                           f'Unable to clear module appdata.') from None
        module.clear_app_data()

    @QtCore.Slot()
    def activate_all_modules(self) -> None:
        if call_slot_from_native_thread(self, 'activate_all_modules', blocking=True):
            for module in self._modules.values():
                try:
                    module.activate()
                except:
                    pass

    @QtCore.Slot()
    def deactivate_all_modules(self) -> None:
        if call_slot_from_native_thread(self, 'deactivate_all_modules', blocking=True):
            for module in self._modules.values():
                try:
                    module.deactivate()
                except:
                    pass

    @QtCore.Slot()
    def remove_all_modules(self) -> None:
        if not called_from_native_thread(self):
            raise RuntimeError(f'"remove_all_modules" can only be called from main/GUI thread')
        for module_name in list(self._modules):
            self.remove_module(module_name, ignore_missing=True, emit_change=False)
        self.sigManagedModulesChanged.emit(self.module_states)

    def _update_module_dependencies(self) -> None:
        for mod_name, module in self._modules.items():
            # Update required modules
            for required_name in module.required_module_names:
                try:
                    module.required_modules[required_name] = self._modules[required_name]
                except KeyError:
                    pass  # module may not have been added to ModuleManager yet
            # Update dependent modules
            for dep_name, dep_module in self._modules.items():
                if mod_name in dep_module.required_module_names:
                    module.dependent_modules[dep_name] = dep_module

    def _is_remote_module(self, configuration: Mapping[str, Any]) -> bool:
        try:
            validate_remote_module_config(configuration)
            return True
        except ValidationError:
            pass
        try:
            validate_local_module_config(configuration)
            return False
        except ValidationError:
            pass
        raise ValueError('Invalid module configuration encountered. Configuration did not pass '
                         'local or remote module json schema validation.')


class ManagedModule(ABCQObject):
    """ Object representing a wrapper for a qudi module (gui, logic or hardware) to be managed by
    the ModuleManager object. Contains status properties and handles initialization, state
    transitions and connection of the module.
    """

    def __init__(self,
                 qudi_main,
                 module_manager: ModuleManager,
                 name: str,
                 base: Union[str, ModuleBase],
                 configuration: Mapping[str, Any]):
        if not isinstance(module_manager, ModuleManager):
            raise TypeError(
                f'ManagedModule expects {ModuleManager.__module__}.ModuleManager instance'
            )
        if not isinstance(name, str):
            raise TypeError('Module name must be str type')
        if len(name) < 1:
            raise ValueError('Module name must be non-empty string')
        super().__init__()
        self._thread_lock = Mutex()
        self._qudi_main = qudi_main
        self._module_manager = module_manager
        self._name = name
        self._base = ModuleBase(base)
        self._configuration = configuration
        self.required_modules = weakref.WeakValueDictionary()
        self.dependent_modules = weakref.WeakValueDictionary()

    @property
    @abstractmethod
    def url(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def instance(self) -> Union[None, Base]:
        raise NotImplementedError

    @property
    @abstractmethod
    def state(self) -> ModuleState:
        raise NotImplementedError

    @property
    @abstractmethod
    def has_app_data(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def clear_app_data(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def activate(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def deactivate(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def reload(self) -> None:
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self._name

    @property
    def base(self) -> ModuleBase:
        return self._base

    @property
    def is_active(self) -> bool:
        return self.state != ModuleState.DEACTIVATED

    @property
    def is_locked(self) -> bool:
        return self.state == ModuleState.LOCKED

    @property
    def required_module_names(self) -> Set[str]:
        return set(self._connect_cfg.values())

    @property
    def active_dependent_modules(self) -> Dict[str, Any]:
        return {mod_name: mod for mod_name, mod in self.dependent_modules.items() if mod.is_active}

    @QtCore.Slot(ModuleState)
    def _state_changed(self, state: Optional[Union[str, ModuleState]] = None) -> None:
        if state is None:
            state = self.state
        else:
            state = ModuleState(state)
        self._module_manager.sigModuleStateChanged.emit(self.name,
                                                        (self.base, state, self.has_app_data))

    @QtCore.Slot()
    def _appdata_changed(self) -> None:
        self._state_changed()


class LocalManagedModule(ManagedModule):
    """
    """
    def __init__(self,
                 qudi_main,
                 module_manager: ModuleManager,
                 name: str,
                 base: ModuleBase,
                 configuration: Mapping[str, Any]):
        super().__init__(qudi_main, module_manager, name, base, configuration)
        # Sort out configuration
        try:
            self._allow_remote = configuration['allow_remote']
            self._options = configuration['options']
            self._connect_cfg = configuration['connect']
            self._module_name, self._class_name = configuration['module.Class'].rsplit('.', 1)
        except KeyError as err:
            raise ValueError('Invalid local module configuration encountered') from err
        self._module_name = f'qudi.{self._base.value}.{self._module_name}'
        # Circular recursion fail-saves
        self.__activating = self.__deactivating = False
        # Import qudi module class
        self._module = self._class = self._instance = None
        self.__import_module_class()
        # App status handling
        self._app_status_handler = ModuleStateFileHandler(self.base, self._class_name, self.name)

    def __import_module_class(self) -> None:
        # (re-)import module
        if self._module is None:
            self._module = importlib.import_module(self._module_name)
        else:
            importlib.reload(self._module)

        # Get class from module
        try:
            self._class = getattr(self._module, self._class_name)
        except AttributeError:
            self._module = self._instance = self._class = None
            raise ImportError(
                f'No class "{self._class_name}" found in module "{self._module_name}"'
            ) from None

        # Check if imported class is a valid qudi module class
        if not issubclass(self._class, Base):
            class_str = f'{self._class.__module__}.{self._class.__name__}'
            self._module = self._instance = self._class = None
            raise TypeError(
                f'Qudi module class "{class_str}" is no subclass of '
                f'"{Base.__module__}.{Base.__name__}"'
            )

    @property
    def url(self) -> str:
        return f'{self._module_name}.{self._class_name}'

    @property
    def module_thread_name(self):
        return f'mod-{self._base.value}-{self._name}'

    @property
    def instance(self) -> Union[None, Base]:
        return self._instance

    @property
    def state(self) -> ModuleState:
        try:
            return ModuleState(self._instance.module_state.current)
        except AttributeError:
            return ModuleState.DEACTIVATED

    @property
    def has_app_data(self) -> bool:
        return self._app_status_handler.exists

    @QtCore.Slot()
    def clear_app_data(self) -> None:
        self._app_status_handler.clear()

    @QtCore.Slot()
    def activate(self) -> None:
        with acquire_timeout(self._thread_lock, 0) as acquired:
            if acquired:
                self._activate()
            elif not (self.__activating or self.is_active):
                raise ModuleStateError(
                    f'{self.base.value.capitalize()} module "{self.name}" already in state '
                    f'transition. Unable to activate until transition is complete.'
                )

    def _activate(self) -> None:
        if self.is_active:
            if self.base == ModuleBase.GUI:
                self._instance.show()
            return

        self.__activating = True
        try:
            logger.info(f'Activating {self.base.value} module "{self.name}" ...')
            connections = self.__activate_required_modules()
            self.__instantiate_module_class(connections)
            if self._class.is_module_threaded():
                try:
                    self.__move_instance_to_thread()
                    self.__connect_module_instance()
                    self.__activate_instance_threaded()
                except Exception:
                    self.__disconnect_module_instance()
                    self.__join_instance_thread()
                    raise
            else:
                self.__connect_module_instance()
                try:
                    self.__activate_instance_direct()
                except Exception:
                    self.__disconnect_module_instance()
                    raise
            QtCore.QCoreApplication.instance().processEvents()
        except Exception:
            self._instance = None
            raise
        else:
            logger.info(f'{self.base.value.capitalize()} module "{self.name}" activated.')
        finally:
            self.__activating = False

    def __activate_required_modules(self) -> Dict[str, Base]:
        target_instances = dict()
        for mod_name, module in self.required_modules.items():
            module.activate()
            target_instances[mod_name] = module.instance
        return {conn: target_instances[target] for conn, target in self._connect_cfg.items()}

    def __instantiate_module_class(self, connections: MutableMapping[str, Base]) -> None:
        """ Try to instantiate the imported qudi module class """
        try:
            self._instance = self._class(qudi_main=self._qudi_main,
                                         name=self.name,
                                         options=self._options,
                                         connections=connections)
        except Exception as err:
            self._instance = None
            raise RuntimeError(f'Error during __init__ of qudi module "{self.url}".') from err

    def __connect_module_instance(self) -> None:
        self._instance.module_state.sigStateChanged.connect(self._state_changed)

    def __move_instance_to_thread(self) -> None:
        thread_name = self.module_thread_name
        thread_manager = self._qudi_main.thread_manager
        thread = thread_manager.get_new_thread(thread_name)
        self._instance.moveToThread(thread)
        thread.start()

    def __join_instance_thread(self) -> None:
        thread_name = self.module_thread_name
        thread_manager = self._qudi_main.thread_manager
        QtCore.QMetaObject.invokeMethod(self._instance,
                                        'move_to_main_thread',
                                        QtCore.Qt.BlockingQueuedConnection)
        thread_manager.quit_thread(thread_name)
        thread_manager.join_thread(thread_name)

    def __activate_instance_threaded(self) -> None:
        QtCore.QMetaObject.invokeMethod(self._instance.module_state,
                                        'activate',
                                        QtCore.Qt.BlockingQueuedConnection)
        # Check if activation has been successful
        if not self.is_active:
            raise RuntimeError(
                f'Error during on_activate execution of {self.base.value} module "{self.name}"'
            )

    def __activate_instance_direct(self) -> None:
        self._instance.module_state.activate()

    @QtCore.Slot()
    def deactivate(self) -> None:
        with acquire_timeout(self._thread_lock, 0) as acquired:
            if acquired:
                self._deactivate()
            elif not (self.__deactivating or not self.is_active):
                raise ModuleStateError(
                    f'{self.base.value.capitalize()} module "{self.name}" already in state '
                    f'transition. Unable to deactivate until transition is complete.'
                )

    def _deactivate(self) -> None:
        if not self.is_active:
            return

        self.__deactivating = True
        logger.info(f'Deactivating {self.base.value} module "{self.name}" ...')
        try:
            try:
                self.__deactivate_dependent_modules()
            finally:
                if self._class.is_module_threaded():
                    try:
                        self.__deactivate_instance_threaded()
                    finally:
                        self.__join_instance_thread()
                else:
                    self.__deactivate_instance_direct()
        finally:
            try:
                QtCore.QCoreApplication.instance().processEvents()
                self.__disconnect_module_instance()
            finally:
                self._instance = None
                self.__deactivating = False
                logger.info(f'{self.base.value.capitalize()} module "{self.name}" deactivated.')

    def __deactivate_dependent_modules(self) -> None:
        for mod_name, module in self.dependent_modules.items():
            module.deactivate()

    def __deactivate_instance_threaded(self) -> None:
        QtCore.QMetaObject.invokeMethod(self._instance.module_state,
                                        'deactivate',
                                        QtCore.Qt.BlockingQueuedConnection)

    def __deactivate_instance_direct(self) -> None:
        self._instance.module_state.deactivate()

    def __disconnect_module_instance(self) -> None:
        self._instance.module_state.sigStateChanged.disconnect(self._state_changed)

    @QtCore.Slot()
    def reload(self) -> None:
        with acquire_timeout(self._thread_lock, 0) as acquired:
            if not acquired:
                raise ModuleStateError(
                    f'{self.base.value.capitalize()} module "{self.name}" already in state '
                    f'transition. Unable to reload until transition is complete.'
                )

            was_active = self.is_active
            if was_active:
                # Find all modules that are currently active and depend recursively on self
                active_dependent_modules = set(self.active_dependent_modules.values())
                while True:
                    dependency_count = len(active_dependent_modules)
                    for module in list(active_dependent_modules):
                        active_dependent_modules.update(module.active_dependent_modules.values())
                    if dependency_count == len(active_dependent_modules):
                        break
                self._deactivate()
            logger.info(f'Reloading {self.base.value} module "{self.name}" from <{self.url}>')
            self.__import_module_class()
            if was_active:
                self._activate()
                for module in active_dependent_modules:
                    module.activate()

    @QtCore.Slot()
    def lock(self) -> None:
        try:
            self._instance.module_state.lock()
        except AttributeError:
            raise ModuleStateError(f'Unable to lock {self.base.value} module "{self.name}". '
                                   f'Module is not active.') from None

    @QtCore.Slot()
    def unlock(self) -> None:
        try:
            self._instance.module_state.unlock()
        except AttributeError:
            raise RuntimeError(f'Unable to unlock {self.base.value} module "{self.name}". '
                               f'Module is not active.') from None


# class RemoteManagedModule(ManagedModule):
#     """
#     """
#     def __init__(self, qudi_main, module_manager: ModuleManager, name: str, base: ModuleBase, configuration: Mapping[str, Any]):
#         super().__init__(qudi_main, module_manager, name, base, configuration)
#         # Sort out configuration
#         self._native_name = configuration['native_module_name']
#         self._address = configuration['address']
#         self._port = configuration['port']
#         self._certfile = configuration['certfile']
#         self._keyfile = configuration['keyfile']
#
#     @property
#     def url(self) -> str:
#         return f'{self._address}:{self._port:d}/{self._native_name}'
#
#     @property
#     def instance(self) -> Union[None, Base]:
#
#
#     @property
#     def state(self) -> ModuleState:
#         return ModuleState(self._fsm.state)
#
#     @property
#     def has_app_data(self) -> bool:
#
#     def clear_app_data(self) -> None:
#
#     def activate(self) -> None:
#
#     def deactivate(self) -> None:
#
#     def reload(self) -> None:
#
#     def set_busy(self) -> None:
#
#     def set_idle(self) -> None:
