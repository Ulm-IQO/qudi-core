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

import importlib
import weakref
import rpyc

from typing import FrozenSet, Dict, Final, Union, Optional, Tuple, Type, Mapping, Callable, List
from typing import Any, final
from types import ModuleType
from PySide2 import QtCore
from abc import abstractmethod

from qudi.util.paths import get_module_appdata_path
from qudi.util.helpers import call_slot_from_native_thread, current_is_main_thread
from qudi.util.yaml import YamlFileHandler
from qudi.util.mutex import Mutex
from qudi.util.network import connect_to_remote_module_server
from qudi.core.logger import get_logger
from qudi.core.object import ABCQObject
from qudi.core.module import Base, LogicBase, GuiBase, ModuleStateError, ModuleState, ModuleBase
from qudi.core.module import module_url
from qudi.core.config.validator import validate_local_module_config, validate_remote_module_config
from qudi.core.config.validator import ValidationError, validate_module_name


_logger = get_logger(__name__)


class ManagedModule(ABCQObject):
    """ Object representing a wrapper for a qudi module (gui, logic or hardware) to be managed by
    the ModuleManager object. Contains status properties and handles initialization, state
    transitions and connection of the module.
    """
    sigStateChanged = QtCore.Signal(ModuleState)  # current module state
    sigAppDataChanged = QtCore.Signal(bool)  # has_appdata flag

    _managed_modules: Final[Dict[str, 'ManagedModule']] = weakref.WeakValueDictionary()

    def __init__(self,
                 name: str,
                 base: Union[str, ModuleBase],
                 configuration: Mapping[str, Any],
                 qudi_main: 'Qudi'):
        super().__init__(parent=qudi_main.module_manager)

        if not isinstance(name, str):
            raise TypeError('Module name must be string type')
        validate_module_name(name)
        if name in self._managed_modules:
            raise ValueError(f'Module by name "{name}" already present in managed modules')
        self._name = name
        self._base = ModuleBase(base)
        self._configuration = configuration
        self._qudi_main = qudi_main
        self.__has_appdata_cache: bool = False
        self.__state_cache: ModuleState = ModuleState.DEACTIVATED
        self._managed_modules[name] = self

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
    def activate(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def deactivate(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def reload(self) -> None:
        raise NotImplementedError

    @property
    @final
    def state(self) -> ModuleState:
        return self.__state_cache

    @property
    @final
    def has_appdata(self) -> bool:
        return self.__has_appdata_cache

    @property
    @final
    def name(self) -> str:
        return self._name

    @property
    @final
    def base(self) -> ModuleBase:
        return self._base

    @property
    def required_module_names(self) -> FrozenSet[str]:
        """ Overwrite by subclass if needed """
        return frozenset()

    @property
    def thread_name(self) -> str:
        """ Generic qudi module thread name used by the ThreadManager in case the module is
        running in its own thread
        """
        return f'mod-{self.base.value}-{self.name}'

    @property
    def allow_remote(self) -> bool:
        """ Flag indicating if the module is allowed to be shared outside of localhost.
        False by default. Overwrite in subclass if necessary.
        """
        return False

    @property
    def active_dependent_modules(self) -> Dict[str, 'ManagedModule']:
        return {mod_name: mod for mod_name, mod in self._managed_modules.items() if
                (self._name in mod.required_module_names) and not mod.state.deactivated}

    @property
    def required_modules(self) -> Dict[str, 'ManagedModule']:
        return {mod_name: mod for mod_name, mod in self._managed_modules.items() if
                mod_name in self.required_module_names}

    def check_module_state(self) -> None:
        """ Override in subclass if you want to periodically poll the module state and perform
        some actions accordingly
        """
        pass

    def _activate_required_modules(self) -> Dict[str, Base]:
        target_instances = dict()
        for mod_name, module in self.required_modules.items():
            module.activate()
            target_instances[mod_name] = module.instance
        return target_instances

    def _deactivate_dependent_modules(self) -> None:
        for _, module in self.active_dependent_modules.items():
            module.deactivate()

    @QtCore.Slot(bool)
    def _update_appdata(self, has_appdata: bool) -> None:
        self.__has_appdata_cache = has_appdata
        self.sigAppDataChanged.emit(self.__has_appdata_cache)

    @QtCore.Slot(ModuleState)
    def _update_state(self, state: ModuleState) -> None:
        self.__state_cache = state
        self.sigStateChanged.emit(self.__state_cache)


class LocalManagedModule(ManagedModule):
    """
    """
    @staticmethod
    def __import_module_class(base: ModuleBase,
                              mod_url: str,
                              class_name: str,
                              reload: Optional[bool] = False) -> Tuple[ModuleType, Type[Base]]:
        # Import module
        try:
            module = importlib.import_module(mod_url)
            if reload:
                module = importlib.reload(module)
        except ImportError:
            raise
        except Exception as err:
            raise ImportError(f'Unable to import module "{mod_url}"') from err
        # Get class from module
        try:
            cls = getattr(module, class_name)
        except AttributeError:
            raise ImportError(f'No class "{class_name}" found in module "{mod_url}"') from None
        # Check if imported class is a valid qudi module class
        if base == ModuleBase.GUI:
            required_base = GuiBase
        elif base == ModuleBase.LOGIC:
            required_base = LogicBase
        else:
            required_base = Base
        if not (isinstance(cls, type) and issubclass(cls, required_base)):
            raise TypeError(
                f'Qudi module class "{cls.__module__}.{cls.__name__}" is no '
                f'subclass of "{required_base.__module__}.{required_base.__name__}"'
            )
        return module, cls

    def __init__(self,
                 name: str,
                 base: ModuleBase,
                 configuration: Mapping[str, Any],
                 qudi_main: 'Qudi'):
        validate_local_module_config(configuration)
        super().__init__(name, base, configuration, qudi_main)
        # Configuration
        self._module_url, self._class_name = self._configuration['module.Class'].rsplit('.', 1)
        if not self._module_url.startswith('qudi.'):
            if self._module_url.startswith(tuple(f'{b.value}.' for b in ModuleBase)):
                self._module_url = f'qudi.{self._module_url}'
            else:
                self._module_url = f'qudi.{self.base.value}.{self._module_url}'
        self._allow_remote = self._configuration['allow_remote']
        if self._allow_remote and (self.base == ModuleBase.GUI):
            self._allow_remote = False
            _logger.warning(f'GUI modules can not be shared as remote modules ({self.url})')
        self._options = self._configuration.get('options', dict())
        self._connections = self._configuration.get('connect', dict())
        # Circular recursion fail-saves
        self.__activating = False
        self.__deactivating = False
        # Import qudi module class
        self._module, self._class = self.__import_module_class(self.base,
                                                               self._module_url,
                                                               self._class_name,
                                                               reload=False)
        self._instance = None
        # App status handling
        self._appdata_handler = YamlFileHandler(
            get_module_appdata_path(self._class_name, self.base.value, self.name)
        )
        self._update_appdata(self._appdata_handler.exists)

    @property
    def url(self) -> str:
        return module_url(self._module_url, self._class_name, self.name)

    @property
    def instance(self) -> Union[None, Base]:
        return self._instance

    @property
    def required_module_names(self) -> FrozenSet[str]:
        return frozenset(self._connections.values())

    @property
    def allow_remote(self) -> bool:
        return self._allow_remote

    @property
    def is_threaded(self) -> bool:
        return self._class.module_threaded

    @QtCore.Slot()
    def clear_appdata(self) -> None:
        try:
            self._instance.clear_status_variables()
        except AttributeError:
            try:
                self._appdata_handler.clear()
            finally:
                self._update_appdata(self._appdata_handler.exists)

    @QtCore.Slot()
    def activate(self) -> None:
        # Redirect to main thread
        if not current_is_main_thread():
            call_slot_from_native_thread(self, 'activate', blocking=True)
            return

        # Avoid circular recursion
        if self.__activating:
            return

        # Do nothing if already active (except showing the GUI again)
        if not self.state.deactivated:
            if self.base == ModuleBase.GUI:
                self._instance.show()
            return

        _logger.info(f'Activating module "{self.url}" ...')
        self.__activating = True
        try:
            self._instantiate_module_class(required_targets=self._activate_required_modules())
            if self.is_threaded:
                try:
                    self._move_instance_to_thread()
                    self._connect_module_signals()
                    self._activate_instance_threaded()
                except Exception:
                    try:
                        self._join_instance_thread()
                    except Exception:
                        pass
                    raise
            else:
                self._connect_module_signals()
                self._instance.module_state.activate()
                QtCore.QCoreApplication.instance().processEvents()
        except Exception:
            try:
                self._disconnect_module_signals()
            except:
                pass
            self._instance = None
            raise
        finally:
            self.__activating = False
        _logger.info(f'Module "{self.url}" successfully activated.')

    @QtCore.Slot()
    def deactivate(self) -> None:
        # Redirect to main thread
        if not current_is_main_thread():
            call_slot_from_native_thread(self, 'deactivate', blocking=True)
            return

        # Avoid circular recursion
        if self.__deactivating or self.state.deactivated:
            return

        self.__deactivating = True
        _logger.info(f'Deactivating module "{self.url}" ...')
        try:
            try:
                self._deactivate_dependent_modules()
            finally:
                try:
                    if self.is_threaded:
                        try:
                            self._deactivate_instance_threaded()
                        finally:
                            self._join_instance_thread()
                    else:
                        self._instance.module_state.deactivate()
                    # QtCore.QCoreApplication.instance().processEvents()
                finally:
                    self._disconnect_module_signals()
                    self._update_state(ModuleState.DEACTIVATED)
        finally:
            self._instance = None
            self.__deactivating = False
        _logger.info(f'Module "{self.url}" successfully deactivated.')

    @QtCore.Slot()
    def reload(self) -> None:
        # Redirect to main thread
        if not current_is_main_thread():
            call_slot_from_native_thread(self, 'reload', blocking=True)
            return

        # Determine current activation state of self and dependent modules.
        # Deactivate all if needed and remember states.
        was_active = not self.state.deactivated
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

        # Re-import module and class
        self._module, self._class = self.__import_module_class(self.base,
                                                               self._module_url,
                                                               self._class_name,
                                                               reload=True)
        _logger.info(f'Module "{self.url}" reloaded successfully')

        # Re-activate all previously active modules
        if was_active:
            self.activate()
            for module in active_dependent_modules:
                module.activate()

    def _instantiate_module_class(self, required_targets: Mapping[str, Base]) -> None:
        """ Try to instantiate the imported qudi module class """
        try:
            connections = {
                conn: required_targets[target] for conn, target in self._connections.items()
            }
            self._instance = self._class(qudi_main=self._qudi_main,
                                         name=self.name,
                                         options=self._options,
                                         connections=connections)
        except Exception as err:
            self._instance = None
            raise RuntimeError(f'Error during __init__ of qudi module "{self.url}".') from err

    def _connect_module_signals(self) -> None:
        self._instance.sigStateChanged.connect(self._update_state, QtCore.Qt.QueuedConnection)
        self._instance.sigAppDataChanged.connect(self._update_appdata, QtCore.Qt.QueuedConnection)

    def _disconnect_module_signals(self) -> None:
        self._instance.sigAppDataChanged.disconnect()
        self._instance.sigStateChanged.disconnect()

    def _move_instance_to_thread(self) -> None:
        thread_manager = self._qudi_main.thread_manager
        thread = thread_manager.get_new_thread(self.thread_name)
        self._instance.moveToThread(thread)
        thread.start()

    def _join_instance_thread(self) -> None:
        thread_manager = self._qudi_main.thread_manager
        try:
            self._instance.move_to_main_thread()
        finally:
            thread_manager.quit_thread(self.thread_name)
            thread_manager.join_thread(self.thread_name)

    def _activate_instance_threaded(self) -> None:
        # Activate instance in native thread
        call_slot_from_native_thread(self._instance.module_state, 'activate', blocking=True)
        # Check if activation has been successful
        if self._instance.module_state.current.deactivated:
            raise ModuleStateError(f'Error during threaded activation of module "{self.url}"')

    def _deactivate_instance_threaded(self) -> None:
        # Activate instance in native thread
        call_slot_from_native_thread(self._instance.module_state, 'deactivate', blocking=True)
        # Check if deactivation has been successful
        if not self._instance.module_state.current.deactivated:
            raise ModuleStateError(f'Error during threaded deactivation of module "{self.url}"')


class RemoteManagedModule(ManagedModule):
    """
    """
    def __init__(self,
                 name: str,
                 base: ModuleBase,
                 configuration: Mapping[str, Any],
                 qudi_main: 'Qudi'):
        validate_remote_module_config(configuration)
        super().__init__(name, base, configuration, qudi_main)
        # Configuration
        self._native_name: str = self._configuration['native_module_name']
        self._host: str = self._configuration['address']
        self._port: int = self._configuration['port']
        self._certfile: Union[str, None] = self._configuration['certfile']
        self._keyfile: Union[str, None] = self._configuration['keyfile']

        self._connection: Union[rpyc.Connection, None] = None
        self._url = f'{self._host}:{self._port:d}/{self._native_name}'
        # Circular recursion fail-saves
        self.__activating = False
        self.__deactivating = False

    @property
    def url(self) -> str:
        return self._url

    @property
    def instance(self) -> Union[None, Base]:
        try:
            return self._connection.root.get_module_instance(self._native_name)
        except AttributeError:
            return None

    @QtCore.Slot()
    def clear_appdata(self) -> None:
        self._update_appdata(False)

    @QtCore.Slot()
    def activate(self) -> None:
        # Redirect to main thread
        if not current_is_main_thread():
            call_slot_from_native_thread(self, 'activate', blocking=True)
            return

        if self.__activating or self._connection is not None:
            return

        _logger.info(f'Activating remote module "{self.name}" at "{self.url}" ...')
        self.__activating = True
        try:
            try:
                self._connection = connect_to_remote_module_server(host=self._host,
                                                                   port=self._port,
                                                                   certfile=self._certfile,
                                                                   keyfile=self._keyfile)
                _logger.debug(f'Connected to RemoteModulesServer on {self._host}:{self._port:d}')
            except Exception as err:
                raise RuntimeError(
                    f'Unable to connect to remote module "{self.name}" at "{self.url}"'
                ) from err
            try:
                self._connection.root.get_module_instance(self._native_name)
            except Exception as err:
                raise ModuleStateError(
                    f'Unable to activate remote module "{self.name}" at "{self.url}"'
                ) from err
            finally:
                try:
                    self._update_state(
                        ModuleState(self._connection.root.get_module_state(self._native_name).value)
                    )
                except Exception:
                    self._update_state(ModuleState.DEACTIVATED)
        except:
            self._connection = None
            raise
        finally:
            self.__activating = False
        QtCore.QCoreApplication.instance().processEvents()
        _logger.info(f'Remote module "{self.name}" at "{self.url}" successfully activated.')

    @QtCore.Slot()
    def deactivate(self) -> None:
        # Redirect to main thread
        if not current_is_main_thread():
            call_slot_from_native_thread(self, 'deactivate', blocking=True)
            return

        if self.__deactivating or self._connection is None:
            return

        self.__deactivating = True
        _logger.info(f'Disconnecting remote module "{self.name}" at "{self.url}" ...')
        try:
            self._deactivate_dependent_modules()
        finally:
            try:
                self._connection.close()
            finally:
                self._connection = None
            self.__deactivating = False
            self._update_state(ModuleState.DEACTIVATED)
        _logger.info(f'Remote module "{self.name}" at "{self.url}" successfully disconnected.')

    @QtCore.Slot()
    def reload(self) -> None:
        # Redirect to main thread
        if not current_is_main_thread():
            call_slot_from_native_thread(self, 'reload', blocking=True)
            return

        if self._connection is not None:
            # Find all modules that are currently active and depend recursively on self
            active_dependent_modules = set(self.active_dependent_modules.values())
            while True:
                dependency_count = len(active_dependent_modules)
                for module in list(active_dependent_modules):
                    active_dependent_modules.update(module.active_dependent_modules.values())
                if dependency_count == len(active_dependent_modules):
                    break
            self.deactivate()
            _logger.info(f'Reconnecting to remote module "{self.name}" at "{self.url}"')
            self.activate()
            for module in active_dependent_modules:
                module.activate()

    def check_module_state(self) -> None:
        try:
            state = ModuleState(self._connection.root.get_module_state(self._native_name).value)
            if state.deactivated:
                self.deactivate()
        except AttributeError:
            state = ModuleState.DEACTIVATED
        if state != self.state:
            self._update_state(state)


class ModuleManager(QtCore.QAbstractTableModel):
    """
    """
    _instance = None  # Only class instance created will be stored here as weakref
    _lock = Mutex()

    __WATCHDOG_TIMEOUT = 1000  # milliseconds

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

    def __init__(self, *args, qudi_main: 'Qudi', **kwargs):
        super().__init__(*args, **kwargs)
        self._qudi_main = qudi_main
        self._modules = list()
        self._name_to_module = dict()
        self._name_to_index = dict()
        self._display_headers = ('Base', 'Name', 'State', 'Has AppData', 'Allow Remote',
                                 'Is Remote')

        # Remote module state watchdog
        self.__remote_watchdog_timer = QtCore.QTimer(self)
        self.__remote_watchdog_timer.setInterval(self.__WATCHDOG_TIMEOUT)
        self.__remote_watchdog_timer.setSingleShot(True)
        self.__remote_watchdog_timer.timeout.connect(self.__remote_watchdog,
                                                     QtCore.Qt.QueuedConnection)

    @classmethod
    def instance(cls):
        with cls._lock:
            if cls._instance is None:
                return None
            return cls._instance()

    def rowCount(self, parent: Optional[QtCore.QModelIndex] = None) -> int:
        """ Returns the number of stored items (rows) """
        return len(self._modules)

    def columnCount(self, parent: Optional[QtCore.QModelIndex] = None) -> int:
        """ Returns the number of data columns """
        return len(self._display_headers)

    def flags(self, index: Optional[QtCore.QModelIndex] = None) -> QtCore.Qt.ItemFlags:
        """ Determines what can be done with the given indexed cell """
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self,
             index: QtCore.QModelIndex,
             role: Optional[QtCore.Qt.ItemDataRole] = QtCore.Qt.DisplayRole
             ) -> Union[None, ManagedModule, str, ModuleBase, ModuleState, bool]:
        """ Get data from model for a given cell. Data can have a role that affects display. """
        if index.isValid():
            module = self._modules[index.row()]
            if role == QtCore.Qt.DisplayRole:
                column = index.column()
                if column == 0:
                    return module.base
                elif column == 1:
                    return module.name
                elif column == 2:
                    return module.state
                elif column == 3:
                    return module.has_appdata
                elif column == 4:
                    return module.allow_remote
                elif column == 5:
                    return isinstance(module, RemoteManagedModule)
            elif role == QtCore.Qt.UserRole:
                return module
        return None

    def headerData(self,
                   section: int,
                   orientation: QtCore.Qt.Orientation,
                   role: Optional[QtCore.Qt.ItemDataRole] = QtCore.Qt.DisplayRole
                   ) -> Union[None, str]:
        """ Data for the table view headers """
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return self._display_headers[section]
            elif role == QtCore.Qt.UserRole:
                return 'ManagedModule'
        return None

    def add_module(self,
                   name: str,
                   base: ModuleBase,
                   configuration: Mapping[str, Any],
                   allow_overwrite: Optional[bool] = False) -> None:
        if not current_is_main_thread():
            raise RuntimeError(
                'Modules can only be added/removed from ModuleManager by the qudi main thread'
            )
        with self._lock:
            if allow_overwrite:
                self._remove_module(name, ignore_missing=True)
            elif name in self._name_to_index:
                raise ValueError(f'Module by name "{name}" already registered')
            # Initialize ManagedModule instance
            try:
                module = LocalManagedModule(name, base, configuration, self._qudi_main)
            except ValidationError:
                module = RemoteManagedModule(name, base, configuration, self._qudi_main)
            # Add module to data model
            row = len(self._modules)
            self.beginInsertRows(QtCore.QModelIndex(), row, row)
            self._modules.append(module)
            self._name_to_index[name] = row
            self._name_to_module[name] = module
            module.sigStateChanged.connect(self.__get_state_updated_slot(name))
            module.sigAppDataChanged.connect(self.__get_appdata_updated_slot(name))
            self.endInsertRows()
            if len(self._modules) == 1:
                self.__remote_watchdog_timer.start()

    def remove_module(self, name: str, ignore_missing: Optional[bool] = False) -> None:
        if not current_is_main_thread():
            raise RuntimeError(
                'Modules can only be added/removed from ModuleManager by the qudi main thread'
            )
        with self._lock:
            return self._remove_module(name, ignore_missing)

    def _remove_module(self, name: str, ignore_missing: Optional[bool] = False) -> None:
        try:
            row = self._get_index_by_name(name)
        except ValueError:
            if ignore_missing:
                return
            raise
        # Remove module from data model
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        row = self._name_to_index.pop(name)
        module = self._name_to_module.pop(name)
        self._modules.pop(row)
        for mod in list(self._name_to_index)[row:]:
            self._name_to_index[mod] -= 1
        module.sigStateChanged.disconnect()
        module.sigAppDataChanged.disconnect()
        self.endRemoveRows()
        module.deactivate()
        if len(self._modules) < 1:
            self.__remote_watchdog_timer.stop()

    def activate_module(self, name: str) -> None:
        with self._lock:
            self._get_module_by_name(name).activate()

    def deactivate_module(self, name: str) -> None:
        with self._lock:
            self._get_module_by_name(name).deactivate()

    def reload_module(self, name: str) -> None:
        with self._lock:
            self._get_module_by_name(name).reload()

    def clear_module_appdata(self, name: str) -> None:
        with self._lock:
            self._get_module_by_name(name).clear_appdata()

    def has_appdata(self, name: str) -> bool:
        with self._lock:
            return self._get_module_by_name(name).has_appdata

    def get_module_state(self, name: str) -> ModuleState:
        with self._lock:
            return self._get_module_by_name(name).state

    def get_module_instance(self, name: str) -> Union[Base, None]:
        with self._lock:
            module = self._get_module_by_name(name)
            module.activate()
            return module.instance

    def activate_all_modules(self) -> None:
        with self._lock:
            for module in self._modules:
                module.activate()

    def deactivate_all_modules(self) -> None:
        with self._lock:
            for module in self._modules:
                module.deactivate()

    def clear_all_appdata(self) -> None:
        with self._lock:
            for module in self._modules:
                module.clear_appdata()

    def clear(self):
        with self._lock:
            self.__remote_watchdog_timer.stop()
            self.beginResetModel()
            for module in self._modules:
                try:
                    module.sigStateChanged.disconnect()
                    module.sigAppDataChanged.disconnect()
                    module.deactivate()
                except Exception:
                    _logger.exception('Exception while clearing ModuleManager:')
            self._modules.clear()
            self._name_to_index.clear()
            self._name_to_module.clear()
            self.endResetModel()

    def _get_index_by_name(self, name: str) -> int:
        """ Get the row index by module name """
        try:
            return self._name_to_index[name]
        except KeyError:
            raise ValueError(f'No module found by name "{name}"') from None

    def _get_module_by_name(self, name: str) -> ManagedModule:
        """ Get the ManagedModule instance by module name """
        try:
            return self._name_to_module[name]
        except KeyError:
            raise ValueError(f'No module found by name "{name}"') from None

    def __get_state_updated_slot(self, name: str) -> Callable[[], None]:

        def state_updated() -> None:
            index = self.index(self._name_to_index[name], 2)
            self.dataChanged.emit(index, index)

        return state_updated

    def __get_appdata_updated_slot(self, name: str) -> Callable[[], None]:

        def appdata_updated() -> None:
            index = self.index(self._name_to_index[name], 3)
            self.dataChanged.emit(index, index)

        return appdata_updated

    @QtCore.Slot()
    def __remote_watchdog(self) -> None:
        with self._lock:
            if len(self._modules) > 0:
                for module in self._modules:
                    module.check_module_state()
                self.__remote_watchdog_timer.start()
