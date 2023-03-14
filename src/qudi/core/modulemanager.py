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

import importlib
import weakref

from typing import FrozenSet, Mapping, Any, Union, MutableMapping, Dict, Optional, List, Tuple

import rpyc
from PySide2 import QtCore
from abc import abstractmethod
from dataclasses import dataclass

from qudi.util.mutex import Mutex
from qudi.util.network import RpycByValueProxy, netobtain, netdeliver
from qudi.util.helpers import call_slot_from_native_thread, called_from_native_thread
from qudi.core.logger import get_logger
from qudi.core.servers import connect_to_remote_module_server
from qudi.core.meta import ABCQObject
from qudi.core.module import Base, RemoteProxy, ModuleStateFileHandler
from qudi.core.module import ModuleState, ModuleBase, ModuleStateError
from qudi.core.config.validator import validate_local_module_config, validate_remote_module_config
from qudi.core.config.validator import ValidationError


logger = get_logger(__name__)


@dataclass(frozen=True)
class ModuleInfo:
    base: ModuleBase
    state: ModuleState
    has_appdata: bool


class ModuleManager(QtCore.QObject):
    """
    """
    _instance = None  # Only class instance created will be stored here as weakref
    _remote_connections: Dict[str, Tuple[rpyc.Connection, List[str]]] = dict()

    sigModuleStateChanged = QtCore.Signal(str, ModuleInfo)
    sigManagedModulesChanged = QtCore.Signal(dict)  # {str: ModuleInfo, ...}

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
        self._thread_lock = Mutex()
        self._qudi_main = qudi_main
        self._modules = dict()

    def __del__(self):
        for conn, _ in self._remote_connections.values():
            conn.close()
            self._remote_connections.clear()

    def __contains__(self, item: str) -> bool:
        return item in self._modules

    @property
    def module_count(self) -> int:
        return len(self._modules)

    @property
    def module_names(self) -> List[str]:
        return list(self._modules)

    @property
    def modules_info(self) -> Dict[str, ModuleInfo]:
        return {name: mod.info for name, mod in self._modules.items()}

    @property
    def module_instances(self) -> Dict[str, Base]:
        return {name: mod.instance for name, mod in self._modules.items()}

    def get_module_info(self, name: str) -> ModuleInfo:
        with self._thread_lock:
            try:
                module = self._modules[name]
            except KeyError:
                raise KeyError(f'No module named "{name}" found in managed qudi modules. '
                               f'Can not check for module info.') from None
            return module.info

    def get_module_state(self, name: str) -> ModuleState:
        with self._thread_lock:
            try:
                module = self._modules[name]
            except KeyError:
                raise KeyError(f'No module named "{name}" found in managed qudi modules. '
                               f'Can not check for module state.') from None
            return module.state

    def get_module_has_appdata(self, name: str) -> bool:
        with self._thread_lock:
            try:
                module = self._modules[name]
            except KeyError:
                raise KeyError(f'No module named "{name}" found in managed qudi modules. '
                               f'Can not check for module appdata.') from None
            return module.has_appdata

    def get_module_instance(self, name: str) -> Base:
        with self._thread_lock:
            try:
                module = self._modules[name]
            except KeyError:
                raise KeyError(f'No module named "{name}" found in managed qudi modules. '
                               f'Can not get module instance.') from None
            return module.instance

    def remove_module(self,
                      name: str,
                      ignore_missing: Optional[bool] = False,
                      emit_change: Optional[bool] = True) -> None:
        if not called_from_native_thread(self):
            raise RuntimeError(f'"remove_module" can only be called from main/GUI thread')
        with self._thread_lock:
            return self._remove_module(name, ignore_missing, emit_change)

    def _remove_module(self, name: str, ignore_missing: bool, emit_change: bool) -> None:
        try:
            self._deactivate_module(name)
            del self._modules[name]
            self._remove_module_remote_connection(module_name=name)
        except KeyError:
            if not ignore_missing:
                raise
        else:
            try:
                self._qudi_main.remote_modules_server.remove_shared_module(name)
            except AttributeError:
                pass
        finally:
            if emit_change:
                self.sigManagedModulesChanged.emit(self.modules_info)

    def add_module(self,
                   name: str,
                   base: Union[str, ModuleBase],
                   configuration: Mapping[str, Any],
                   allow_overwrite: Optional[bool] = False,
                   emit_change: Optional[bool] = True) -> None:
        if not called_from_native_thread(self):
            raise RuntimeError(f'"add_module" can only be called from main/GUI thread')
        with self._thread_lock:
            return self._add_module(name, base, configuration, allow_overwrite, emit_change)

    def _add_module(self,
                    name: str,
                    base: Union[str, ModuleBase],
                    configuration: Mapping[str, Any],
                    allow_overwrite: bool,
                    emit_change: bool) -> None:

        if name in self._modules:
            if allow_overwrite:
                self._remove_module(name, ignore_missing=True, emit_change=emit_change)
            else:
                raise KeyError(f'Module with name "{name}" already registered')
        is_remote = self._is_remote_module(configuration)
        if is_remote:
            try:
                connection = self._add_module_remote_connection(module_name=name,
                                                                host=configuration['address'],
                                                                port=configuration['port'],
                                                                certfile=configuration['certfile'],
                                                                keyfile=configuration['keyfile'])
                module = RemoteManagedModule(name=name,
                                             base=base,
                                             qudi_main=self._qudi_main,
                                             native_name=configuration['native_module_name'],
                                             host=configuration['address'],
                                             port=configuration['port'],
                                             connection=connection)
            except Exception:
                self._remove_module_remote_connection(module_name=name)
                raise
        else:
            module = LocalManagedModule(name=name,
                                        base=base,
                                        qudi_main=self._qudi_main,
                                        module_class_cfg=configuration['module.Class'],
                                        allow_remote=configuration['allow_remote'],
                                        options_cfg=configuration['options'],
                                        connect_cfg=configuration['connect'])
        module.sigStateChanged.connect(self.sigModuleStateChanged)
        self._modules[name] = module
        if not is_remote and module.allow_remote:
            try:
                self._qudi_main.remote_modules_server.share_module(name)
            except AttributeError:
                pass
        if emit_change:
            self.sigManagedModulesChanged.emit(self.modules_info)

    @QtCore.Slot(str)
    def activate_module(self, name: str) -> None:
        with self._thread_lock:
            return self._activate_module(name)

    def _activate_module(self, name: str) -> None:
        try:
            module = self._modules[name]
        except KeyError:
            raise KeyError(f'No module named "{name}" found in managed qudi modules. '
                           f'Module activation aborted.') from None
        if call_slot_from_native_thread(module, 'activate', blocking=True):
            module.activate()

    @QtCore.Slot(str)
    def deactivate_module(self, name: str) -> None:
        with self._thread_lock:
            return self._deactivate_module(name)

    def _deactivate_module(self, name: str) -> None:
        try:
            module = self._modules[name]
        except KeyError:
            raise KeyError(f'No module named "{name}" found in managed qudi modules. '
                           f'Module deactivation aborted.') from None
        if call_slot_from_native_thread(module, 'deactivate', blocking=True):
            module.deactivate()

    @QtCore.Slot(str)
    def reload_module(self, name: str) -> None:
        with self._thread_lock:
            return self._reload_module(name)

    def _reload_module(self, name: str) -> None:
        try:
            module = self._modules[name]
        except KeyError:
            raise KeyError(f'No module named "{name}" found in managed qudi modules. '
                           f'Module reload aborted.') from None
        if call_slot_from_native_thread(module, 'reload', blocking=True):
            module.reload()

    @QtCore.Slot(str)
    def clear_module_appdata(self, name: str) -> None:
        with self._thread_lock:
            try:
                module = self._modules[name]
            except KeyError:
                raise KeyError(f'No module named "{name}" found in managed qudi modules. '
                               f'Unable to clear module appdata.') from None
            module.clear_appdata()

    @QtCore.Slot()
    def activate_all_modules(self) -> None:
        if call_slot_from_native_thread(self, 'activate_all_modules', blocking=True):
            with self._thread_lock:
                for module in self._modules.values():
                    try:
                        module.activate()
                    except:
                        logger.exception('Module activation failed. Activating all modules will '
                                         'continue regardless.')

    @QtCore.Slot()
    def deactivate_all_modules(self) -> None:
        if call_slot_from_native_thread(self, 'deactivate_all_modules', blocking=True):
            with self._thread_lock:
                for module in self._modules.values():
                    try:
                        module.deactivate()
                    except:
                        logger.exception('Module deactivation failed. Deactivating all modules '
                                         'will continue regardless.')

    @QtCore.Slot()
    def remove_all_modules(self) -> None:
        if not called_from_native_thread(self):
            raise RuntimeError(f'"remove_all_modules" can only be called from main/GUI thread')
        with self._thread_lock:
            for module_name in list(self._modules):
                self._remove_module(module_name, ignore_missing=True, emit_change=False)
            self.sigManagedModulesChanged.emit(self.modules_info)

    @staticmethod
    def _is_remote_module(configuration: Mapping[str, Any]) -> bool:
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

    def _add_module_remote_connection(self,
                                      module_name: str,
                                      host: str,
                                      port: int,
                                      certfile: Optional[str] = None,
                                      keyfile: Optional[str] = None) -> rpyc.Connection:
        url = f'{host}:{port:d}:{certfile}:{keyfile}'
        try:
            conn, mod_list = self._remote_connections[url]
        except KeyError:
            conn = connect_to_remote_module_server(host=host,
                                                   port=port,
                                                   certfile=certfile,
                                                   keyfile=keyfile)
            mod_list = list()
            self._remote_connections[url] = (conn, mod_list)
        if module_name not in mod_list:
            mod_list.append(module_name)
        return conn

    def _remove_module_remote_connection(self, module_name: str) -> None:
        terminate = None
        for url, (conn, mod_list) in self._remote_connections.items():
            if module_name in mod_list:
                mod_list.remove(module_name)
                if len(mod_list) == 0:
                    terminate = url
                break
        if terminate is not None:
            conn, mod_list = self._remote_connections.pop(terminate)
            conn.close()


class ManagedModule(ABCQObject):
    """ Object representing a wrapper for a qudi module (gui, logic or hardware) to be managed by
    the ModuleManager object. Contains status properties and handles initialization, state
    transitions and connection of the module.
    """
    sigStateChanged = QtCore.Signal(str, ModuleInfo)

    _managed_modules = weakref.WeakValueDictionary()

    def __new__(cls, name: str, *args, **kwargs):
        obj = super().__new__(cls)
        cls._managed_modules[name] = obj
        return obj

    def __init__(self,
                 name: str,
                 base: Union[str, ModuleBase],
                 qudi_main: 'Qudi'):
        if not isinstance(name, str):
            raise TypeError('Module name must be str type')
        if len(name) < 1:
            raise ValueError('Module name must be non-empty string')
        super().__init__(parent=qudi_main.module_manager)
        self._name = name
        self._base = ModuleBase(base)
        self._qudi_main = qudi_main

    @property
    @abstractmethod
    def url(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def has_appdata(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def state(self) -> ModuleState:
        raise NotImplementedError

    @property
    @abstractmethod
    def instance(self) -> Union[None, Base]:
        raise NotImplementedError

    @abstractmethod
    def clear_appdata(self) -> None:
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
    def info(self) -> ModuleInfo:
        return ModuleInfo(self.base, self.state, self.has_appdata)

    @property
    def is_active(self) -> bool:
        return self.state != ModuleState.DEACTIVATED

    @property
    def is_locked(self) -> bool:
        return self.state == ModuleState.LOCKED

    @property
    def required_module_names(self) -> FrozenSet[str]:
        """ Overwrite by subclass if needed """
        return frozenset()

    @property
    def module_thread_name(self) -> str:
        """ Generic qudi module thread name used by the ThreadManager in case the module is
        running in its own thread
        """
        return f'mod-{self.base.value}-{self.name}'

    @property
    def active_dependent_modules(self) -> Dict[str, 'ManagedModule']:
        return {mod_name: mod for mod_name, mod in self._managed_modules.items() if
                (self.name in mod.required_module_names) and mod.is_active}

    @property
    def required_modules(self) -> Dict[str, 'ManagedModule']:
        return {mod_name: mod for mod_name, mod in self._managed_modules.items() if
                mod_name in self.required_module_names}

    def _activate_required_modules(self) -> Dict[str, Base]:
        target_instances = dict()
        for mod_name, module in self.required_modules.items():
            module.activate()
            target_instances[mod_name] = module.instance
        return target_instances

    def _deactivate_dependent_modules(self) -> None:
        for _, module in self.active_dependent_modules.items():
            module.deactivate()

    def _connect_module_signals(self) -> None:
        instance = self.instance
        instance.sigModuleStateChanged.connect(self._state_changed)
        instance.sigModuleAppDataChanged.connect(self._appdata_changed)

    def _disconnect_module_signals(self) -> None:
        instance = self.instance
        instance.sigModuleAppDataChanged.disconnect()
        instance.sigModuleStateChanged.disconnect()

    def _move_instance_to_thread(self) -> None:
        thread_manager = self._qudi_main.thread_manager
        thread = thread_manager.get_new_thread(self.module_thread_name)
        self.instance.moveToThread(thread)
        thread.start()

    def _join_instance_thread(self) -> None:
        thread_name = self.module_thread_name
        thread_manager = self._qudi_main.thread_manager
        call_slot_from_native_thread(self.instance, 'move_to_main_thread', blocking=True)
        thread_manager.quit_thread(thread_name)
        thread_manager.join_thread(thread_name)

    def _activate_instance_threaded(self) -> None:
        call_slot_from_native_thread(self.instance.module_state, 'activate', blocking=True)
        # Check if activation has been successful
        if not self.is_active:
            raise ModuleStateError(f'Error during threaded activation of module "{self.url}"')

    def _info_changed(self,
                      state: Optional[ModuleState] = None,
                      has_appdata: Optional[bool] = None) -> None:
        if state is None:
            state = self.state
        if has_appdata is None:
            has_appdata = self.has_appdata
        self.sigStateChanged.emit(self.name, ModuleInfo(self.base, state, has_appdata))

    @QtCore.Slot(ModuleState)
    def _state_changed(self, state: ModuleState) -> None:
        self._info_changed(state=state)

    @QtCore.Slot(bool)
    def _appdata_changed(self, has_appdata: bool) -> None:
        self._info_changed(has_appdata=has_appdata)


class LocalManagedModule(ManagedModule):
    """
    """
    def __init__(self,
                 name: str,
                 base: ModuleBase,
                 qudi_main: 'Qudi',
                 module_class_cfg: str,
                 allow_remote: Optional[bool] = None,
                 options_cfg: Optional[Mapping[str, Any]] = None,
                 connect_cfg: Optional[Mapping[str, str]] = None):
        super().__init__(name, base, qudi_main)
        # Configuration
        self._module_url, self._class_name = module_class_cfg.rsplit('.', 1)
        self._module_url = f'qudi.{self.base.value}.{self._module_url}'
        self._allow_remote = bool(allow_remote)
        self._options = dict() if options_cfg is None else options_cfg
        self._connections = dict() if connect_cfg is None else connect_cfg

        # Circular recursion fail-saves
        self.__activating = False
        self.__deactivating = False
        # Import qudi module class
        self._module = None
        self._class = None
        self._instance = None
        self.__import_module_class()
        # App status handling
        self._appdata_handler = ModuleStateFileHandler(self.name, self._class)

    def __import_module_class(self) -> None:
        try:
            # (re-)import module
            try:
                if self._module is None:
                    self._module = importlib.import_module(self._module_url)
                else:
                    importlib.reload(self._module)
            except ImportError:
                raise
            except Exception as err:
                raise ImportError(f'Unable to (re-)import module "{self._module_url}"') from err

            # Get class from module
            try:
                self._class = getattr(self._module, self._class_name)
            except AttributeError:
                raise ImportError(
                    f'No class "{self._class_name}" found in module "{self._module_url}"'
                ) from None

            # Check if imported class is a valid qudi module class
            if not (isinstance(self._class, type) and issubclass(self._class, Base)):
                raise TypeError(
                    f'Qudi module class "{self._class.__module__}.{self._class.__name__}" is no '
                    f'subclass of "{Base.__module__}.{Base.__name__}"'
                )
        except Exception:
            self._instance = self._class = None
            raise

    @property
    def url(self) -> str:
        return f'{self._module_url}.{self._class_name}::{self.name}'

    @property
    def has_appdata(self) -> bool:
        return self._appdata_handler.exists

    @property
    def state(self) -> ModuleState:
        try:
            return self.instance.module_state.state
        except AttributeError:
            return ModuleState.DEACTIVATED

    @property
    def instance(self) -> Union[None, Base]:
        return self._instance

    @property
    def required_module_names(self) -> FrozenSet[str]:
        return frozenset(self._connections.values())

    @property
    def allow_remote(self) -> bool:
        return self._allow_remote

    @QtCore.Slot()
    def clear_appdata(self) -> None:
        try:
            self._appdata_handler.clear()
        finally:
            self._appdata_changed(self.has_appdata)

    @QtCore.Slot()
    def activate(self) -> None:
        if self.__activating:
            return
        if self.is_active:
            if self.base == ModuleBase.GUI:
                self.instance.show()
            return
        self.__activating = True
        try:
            logger.info(f'Activating module "{self.url}" ...')
            required_instances = self._activate_required_modules()
            connections = {
                conn: required_instances[target] for conn, target in self._connections.items()
            }
            self._instantiate_module_class(connections)
            if self._class.module_threaded:
                try:
                    self._move_instance_to_thread()
                    self._activate_instance_threaded()
                except Exception:
                    self._join_instance_thread()
                    raise
            else:
                self.instance.module_state.activate()
            self._connect_module_signals()
        except Exception:
            self._instance = None
            raise
        else:
            logger.info(f'Module "{self.url}" successfully activated.')
        finally:
            self.__activating = False
            self._info_changed()
            QtCore.QCoreApplication.instance().processEvents()

    def _instantiate_module_class(self, connections: MutableMapping[str, Base]) -> None:
        """ Try to instantiate the imported qudi module class """
        try:
            self._instance = self._class(qudi_main=self._qudi_main,
                                         name=self.name,
                                         options=self._options,
                                         connections=connections)
        except Exception as err:
            self._instance = None
            raise RuntimeError(f'Error during __init__ of qudi module "{self.url}".') from err

    @QtCore.Slot()
    def deactivate(self) -> None:
        if self.__deactivating or not self.is_active:
            return
        self.__deactivating = True
        try:
            logger.info(f'Deactivating module "{self.url}" ...')
            try:
                self._deactivate_dependent_modules()
            finally:
                try:
                    self._disconnect_module_signals()
                finally:
                    if self._class.module_threaded:
                        try:
                            QtCore.QMetaObject.invokeMethod(self.instance.module_state,
                                                            'deactivate',
                                                            QtCore.Qt.BlockingQueuedConnection)
                        finally:
                            self._join_instance_thread()
                    else:
                        self.instance.module_state.deactivate()
        finally:
            try:
                self._instance = None
                logger.info(f'Module "{self.url}" successfully deactivated.')
            finally:
                self.__deactivating = False
                self._info_changed()
                QtCore.QCoreApplication.instance().processEvents()

    @QtCore.Slot()
    def reload(self) -> None:
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
            self.deactivate()
        else:
            active_dependent_modules = set()
        logger.info(f'Reloading module "{self.url}" with re-import.')
        self.__import_module_class()
        if was_active:
            self.activate()
            for module in active_dependent_modules:
                module.activate()


class RemoteManagedModule(ManagedModule):
    """
    """
    def __init__(self,
                 name: str,
                 base: ModuleBase,
                 qudi_main: 'Qudi',
                 native_name: str,
                 host: str,
                 port: int,
                 connection: rpyc.Connection):
        super().__init__(name, base, qudi_main)
        self._native_name = native_name
        self.__connection = connection
        self._instance = None
        self._url = f'{host}:{port:d}/{self._native_name}'

        # Circular recursion fail-saves
        self.__activating = False
        self.__deactivating = False
        # state cache
        self.__cached_state = ModuleState.DEACTIVATED
        self.__cached_has_appdata = False

    @property
    def url(self) -> str:
        return self._url

    @property
    def has_appdata(self) -> bool:
        self.update_module_info()
        return self.__cached_has_appdata

    @property
    def state(self) -> ModuleState:
        self.update_module_info()
        return self.__cached_state

    @property
    def info(self) -> ModuleInfo:
        self.update_module_info()
        return ModuleInfo(self.base, self.__cached_state, self.__cached_has_appdata)

    @property
    def instance(self) -> Union[None, Base]:
        return self._instance

    @QtCore.Slot()
    def clear_appdata(self) -> None:
        try:
            self.__connection.root.clear_module_appdata(self._native_name)
        finally:
            self.update_module_info()

    @QtCore.Slot()
    def activate(self) -> None:
        if self.__activating or self.is_active:
            return
        self.__activating = True
        try:
            logger.info(f'Activating remote module "{self.url}" ...')
            self._instantiate_module_proxy()
            self.instance.module_state.activate()
            self._connect_module_signals()
        except Exception:
            self._instance = None
            raise
        else:
            logger.info(f'Remote module "{self.url}" successfully activated.')
        finally:
            self.__activating = False
            self.update_module_info()
            QtCore.QCoreApplication.instance().processEvents()

    def _instantiate_module_proxy(self):
        try:
            self._instance = RemoteProxy(qudi_main=self._qudi_main,
                                         name=self.name,
                                         native_name=self._native_name,
                                         connection=self.__connection)
        except Exception as err:
            self._instance = None
            raise RuntimeError(
                f'Error during RemoteProxy.__init__ of qudi remote module "{self.url}".'
            ) from err

    @QtCore.Slot()
    def deactivate(self) -> None:
        if self.__deactivating or not self.is_active:
            return
        self.__deactivating = True
        try:
            logger.info(f'Deactivating module "{self.url}" ...')
            try:
                self._deactivate_dependent_modules()
            finally:
                try:
                    self._disconnect_module_signals()
                finally:
                    self.instance.module_state.deactivate()
        finally:
            try:
                self._instance = None
                logger.info(f'Module "{self.url}" successfully deactivated.')
            finally:
                self.__deactivating = False
                self._info_changed()
                QtCore.QCoreApplication.instance().processEvents()

    @QtCore.Slot()
    def reload(self) -> None:
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
            self.deactivate()
        else:
            active_dependent_modules = set()
        logger.info(f'Reloading remote module "{self.url}" with re-import.')
        self.__connection.root.reload_module(self._native_name)
        if was_active:
            self.activate()
            for module in active_dependent_modules:
                module.activate()

    @QtCore.Slot()
    def update_module_info(self) -> None:
        has_appdata = self.__connection.root.get_module_has_appdata(self._native_name)
        try:
            state = ModuleState(self._instance.module_state.state.value)
        except AttributeError:
            state = ModuleState.DEACTIVATED
        state_changed = self.__cached_state != state
        if state_changed or (self.__cached_has_appdata != has_appdata):
            self.__cached_state = state
            self.__cached_has_appdata = has_appdata
            if state == ModuleState.DEACTIVATED:
                self._instance = None
            self.sigStateChanged.emit(
                ModuleInfo(self.base, self.__cached_state, self.__cached_has_appdata)
            )
