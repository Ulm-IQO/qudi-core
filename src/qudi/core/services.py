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
from PySide2 import QtCore
from typing import Optional, Union, List, Dict, Any, Iterable, Set

from qudi.util.mutex import Mutex
from qudi.util.proxy import CachedObjectRpycByValueProxy
from qudi.core.logger import get_logger
from qudi.core.module import Base, ModuleState, ModuleBase
from qudi.core.modulemanager import ModuleManager


_logger = get_logger(__name__)


class _SharedModuleTableProxyModel(QtCore.QSortFilterProxyModel):
    """ Model proxy to filter ManagedModules according to their "allow_remote" flag. """
    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:
        return self.sourceModel().index(source_row, 4, source_parent).data()


class _LocalModuleTableProxyModel(QtCore.QSortFilterProxyModel):
    """ Model proxy to filter ManagedModules according to their "allow_remote" flag. """
    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:
        return self.sourceModel().index(source_row, 0, source_parent).data() != ModuleBase.GUI


class RemoteModulesService(rpyc.Service):
    """ An RPyC service that has a shared modules table model """
    ALIASES = ['RemoteModules']

    def __init__(self,
                 *args,
                 module_manager: ModuleManager,
                 force_remote_calls_by_value: Optional[bool] = False,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self._thread_lock = Mutex()
        self._force_remote_calls_by_value = force_remote_calls_by_value
        self._module_manager = module_manager
        self._module_cache: Set[str] = set()
        self.shared_modules = _SharedModuleTableProxyModel()
        self.shared_modules.setSourceModel(self._module_manager)
        self.shared_modules.modelReset.connect(self._refresh_module_cache)
        self.shared_modules.rowsInserted.connect(self._refresh_module_cache)
        self.shared_modules.rowsRemoved.connect(self._refresh_module_cache)
        self._refresh_module_cache()

    @QtCore.Slot()
    def _refresh_module_cache(self) -> None:
        with self._thread_lock:
            self._module_cache = {
                self.shared_modules.index(row, 1).data() for row in
                range(self.shared_modules.rowCount())
            }

    def _check_module_name(self, name: str) -> None:
        if name not in self._module_cache:
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
        with self._thread_lock:
            self._check_module_name(name)
            instance = self._module_manager.get_module_instance(name)
            if self._force_remote_calls_by_value:
                return CachedObjectRpycByValueProxy(instance)
            return instance

    def exposed_get_module_state(self, name: str) -> ModuleState:
        """ Return current ModuleState of the given module """
        with self._thread_lock:
            self._check_module_name(name)
            return self._module_manager.get_module_state(name)

    def exposed_get_available_module_names(self) -> List[str]:
        """ Returns the currently shared module names """
        with self._thread_lock:
            return list(self._module_cache)


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
        self._thread_lock = Mutex()
        self._qudi = qudi
        self._force_remote_calls_by_value = force_remote_calls_by_value
        self._module_cache: Dict[str, Union[Base, CachedObjectRpycByValueProxy]] = dict()

        self.namespace_modules = _LocalModuleTableProxyModel()
        self.namespace_modules.setSourceModel(self._qudi.module_manager)
        self.namespace_modules.modelReset.connect(self._refresh_module_cache)
        self.namespace_modules.rowsInserted.connect(self._refresh_module_cache)
        self.namespace_modules.rowsRemoved.connect(self._refresh_module_cache)
        self.namespace_modules.dataChanged.connect(self._module_state_changed)
        self._refresh_module_cache()

    @QtCore.Slot()
    def _refresh_module_cache(self) -> None:
        with self._thread_lock:
            modules = [
                self.namespace_modules.index(row, 0).data(QtCore.Qt.UserRole) for row in
                range(self.namespace_modules.rowCount())
            ]
            if self._force_remote_calls_by_value:
                self._module_cache = {mod.name: CachedObjectRpycByValueProxy(mod.instance) for mod
                                      in modules if not mod.state.deactivated}
            else:
                self._module_cache = {mod.name: mod.instance for mod in modules if
                                      not mod.state.deactivated}

    def _module_state_changed(self,
                              top_left: QtCore.QModelIndex,
                              bottom_right: QtCore.QModelIndex,
                              roles: Iterable[QtCore.Qt.ItemDataRole]) -> None:
        if (top_left.column() <= 2) and (bottom_right.column() >= 2):
            with self._thread_lock:
                for row in range(top_left.row(), bottom_right.row() + 1):
                    module = top_left.model().index(row, 0).data(QtCore.Qt.UserRole)
                    if module.state.deactivated:
                        self._module_cache.pop(module.name, None)
                    else:
                        if self._force_remote_calls_by_value:
                            self._module_cache[module.name] = CachedObjectRpycByValueProxy(
                                module.instance
                            )
                        else:
                            self._module_cache[module.name] = module.instance

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
        with self._thread_lock:
            mods = self._module_cache.copy()
            mods['qudi'] = self._qudi
            return mods

    def exposed_get_logger(self, name: str) -> Logger:
        """ Returns a logger object for remote processes to log into the qudi logging facility """
        return get_logger(name)
