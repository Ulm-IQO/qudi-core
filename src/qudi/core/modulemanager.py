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
from typing import FrozenSet, Iterable, Mapping, Any, Union
from functools import partial
from PySide2 import QtCore
from abc import ABCMeta, abstractmethod

from qudi.util.mutex import RecursiveMutex, Mutex   # provides access serialization between threads
from qudi.core.logger import get_logger
from qudi.core.servers import get_remote_module_instance
from qudi.core.module import Base, ModuleState, ModuleBase, ModuleStateMachine

logger = get_logger(__name__)


class ModuleManager(QtCore.QObject):
    """
    """
    _instance = None  # Only class instance created will be stored here as weakref
    _lock = RecursiveMutex()

    sigModuleStateChanged = QtCore.Signal(str, str, str)
    sigModuleAppDataChanged = QtCore.Signal(str, str, bool)
    sigManagedModulesChanged = QtCore.Signal(dict)

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None or cls._instance() is None:
                obj = super().__new__(cls, *args, **kwargs)
                cls._instance = weakref.ref(obj)
                return obj
            raise RuntimeError(
                'ModuleManager is a singleton. An instance has already been created in this '
                'process. Please use ModuleManager.instance() instead.'
            )

    def __init__(self, *args, qudi_main, **kwargs):
        super().__init__(*args, **kwargs)
        self._qudi_main_ref = weakref.ref(qudi_main, self._qudi_main_ref_dead_callback)
        self._modules = dict()

    @classmethod
    def instance(cls):
        with cls._lock:
            if cls._instance is None:
                return None
            return cls._instance()

    def __len__(self):
        with self._lock:
            return len(self._modules)

    def __getitem__(self, key):
        with self._lock:
            return self._modules.__getitem__(key)

    def __setitem__(self, key, value):
        with self._lock:
            if value.name != key:
                raise NameError('ManagedModule.name attribute does not match key')
            self.add_module(value, allow_overwrite=True)

    def __delitem__(self, key):
        self.remove_module(key)

    def __contains__(self, item):
        with self._lock:
            return self._modules.__contains__(item)

    def clear(self):
        with self._lock:
            for module_name in tuple(self._modules):
                self.remove_module(module_name, ignore_missing=True, emit_change=False)
            self.sigManagedModulesChanged.emit(self.modules)

    def get(self, *args):
        with self._lock:
            return self._modules.get(*args)

    def items(self):
        return self._modules.copy().items()

    def values(self):
        return self._modules.copy().values()

    def keys(self):
        return self._modules.copy().keys()

    @property
    def module_names(self):
        with self._lock:
            return tuple(self._modules)

    @property
    def module_states(self):
        with self._lock:
            return {name: mod.state for name, mod in self._modules.items()}

    @property
    def module_instances(self):
        with self._lock:
            return {name: mod.instance for name, mod in self._modules.items() if
                    mod.instance is not None}

    @property
    def modules(self):
        return self._modules.copy()

    def remove_module(self, module_name, ignore_missing=False, emit_change=True):
        with self._lock:
            module = self._modules.pop(module_name, None)
            if module is None and not ignore_missing:
                raise KeyError(f'No module with name "{module_name}" registered.')
            module.deactivate()
            module.sigStateChanged.disconnect(self.sigModuleStateChanged)
            module.sigAppDataChanged.disconnect(self.sigModuleAppDataChanged)
            if module.allow_remote_access:
                remote_modules_server = self._qudi_main_ref().remote_modules_server
                if remote_modules_server is not None:
                    remote_modules_server.remove_shared_module(module_name)
            self.refresh_module_links()
            if emit_change:
                self.sigManagedModulesChanged.emit(self.modules)

    def add_module(self, name, base, configuration, allow_overwrite=False, emit_change=True):
        with self._lock:
            if not isinstance(name, str) or not name:
                raise TypeError('module name must be non-empty str type')
            if base not in ('gui', 'logic', 'hardware'):
                raise ValueError(f'No valid module base "{base}". '
                                 f'Unable to create qudi module "{name}".')
            if allow_overwrite:
                self.remove_module(name, ignore_missing=True)
            elif name in self._modules:
                raise ValueError(f'Module with name "{name}" already registered.')
            module = ManagedModule(self._qudi_main_ref, name, base, configuration)
            module.sigStateChanged.connect(self.sigModuleStateChanged)
            module.sigAppDataChanged.connect(self.sigModuleAppDataChanged)
            self._modules[name] = module
            self.refresh_module_links()
            # Register module in remote module service if module should be shared
            if module.allow_remote_access:
                remote_modules_server = self._qudi_main_ref().remote_modules_server
                if remote_modules_server is None:
                    raise RuntimeError(
                        f'Unable to share qudi module "{module.name}" as remote module. No remote '
                        f'module server running in this qudi process.'
                    )
                else:
                    logger.info(
                        f'Start sharing qudi module "{module.name}" via remote module server.'
                    )
                    remote_modules_server.share_module(module)
            if emit_change:
                self.sigManagedModulesChanged.emit(self.modules)

    def refresh_module_links(self):
        with self._lock:
            weak_refs = {
                name: weakref.ref(mod, partial(self._module_ref_dead_callback, module_name=name))
                for name, mod in self._modules.items()
            }
            for module_name, module in self._modules.items():
                # Add required module references
                required = set(module.connection_cfg.values())
                module.required_modules = set(
                    mod_ref for name, mod_ref in weak_refs.items() if name in required)
                # Add dependent module references
                module.dependent_modules = set(mod_ref for mod_ref in weak_refs.values() if
                                               module_name in mod_ref().connection_cfg.values())

    def activate_module(self, module_name):
        with self._lock:
            if module_name not in self._modules:
                raise KeyError(f'No module named "{module_name}" found in managed qudi modules. '
                               f'Module activation aborted.')
            self._modules[module_name].activate()

    def deactivate_module(self, module_name):
        with self._lock:
            if module_name not in self._modules:
                raise KeyError(f'No module named "{module_name}" found in managed qudi modules. '
                               f'Module deactivation aborted.')
            self._modules[module_name].deactivate()

    def reload_module(self, module_name):
        with self._lock:
            if module_name not in self._modules:
                raise KeyError(f'No module named "{module_name}" found in managed qudi modules. '
                               f'Module reload aborted.')
            return self._modules[module_name].reload()

    def clear_module_app_data(self, module_name):
        with self._lock:
            if module_name not in self._modules:
                raise KeyError(f'No module named "{module_name}" found in managed qudi modules. '
                               f'Can not clear module app status.')
            return self._modules[module_name].clear_module_app_data()

    def has_app_data(self, module_name):
        with self._lock:
            if module_name not in self._modules:
                raise KeyError(f'No module named "{module_name}" found in managed qudi modules. '
                               f'Can not check for app status file.')
            return self._modules[module_name].has_app_data()

    def start_all_modules(self):
        with self._lock:
            for module in self._modules.values():
                module.activate()

    def stop_all_modules(self):
        with self._lock:
            for module in self._modules.values():
                module.deactivate()

    def _module_ref_dead_callback(self, dead_ref, module_name):
        self.remove_module(module_name, ignore_missing=True)

    def _qudi_main_ref_dead_callback(self):
        logger.error('Qudi main reference no longer valid. This should never happen. Tearing down '
                     'ModuleManager.')
        self.clear()


class ManagedModule(metaclass=ABCMeta):
    """ Object representing a qudi module (gui, logic or hardware) to be managed by the qudi Manager
     object. Contains status properties and handles initialization, state transitions and
     connection of the module.
    """

    def __init__(self, qudi_main, name: str, base: ModuleBase, configuration: Mapping[str, Any]):
        super().__init__()
        self._qudi_main = qudi_main
        self._name = name
        self._base = base
        self._configuration = configuration

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
    def connected_modules(self) -> FrozenSet[object]:
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


class LocalManagedModule(ManagedModule):
    """
    """
    def __init__(self, qudi_main, name: str, base: ModuleBase, configuration: Mapping[str, Any]):
        super().__init__(qudi_main, name, base, configuration)
        # Sort out configuration
        mod_stub, self._class = configuration['module.Class'].rsplit('.', 1)
        self._module = f'qudi.{base.value}.{mod_stub}'
        self._allow_remote = configuration['allow_remote']
        self._options = configuration['options']
        self._connect_cfg = configuration['connect']
        self._appdata_path =
        # Module control
        self._instance = None
        self._fsm = ModuleStateMachine()
        self._connected_modules = frozenset()
        self.__activating = False
        self.__deactivating = False

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
        return True

    @property
    def url(self) -> str:
        return self._module

    @property
    def instance(self) -> Base:
        return self._instance

    @property
    def state(self) -> ModuleState:
        return ModuleState(self._fsm.state)

    @property
    def has_app_data(self) -> bool:
        return os.path.isfile(self._appdata_path)

    def clear_app_data(self) -> None:
        try:
            os.remove(self._appdata_path)
        except OSError:
            pass

    def activate(self) -> None:
        self._fsm.activate()

    def deactivate(self) -> None:
        self._fsm.deactivate()

    def reload(self) -> None:
        self._fsm.deactivate()
        # reload
        self._fsm.activate()

    def lock(self) -> None:
        raise NotImplementedError

    def unlock(self) -> None:
        raise NotImplementedError


class RemoteManagedModule(ManagedModule):
    """
    """
    def __init__(self, qudi_main, name: str, base: ModuleBase, configuration: Mapping[str, Any]):
        super().__init__(qudi_main, name, base, configuration)
        # Sort out configuration
        self._native_name = configuration['native_module_name']
        self._address = configuration['address']
        self._port = configuration['port']
        self._certfile = configuration['certfile']
        self._keyfile = configuration['keyfile']
        self._url = f'{self._address}:{self._port:d}:{self._native_name}'

    @property
    def url(self) -> str:
        return self._url

    @property
    def instance(self) -> Base:


    @property
    def state(self) -> ModuleState:
        return ModuleState(self._fsm.state)

    @property
    def has_app_data(self) -> bool:

    def clear_app_data(self) -> None:

    def activate(self) -> None:

    def deactivate(self) -> None:

    def reload(self) -> None:

    def set_busy(self) -> None:

    def set_idle(self) -> None:
