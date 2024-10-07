# -*- coding: utf-8 -*-
"""
This file contains the Qudi Manager class.

Copyright (c) 2021-2024, the qudi developers. See the AUTHORS.md file at the top-level directory of
this distribution and on <https://github.com/Ulm-IQO/qudi-core/>

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

__all__ = ['ModuleManager', 'ManagedModule', 'LocalManagedModule', 'RemoteManagedModule']

import weakref
import rpyc

from typing import FrozenSet, Dict, Union, Optional, Mapping, Callable, List
from typing import Any, final
from PySide2 import QtCore
from abc import abstractmethod

from qudi.util.helpers import call_slot_from_native_thread, current_is_main_thread
from qudi.util.mutex import Mutex
from qudi.util.network import connect_to_remote_module_server
from qudi.core.logger import get_logger
from qudi.core.object import ABCQObjectMixin
from qudi.core.module import Base
from qudi.core.module import ModuleStateError, ModuleState, ModuleBase
from qudi.core.threadmanager import ThreadManager
from qudi.core.module import module_url, import_module_type, module_thread_name
from qudi.core.config.validator import validate_local_module_config, validate_remote_module_config
from qudi.core.config.validator import ValidationError, validate_module_name


_logger = get_logger(__name__)


class ManagedModule(ABCQObjectMixin, QtCore.QObject):
    """ Object representing a wrapper for a qudi module (gui, logic or hardware) to be managed by
    the ModuleManager object. Contains status properties and handles initialization, state
    transitions and connection of the module.
    Use of ManagedModule objects is generally not thread safe. They should ideally only ever be
    handled indirectly via the thread-safe ModuleManager.
    """
    sigStateChanged = QtCore.Signal(ModuleState)  # current module state
    sigAppDataChanged = QtCore.Signal(bool)  # has_appdata flag

    def __init__(self,
                 name: str,
                 base: ModuleBase,
                 config: Mapping[str, Any],
                 parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        validate_module_name(name)
        self._name = name
        self._base = base
        self._config = config
        self._thread_name = module_thread_name(name=name, base=base)
        self._allow_remote = self._config.get('allow_remote', False)
        if self._allow_remote and (self._base == ModuleBase.GUI):
            self._allow_remote = False
            _logger.warning(f'GUI modules can not be shared as remote modules')
        self._required_modules = frozenset(
            target for target in self._config.get('connect', dict()).values()
        )
        self.__has_appdata_cache = False
        self.__state_cache = ModuleState.DEACTIVATED

    @property
    @abstractmethod
    def url(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def instance(self) -> Union[None, Base]:
        raise NotImplementedError

    @abstractmethod
    def clear_appdata(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def activate(self, conn_targets: Mapping[str, Base]) -> None:
        raise NotImplementedError

    @abstractmethod
    def deactivate(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def reload(self, conn_targets: Mapping[str, Base]) -> None:
        raise NotImplementedError

    def check_module_state(self) -> None:
        """ Override in subclass to allow external polling of "state" and "has_appdata" from the
        module instance
        """
        pass

    @property
    @final
    def state(self) -> ModuleState:
        """ The current module state enum """
        return self.__state_cache

    @property
    @final
    def has_appdata(self) -> bool:
        """ Flag indicating if module appdata exists """
        return self.__has_appdata_cache

    @property
    @final
    def name(self) -> str:
        """ Configured module name """
        return self._name

    @property
    @final
    def base(self) -> ModuleBase:
        """ Module base type enum """
        return self._base

    @property
    @final
    def required_modules(self) -> FrozenSet[str]:
        """ Configured target module names to connect to this module """
        return self._required_modules

    @property
    @final
    def thread_name(self) -> str:
        """ Generic qudi module thread name used by the ThreadManager in case the module is
        running in its own thread
        """
        return self._thread_name

    @property
    @final
    def allow_remote(self) -> bool:
        """ Flag indicating if the module is allowed to be shared outside of localhost.
        False by default if not configured or if it is a remote module.
        """
        return self._allow_remote

    @final
    def _update_appdata(self, has_appdata: bool) -> None:
        if has_appdata != self.__has_appdata_cache:
            self.__has_appdata_cache = has_appdata
            self.sigAppDataChanged.emit(self.__has_appdata_cache)

    @final
    def _update_state(self, state: ModuleState) -> None:
        if state != self.__state_cache:
            self.__state_cache = state
            self.sigStateChanged.emit(self.__state_cache)


class LocalManagedModule(ManagedModule):
    """ ManagedModule specialization for local modules """

    def __init__(self,
                 name: str,
                 base: ModuleBase,
                 config: Mapping[str, Any],
                 parent: Optional[QtCore.QObject] = None):
        validate_local_module_config(config)
        super().__init__(name, base, config, parent)

        # Configuration
        self._module_url, self._class_name = config['module.Class'].rsplit('.', 1)
        if not self._module_url.startswith('qudi.'):
            if self._module_url.startswith(tuple(f'{b.value}.' for b in ModuleBase)):
                self._module_url = f'qudi.{self._module_url}'
            else:
                self._module_url = f'qudi.{self.base.value}.{self._module_url}'
        self._url = module_url(self._module_url, self._class_name, self.name)
        self._options = config.get('options', dict())
        self._connections = config.get('connect', dict())

        # Import qudi module class
        self._module_class = import_module_type(module=self._module_url,
                                                cls=self._class_name,
                                                base=self.base,
                                                reload=False)
        self._instance: Union[None, Base] = None
        # Initialize appdata file handler
        self._appdata_handler = self._module_class.appdata_handler(self.name)

        self._update_appdata(self._appdata_handler.exists)
        self._update_state(ModuleState.DEACTIVATED)

    @property
    def url(self) -> str:
        return self._url

    @property
    def instance(self) -> Union[None, Base]:
        return self._instance

    @property
    def is_threaded(self) -> bool:
        return self._module_class.module_threaded

    def clear_appdata(self) -> None:
        self._appdata_handler.clear()
        self._update_appdata(self._appdata_handler.exists)

    def activate(self, conn_targets: Mapping[str, Base]) -> None:
        # Do nothing if already active (except showing the GUI again)
        if self._instance is None:
            _logger.info(f'Activating module "{self.url}" ...')
            try:
                self._instance = self._instantiate_module(required_targets=conn_targets)
                if self.is_threaded:
                    try:
                        self._move_instance_to_thread()
                        self._activate_instance_threaded()
                    except Exception:
                        try:
                            self._join_instance_thread()
                        except:
                            pass
                        raise
                else:
                    self._instance.module_state.activate()
            except Exception:
                self._instance = None
                self._update_state(ModuleState.DEACTIVATED)
                raise
            else:
                self._instance.module_state.sigStateChanged.connect(self._update_state)
                self._update_state(self._instance.module_state.current)
            finally:
                self._update_appdata(self._appdata_handler.exists)
            _logger.info(f'Module "{self.url}" successfully activated.')
        else:
            if self.base == ModuleBase.GUI:
                self._instance.show()
            self._update_state(self._instance.module_state.current)
            self._update_appdata(self._appdata_handler.exists)

    def deactivate(self) -> None:
        if self._instance is None:
            self._update_state(ModuleState.DEACTIVATED)
        else:
            _logger.info(f'Deactivating module "{self.url}" ...')
            try:
                try:
                    self._instance.module_state.sigStateChanged.disconnect()
                except:
                    pass
                if self.is_threaded:
                    try:
                        self._deactivate_instance_threaded()
                    finally:
                        self._join_instance_thread()
                else:
                    self._instance.module_state.deactivate()
            finally:
                self._instance = None
                self._update_state(ModuleState.DEACTIVATED)
                self._update_appdata(self._appdata_handler.exists)
            _logger.info(f'Module "{self.url}" successfully deactivated')

    def reload(self, conn_targets: Mapping[str, Base]) -> None:
        # Remember activation state and restore it afterward
        was_active = self._instance is not None
        if was_active:
            self.deactivate()

        # Re-import module class
        self._module_class = import_module_type(module=self._module_url,
                                                cls=self._class_name,
                                                base=self.base,
                                                reload=True)
        _logger.info(f'Module "{self.url}" reloaded successfully')

        # Re-activate if needed
        if was_active:
            self.activate(conn_targets)

    def _instantiate_module(self, required_targets: Mapping[str, Base]) -> Base:
        """ Try to instantiate the imported qudi module class """
        try:
            connections = {
                conn: required_targets[target] for conn, target in self._connections.items()
            }
            return self._module_class(name=self.name,
                                      options=self._options,
                                      connections=connections)
        except Exception as err:
            raise RuntimeError(f'Error during __init__ of qudi module "{self.url}"') from err

    def _move_instance_to_thread(self) -> None:
        thread = ThreadManager.instance().get_new_thread(self.thread_name)
        self._instance.moveToThread(thread)
        thread.start()

    def _join_instance_thread(self) -> None:
        thread_manager = ThreadManager.instance()
        thread_manager.quit_thread(self.thread_name)
        thread_manager.join_thread(self.thread_name)

    def _activate_instance_threaded(self) -> None:
        # Activate instance in native thread
        call_slot_from_native_thread(self._instance.module_state, 'activate', blocking=True)
        # Check if activation has been successful
        if self._instance.module_state.current == ModuleState.DEACTIVATED:
            raise ModuleStateError(f'Threaded activation of module "{self.url}" failed!')

    def _deactivate_instance_threaded(self) -> None:
        # Activate instance in native thread
        call_slot_from_native_thread(self._instance.module_state, 'deactivate', blocking=True)
        # Check if deactivation has been successful
        if self._instance.module_state.current != ModuleState.DEACTIVATED:
            raise ModuleStateError(f'Threaded deactivation of module "{self.url}" failed!')


class RemoteManagedModule(ManagedModule):
    """ ManagedModule specialization for modules running in a remote qudi instance """

    def __init__(self,
                 name: str,
                 base: ModuleBase,
                 config: Mapping[str, Any],
                 parent: Optional[QtCore.QObject] = None):
        if base == ModuleBase.GUI:
            raise ValueError(f'{ModuleBase.GUI.value} modules can not be configured as remote')
        validate_remote_module_config(config)
        super().__init__(name, base, config, parent)

        self._native_name = config['native_module_name']
        self._host = config['address']
        self._port = config['port']
        self._certfile = config['certfile']
        self._keyfile = config['keyfile']
        self._url = f'{self._host}:{self._port:d}/{self._native_name}'
        self._connection: Union[rpyc.Connection, None] = None

    @property
    def url(self) -> str:
        return self._url

    @property
    def instance(self) -> Union[None, Base]:
        if self._connection is None:
            instance = None
        else:
            instance = self._connection.root.get_module_instance(self._native_name)
        return instance

    def clear_appdata(self) -> None:
        self._update_appdata(False)

    def activate(self, conn_targets: Mapping[str, Base]) -> None:
        if self._connection is None:
            _logger.info(f'Activating remote module "{self.name}" at "{self.url}" ...')
            try:
                try:
                    self._connection = connect_to_remote_module_server(host=self._host,
                                                                       port=self._port,
                                                                       certfile=self._certfile,
                                                                       keyfile=self._keyfile)
                    _logger.debug(
                        f'Connected to RemoteModulesServer on {self._host}:{self._port:d}'
                    )
                except Exception as err:
                    raise ModuleStateError(
                        f'Unable to connect to remote module "{self.name}" at "{self.url}"'
                    ) from err
                try:
                    self._connection.root.get_module_instance(self._native_name)
                except Exception as err:
                    try:
                        self._connection.close()
                    except:
                        pass
                    raise ModuleStateError(
                        f'Unable to activate remote module "{self.name}" at "{self.url}"'
                    ) from err
            except:
                self._connection = None
                raise
            finally:
                self.check_module_state()
            _logger.info(f'Remote module "{self.name}" at "{self.url}" successfully activated')
        else:
            self.check_module_state()

    def deactivate(self) -> None:
        if self._connection is None:
            self.check_module_state()
        else:
            _logger.info(f'Disconnecting remote module "{self.name}" at "{self.url}" ...')
            try:
                self._connection.close()
            finally:
                self._connection = None
                self.check_module_state()
            _logger.info(f'Remote module "{self.name}" at "{self.url}" successfully disconnected.')

    def reload(self, conn_targets: Mapping[str, Base]) -> None:
        if self._connection is not None:
            self.deactivate()
            _logger.info(f'Reconnecting to remote module "{self.name}" at "{self.url}"')
            self.activate(conn_targets)

    def check_module_state(self) -> None:
        if self._connection is None:
            self._update_state(ModuleState.DEACTIVATED)
        else:
            state = ModuleState(self._connection.root.get_module_state(self._native_name).value)
            if state == ModuleState.DEACTIVATED:
                self.deactivate()
            else:
                self._update_state(state)


class ModuleManager(QtCore.QObject):
    """ Main control interface singleton for qudi measurement modules (GUI, logic, hardware).
    Using this object can be considered thread-safe.
    """
    _instance = None  # Only class instance created will be stored here as weakref
    _WATCHDOG_INTERVAL: int = 1000  # milliseconds

    sigStateChanged = QtCore.Signal(ModuleBase, str, ModuleState)  # base, name, state
    sigHasAppdataChanged = QtCore.Signal(ModuleBase, str, bool)  # base, name, has_appdata
    __sigActivateModule = QtCore.Signal(str)  # name
    __sigDeactivateModule = QtCore.Signal(str)  # name
    __sigReloadModule = QtCore.Signal(str)  # name

    _main_gui: Union[None, LocalManagedModule]

    @classmethod
    def instance(cls):
        try:
            return cls._instance()
        except TypeError:
            return None

    def __new__(cls, *args, **kwargs):
        if cls.instance() is not None:
            raise RuntimeError(
                'ModuleManager is a singleton. An instance has already been created in this '
                'process. Please use ModuleManager.instance() instead.'
            )
        obj = super().__new__(cls, *args, **kwargs)
        cls._instance = weakref.ref(obj)
        return obj

    def __init__(self, config: Mapping[str, Any], parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

        self._lock = Mutex()
        self._modules: Dict[str, ManagedModule] = dict()
        self.__modules_pending_deactivation = set()
        self.__modules_pending_activation = set()
        # Remote module state watchdog
        self._remote_watchdog_timer = QtCore.QTimer(self)
        self._remote_watchdog_timer.setInterval(self._WATCHDOG_INTERVAL)
        self._remote_watchdog_timer.setSingleShot(True)
        self._remote_watchdog_timer.timeout.connect(self._remote_watchdog,
                                                    QtCore.Qt.QueuedConnection)
        # Apply module configuration
        for module_base in ModuleBase:
            for module_name, module_config in config.get(module_base.value, dict()).items():
                try:
                    self._modules[module_name] = self.__init_module(name=module_name,
                                                                    base=module_base,
                                                                    config=module_config)
                except Exception:
                    _logger.exception(
                        f'Failed to configure {module_base.value} module "{module_name}"'
                    )
        # Configure main GUI if necessary
        module_config = config['global'].get('main_gui', None)
        if module_config:
            self._main_gui = self.__init_module(name='__maingui__',
                                                base=ModuleBase.GUI,
                                                config=module_config)
        else:
            self._main_gui = None
        # Connect internal signals
        self.__sigActivateModule.connect(self.activate_module, QtCore.Qt.BlockingQueuedConnection)
        self.__sigDeactivateModule.connect(self.deactivate_module,
                                           QtCore.Qt.BlockingQueuedConnection)
        self.__sigReloadModule.connect(self.reload_module, QtCore.Qt.BlockingQueuedConnection)

    @property
    def has_main_gui(self) -> bool:
        return self._main_gui is not None

    @property
    def module_names(self) -> List[str]:
        return list(self._modules)

    def activate_main_gui(self) -> None:
        """ Recursive activation of the main_gui module and all the modules it depends on """
        if not current_is_main_thread():
            raise RuntimeError('Main GUI can only be activated from main thread')
        if not self.has_main_gui:
            raise RuntimeError('No main GUI configured')
        if '__maingui__' not in self.__modules_pending_activation:
            with self._lock:
                try:
                    conn_targets = dict()
                    self.__modules_pending_activation.add('__maingui__')
                    for required in self._main_gui.required_modules:
                        self._activate_module(required)
                        conn_targets[required] = self._modules[required].instance
                    self._main_gui.activate(conn_targets)
                finally:
                    self.__modules_pending_activation.clear()


    def deactivate_main_gui(self) -> None:
        if not current_is_main_thread():
            raise RuntimeError('Main GUI can only be deactivated from main thread')
        if not self.has_main_gui:
            raise RuntimeError('No main GUI configured')
        if '__maingui__' not in self.__modules_pending_deactivation:
            with self._lock:
                try:
                    self.__modules_pending_deactivation.add('__maingui__')
                    self._main_gui.deactivate()
                finally:
                    self.__modules_pending_deactivation.clear()

    def clear_main_gui_appdata(self) -> None:
        if not self.has_main_gui:
            raise RuntimeError('No main GUI configured')
        self._main_gui.clear_appdata()

    def activate_module(self, name: str) -> None:
        if name not in self.__modules_pending_activation:
            if current_is_main_thread():
                with self._lock:
                    try:
                        self._activate_module(name=name)
                    finally:
                        self.__modules_pending_activation.clear()
            else:
                self.__sigActivateModule.emit(name)

    def _activate_module(self, name: str) -> None:
        """ Recursive activation of the requested module and all the modules it depends on """
        if name not in self.__modules_pending_activation:  # Prevent circular recursion
            module = self._get_module(name)
            self.__modules_pending_activation.add(name)
            try:
                conn_targets = dict()
                for required in module.required_modules:
                    self._activate_module(required)
                    conn_targets[required] = self._modules[required].instance
                module.activate(conn_targets)
            finally:
                self.__modules_pending_activation.remove(name)

    def deactivate_module(self, name: str) -> None:
        if name not in self.__modules_pending_deactivation:
            if current_is_main_thread():
                with self._lock:
                    try:
                        self._deactivate_module(name=name)
                    finally:
                        self.__modules_pending_deactivation.clear()
            else:
                self.__sigDeactivateModule.emit(name)

    def _deactivate_module(self, name: str) -> None:
        """ Recursive deactivation of the requested module and all the modules that depend on it """
        if name not in self.__modules_pending_deactivation:  # Prevent circular recursion
            module = self._get_module(name)
            if module.state != ModuleState.DEACTIVATED:
                self.__modules_pending_deactivation.add(name)
                try:
                    for dep_name, dep_module in self._modules.items():
                        if name in dep_module.required_modules:
                            self._deactivate_module(dep_name)
                    module.deactivate()
                finally:
                    self.__modules_pending_deactivation.remove(name)

    def reload_module(self, name: str) -> None:
        if current_is_main_thread():
            with self._lock:
                self._get_module_by_name(name).reload()
        else:
            self.__sigReloadModule.emit(name)

    def clear_module_appdata(self, name: str) -> None:
        with self._lock:
            self._get_module(name).clear_appdata()

    def has_appdata(self, name: str) -> bool:
        return self._get_module(name).has_appdata

    def module_state(self, name: str) -> ModuleState:
        return self._get_module(name).state

    def module_base(self, name: str) -> ModuleBase:
        return self._get_module(name).base

    def allow_remote(self, name: str) -> bool:
        return self._get_module(name).allow_remote

    def is_remote(self, name: str) -> bool:
        return isinstance(self._get_module(name), RemoteManagedModule)

    def get_module_instance(self, name: str) -> Base:
        if current_is_main_thread():
            with self._lock:
                self._activate_module(name=name)
                instance = self._get_module(name).instance
        else:
            self.__sigActivateModule.emit(name)
            instance = self._get_module(name).instance
        return instance

    def get_active_module_instances(self) -> Dict[str, Base]:
        with self._lock:
            return {name: mod.instance for name, mod in self._modules.items() if
                    mod.state != ModuleState.DEACTIVATED}

    @QtCore.Slot()
    def activate_all_modules(self) -> None:
        if current_is_main_thread():
            with self._lock:
                for name in self._modules:
                    self._activate_module(name=name)
        else:
            call_slot_from_native_thread(self, 'activate_all_modules', True)

    @QtCore.Slot()
    def deactivate_all_modules(self) -> None:
        if current_is_main_thread():
            with self._lock:
                for name in self._modules:
                    self._deactivate_module(name=name)
        else:
            call_slot_from_native_thread(self, 'deactivate_all_modules', True)

    def clear_all_appdata(self) -> None:
        with self._lock:
            for module in self._modules.values():
                module.clear_appdata()

    def _get_module(self, name: str) -> ManagedModule:
        try:
            return self._modules[name]
        except KeyError:
            raise KeyError(f'No module with name "{name}" configured') from None

    def _remote_watchdog(self) -> None:
        with self._lock:
            for module in self._modules.values():
                module.check_module_state()
            self._remote_watchdog_timer.start()

    def __init_module(self,
                      name: str,
                      base: ModuleBase,
                      config: Mapping[str, Any]) -> ManagedModule:
        try:
            module = LocalManagedModule(name=name, base=base, config=config, parent=self)
        except ValidationError:
            module = RemoteManagedModule(name=name, base=base, config=config, parent=self)
        if name != '__maingui__':
            module.sigStateChanged.connect(self.__get_state_updated_cb(base, name))
            module.sigAppDataChanged.connect(self.__get_appdata_updated_cb(base, name))
        return module

    def __get_state_updated_cb(self,
                               base: ModuleBase,
                               name: str) -> Callable[[ModuleState], None]:

        def state_updated(state: ModuleState) -> None:
           self.sigStateChanged.emit(base, name, state)

        return state_updated

    def __get_appdata_updated_cb(self, base: ModuleBase, name: str) -> Callable[[bool], None]:

        def appdata_updated(has_appdata: bool) -> None:
            self.sigHasAppdataChanged.emit(base, name, has_appdata)

        return appdata_updated
