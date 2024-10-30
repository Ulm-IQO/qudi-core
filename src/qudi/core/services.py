# -*- coding: utf-8 -*-
"""
Contains RPyC services to interact with qudi modules across process boundaries.

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

__all__ = ['RemoteModulesService', 'LocalNamespaceService']

import rpyc
from logging import Logger
from typing import Optional, Union, List, Dict, Any

from qudi.util.proxy import CachedObjectRpycByValueProxy
from qudi.util.mutex import Mutex
from qudi.core.logger import get_logger
from qudi.core.module import Base, ModuleState, ModuleBase
from qudi.core.modulemanager import ModuleManager


_logger = get_logger(__name__)


class RemoteModulesService(rpyc.Service):
    """
    RPyC service providing access of allowed qudi modules to client qudi applications.

    Parameters
    ----------
    module_manager : qudi.core.modulemanager.ModuleManager
        Qudi module manager singleton.
    force_remote_calls_by_value : bool, optional
        If `True` each qudi module instance will be wrapped by
        `qudi.util.proxy.CachedObjectRpycByValueProxy` to force serialization of most call
        arguments and return values.
    *args
        Positional arguments will be passed to `rpyc.Service.__init__`.
    **kwargs
        Additional keyword arguments will be passed to `rpyc.Service.__init__`.
    """
    ALIASES = ['RemoteModules']

    _lock = Mutex()
    __shared_module_count: Dict[str, int] = dict()

    @classmethod
    def init_shared_modules(cls, module_manager: ModuleManager) -> None:
        with cls._lock:
            cls.__shared_module_count = {name: 0 for name in module_manager.module_names if
                                         module_manager.allow_remote(name)}

    @classmethod
    def __increase_module_count(cls, name: str) -> int:
        cls.__shared_module_count[name] += 1
        return cls.__shared_module_count[name]

    @classmethod
    def __decrease_module_count(cls, name: str) -> int:
        new_count = max(0, cls.__shared_module_count[name] - 1)
        cls.__shared_module_count[name] = new_count
        return new_count

    @classmethod
    def __reset_module_count(cls, name: str) -> int:
        cls.__shared_module_count[name] = 0
        return 0

    def __init__(self,
                 *args,
                 module_manager: ModuleManager,
                 force_remote_calls_by_value: Optional[bool] = False,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self._force_remote_calls_by_value = force_remote_calls_by_value
        self._module_manager = module_manager
        self.__shared_modules = set()

    def __del__(self):
        self.__cleanup_shared_modules()

    def _check_module_name(self, name: str) -> None:
        if name not in self.__shared_module_count:
            raise ValueError(f'Client requested module "{name}" that is not shared')

    def __cleanup_shared_modules(self) -> None:
        with self._lock:
            for name in self.__shared_modules:
                self.__decrease_module_count(name)
        self.__shared_modules.clear()

    def on_connect(self, conn):
        """Runs when a connection is created."""
        host, port = conn._config['endpoints'][1]
        address = f'{host}:{port:d}'
        self.__shared_modules = set()
        _logger.info(f'Client connected to remote modules service from {address}')

    def on_disconnect(self, conn):
        """Runs when the connection is closing."""
        host, port = conn._config['endpoints'][1]
        address = f'{host}:{port:d}'
        self.__cleanup_shared_modules()
        _logger.info(f'Client {address} disconnected from remote modules service')

    def exposed_get_module_instance(self, name: str) -> Union[CachedObjectRpycByValueProxy, Base]:
        """ Return reference to a module in the shared module list """
        self._check_module_name(name)
        with self._lock:
            instance = self._module_manager.get_module_instance(name)
            if self._force_remote_calls_by_value:
                instance = CachedObjectRpycByValueProxy(instance)
            if name not in self.__shared_modules:
                self.__shared_modules.add(name)
                self.__increase_module_count(name)
        return instance

    def exposed_try_deactivate_module(self, name: str) -> int:
        """
        Tries to deactivate module from remote client. Only succeeds if no other local module
        or remote client is connected to it; unregisters the calling client in any case.
        Returns the number of remaining connections to local modules or remote clients.
        A return value > 0 indicates that the module remains active on the server side.

        Parameters
        ----------
        name : str
            Local native (server side) module name to deactivate.

        Returns
        -------
        int
            Number of remaining module connections. A value > 0 indicates the module remains active.
        """
        self._check_module_name(name)
        with self._lock:
            self.__shared_modules.discard(name)
            if self._module_manager.module_state(name) == ModuleState.DEACTIVATED:
                count = self.__reset_module_count(name)
            else:
                count = self.__decrease_module_count(name)
                if count == 0 and len(self._module_manager.active_dependent_modules(name)) == 0:
                    self._module_manager.deactivate_module(name)
                else:
                    count += 1
        return count

    def exposed_get_module_state(self, name: str) -> ModuleState:
        """
        Get current module state of the requested module.

        Parameters
        ----------
        name : str
            Local native (server side) module name to get the state for.

        Returns
        -------
        qudi.core.module.ModuleState
            Current state representation enum.
        """
        self._check_module_name(name)
        with self._lock:
            state = self._module_manager.module_state(name)
            if state == ModuleState.DEACTIVATED:
                self.__shared_modules.discard(name)
                self.__reset_module_count(name)
        return state

    def exposed_module_has_appdata(self, name: str) -> bool:
        """
        Get flag indicating if the requested module has an existing AppData file.

        Parameters
        ----------
        name : str
            Local native (server side) module name to get the AppData flag for.

        Returns
        -------
        bool
            Flag indicating if the requested module has AppData (`True`) or nor (`False`).
        """
        self._check_module_name(name)
        return self._module_manager.has_appdata(name)

    def exposed_get_available_module_names(self) -> List[str]:
        """
        Get a list of currently shared module names, i.e. a list of valid names to use as call
        arguments for most of the methods in this service.

        Returns
        -------
        list of str
            List of shared native (server side) module names.
        """
        return list(self.__shared_module_count)


class LocalNamespaceService(rpyc.Service):
    """
    An RPyC service providing a namespace dict containing references to all active qudi module
    instances as well as a reference to the qudi application itself.

    Parameters
    ----------
    qudi : qudi.core.application.Qudi
        Qudi application singleton instance.
    force_remote_calls_by_value : bool, optional
        If `True` each qudi module instance will be wrapped by
        `qudi.util.proxy.CachedObjectRpycByValueProxy` to force serialization of most call
        arguments and return values.
    *args
        Positional arguments will be passed to `rpyc.Service.__init__`.
    **kwargs
        Additional keyword arguments will be passed to `rpyc.Service.__init__`.
    """
    ALIASES = ['QudiNamespace']

    def __init__(self,
                 *args,
                 qudi: 'Qudi',
                 force_remote_calls_by_value: Optional[bool] = False,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self._qudi = qudi
        self._force_remote_calls_by_value = force_remote_calls_by_value

    def on_connect(self, conn):
        """Runs when a connection is created."""
        host, port = conn._config['endpoints'][1]
        _logger.info(f'Client connected to local module service from {host}:{port:d}')

    def on_disconnect(self, conn):
        """Runs when the connection is closing."""
        host, port = conn._config['endpoints'][1]
        _logger.info(f'Client {host}:{port:d} disconnected from local module service')

    def exposed_get_namespace_dict(self) -> Dict[str, Any]:
        """
        Get names and instances of the currently active modules as well as a reference to the
        qudi application itself.

        Returns
        -------
        dict
            Currently active module names (keys) with their respective module instances (values).
            Also the special key "qudi" containing a reference to the qudi application instance.
        """
        mods = self._qudi.module_manager.get_active_module_instances()
        if self._force_remote_calls_by_value:
            mods = {name: CachedObjectRpycByValueProxy(mod) for name, mod in mods.items() if
                    mod.module_base != ModuleBase.GUI}
        else:
            mods = {name: mod for name, mod in mods.items() if mod.module_base != ModuleBase.GUI}
        mods['qudi'] = self._qudi
        return mods

    def exposed_get_logger(self, name: str) -> Logger:
        """
        Returns a logger instance for remote processes to send log messages directly into the qudi
        logging facility.

        Parameters
        ----------
        name : str
            Name identifier to initialize the logger instance with.

        Returns
        -------
        logging.Logger
            Logger instance initialized with given name and connected to the running qudi app.
        """
        return get_logger(name)
