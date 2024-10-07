# -*- coding: utf-8 -*-
"""
This file contains the qudi tools for remote module sharing via rpyc server.

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

__all__ = ['RemoteModulesService', 'LocalNamespaceService']

import rpyc
from logging import Logger
from typing import Optional, Union, List, Dict, Any

from qudi.util.proxy import CachedObjectRpycByValueProxy
from qudi.core.logger import get_logger
from qudi.core.module import Base, ModuleState, ModuleBase
from qudi.core.modulemanager import ModuleManager


_logger = get_logger(__name__)


class RemoteModulesService(rpyc.Service):
    """ An RPyC service that has a shared modules table model """
    ALIASES = ['RemoteModules']

    def __init__(self,
                 *args,
                 module_manager: ModuleManager,
                 force_remote_calls_by_value: Optional[bool] = False,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self._force_remote_calls_by_value = force_remote_calls_by_value
        self._module_manager = module_manager
        self.__shared_module_names = {name for name in self._module_manager.module_names if
                                      self._module_manager.allow_remote(name)}

    def _check_module_name(self, name: str) -> None:
        if name not in self.__shared_module_names:
            raise ValueError(f'Client requested module "{name}" that is not shared')

    def on_connect(self, conn):
        """ code that runs when a connection is created
        """
        host, port = conn._config['endpoints'][1]
        _logger.info(f'Client connected to remote modules service from [{host}]:{port:d}')

    def on_disconnect(self, conn):
        """ code that runs when the connection is closing
        """
        host, port = conn._config['endpoints'][1]
        _logger.info(f'Client [{host}]:{port:d} disconnected from remote modules service')

    def exposed_get_module_instance(self, name: str,) -> Union[CachedObjectRpycByValueProxy, Base]:
        """ Return reference to a module in the shared module list """
        self._check_module_name(name)
        instance = self._module_manager.get_module_instance(name)
        if self._force_remote_calls_by_value:
            instance = CachedObjectRpycByValueProxy(instance)
        return instance

    def exposed_get_module_state(self, name: str) -> ModuleState:
        """ Return current ModuleState of the given module """
        self._check_module_name(name)
        return self._module_manager.get_module_state(name)

    def exposed_module_has_appdata(self, name: str) -> bool:
        self._check_module_name(name)
        return self._module_manager.has_appdata(name)

    def exposed_get_available_module_names(self) -> List[str]:
        """ Returns the currently shared module names """
        return list(self.__shared_module_names)


class LocalNamespaceService(rpyc.Service):
    """ An RPyC service providing a namespace dict containing references to all active qudi module
    instances as well as a reference to the qudi application itself.
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
        """ runs when a connection is created """
        host, port = conn._config['endpoints'][1]
        _logger.info(f'Client connected to local module service from [{host}]:{port:d}')

    def on_disconnect(self, conn):
        """ runs when the connection is closing """
        host, port = conn._config['endpoints'][1]
        _logger.info(f'Client [{host}]:{port:d} disconnected from local module service')

    def exposed_get_namespace_dict(self) -> Dict[str, Any]:
        """ Returns the instances of the currently active modules as well as a reference to the
        qudi application itself.
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
        """ Returns a logger object for remote processes to log into the qudi logging facility """
        return get_logger(name)
