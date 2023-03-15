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

__all__ = ('RemoteModulesService', 'QudiNamespaceService')

import logging

import rpyc
import pickle
from typing import Optional, Any

from qudi.util.mutex import Mutex
from qudi.util.models import DictTableModel
from qudi.core.logger import get_logger

logger = get_logger(__name__)


class _SharedModulesModel(DictTableModel):
    """ Derived list model for GUI display elements
    """
    def __init__(self):
        super().__init__(headers='Shared Module')


class RemoteModulesService(rpyc.Service):
    """ An RPyC service that has a module list.
    """
    ALIASES = ['RemoteModules']

    def __init__(self, *args, module_manager, **kwargs):
        super().__init__(*args, **kwargs)
        self._thread_lock = Mutex()
        self._module_manager = module_manager
        # Dict model with module names (keys) and instance client counts (values)
        self.shared_modules = _SharedModulesModel()

    def share_module(self, module_name: str) -> None:
        with self._thread_lock:
            if module_name in self.shared_modules:
                logger.warning(f'Module "{module_name}" already shared')
                return
            self.shared_modules[module_name] = 0

    def remove_shared_module(self, module_name: str) -> None:
        with self._thread_lock:
            self.shared_modules.pop(module_name, None)

    def on_connect(self, conn):
        """ code that runs when a connection is created """
        host, port = conn._config['endpoints'][1]
        logger.info(f'Client connected to remote modules service from {host}:{port:d}')

    def on_disconnect(self, conn):
        """ code that runs when the connection is closing """
        host, port = conn._config['endpoints'][1]
        logger.info(f'Client {host}:{port:d} disconnected from remote modules service')

    def __check_module_name(self, name: str) -> None:
        if name not in self.shared_modules:
            raise ValueError(
                f'Module "{name}" requested by client can not be found in shared modules.'
            )

    def exposed_activate_module(self, name: str) -> None:
        with self._thread_lock:
            self.__check_module_name(name)
            self._module_manager.activate_module(name)

    def exposed_deactivate_module(self, name: str) -> None:
        with self._thread_lock:
            self.__check_module_name(name)
            self._module_manager.deactivate_module(name)

    def exposed_reload_module(self, name: str) -> None:
        with self._thread_lock:
            self.__check_module_name(name)
            self._module_manager.reload_module(name)

    def exposed_module_has_appdata(self, name: str):
        with self._thread_lock:
            self.__check_module_name(name)
            return self._module_manager.module_has_appdata(name)

    def exposed_get_module_state(self, name: str):
        with self._thread_lock:
            self.__check_module_name(name)
            return self._module_manager.get_module_state(name)

    def exposed_clear_module_appdata(self, name: str) -> None:
        with self._thread_lock:
            self.__check_module_name(name)
            self._module_manager.clear_module_appdata(name)

    def exposed_get_module_instance(self, name: str) -> object:
        """ Return reference to a qudi module instance in the shared module list """
        with self._thread_lock:
            self.__check_module_name(name)
            instance = self._module_manager.get_module_instance(name)
            if instance is None:
                return None
            # Increment instance client counter
            self.shared_modules[name] += 1
            return instance

    def exposed_return_module_instance(self, instance: object) -> None:
        with self._thread_lock:
            try:
                self.shared_modules[instance.module_name] -= 1
            except (KeyError, AttributeError):
                pass

    def exposed_get_module_client_count(self, name: str) -> int:
        with self._thread_lock:
            try:
                return self.shared_modules[name]
            except KeyError:
                return 0

    def exposed_get_shared_module_names(self) -> tuple:
        """ Returns the currently shared module names independent of the current module state """
        with self._thread_lock:
            return tuple(self.shared_modules)

    def exposed_get_pickle_module(self):
        return pickle

    def exposed_get_module_attribute(self, module_name: str, attribute_name: str) -> Any:
        with self._thread_lock:
            self.__check_module_name(module_name)
            instance = self._module_manager.get_module_instance(module_name)
        if instance is None:
            raise RuntimeError(f'Module "{module_name}" is not active')
        return getattr(instance, attribute_name)

    def exposed_set_module_attribute(self,
                                     module_name: str,
                                     attribute_name: str,
                                     value: Any) -> None:
        with self._thread_lock:
            self.__check_module_name(module_name)
            instance = self._module_manager.get_module_instance(module_name)
        if instance is None:
            raise RuntimeError(f'Module "{module_name}" is not active')
        setattr(instance, attribute_name, value)

    def exposed_del_module_attribute(self, module_name: str, attribute_name: str) -> None:
        with self._thread_lock:
            self.__check_module_name(module_name)
            instance = self._module_manager.get_module_instance(module_name)
        if instance is None:
            raise RuntimeError(f'Module "{module_name}" is not active')
        delattr(instance, attribute_name)


class QudiNamespaceService(rpyc.Service):
    """ An RPyC service providing a namespace dict containing references to all active qudi module
    instances as well as a reference to the qudi application itself.
    """
    ALIASES = ['QudiNamespace']

    def __init__(self, *args, qudi, force_remote_calls_by_value=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._qudi_main = qudi
        self._notifier_callbacks = dict()
        self._force_remote_calls_by_value = force_remote_calls_by_value

    @property
    def _module_manager(self):
        return self._qudi_main.module_manager

    def on_connect(self, conn):
        """ code that runs when a connection is created
        """
        try:
            self._notifier_callbacks[conn] = rpyc.async_(conn.root.modules_changed)
        except AttributeError:
            pass
        host, port = conn._config['endpoints'][1]
        logger.info(f'Client connected to local namespace service from {host}:{port:d}')

    def on_disconnect(self, conn):
        """ code that runs when the connection is closing
        """
        self._notifier_callbacks.pop(conn, None)
        host, port = conn._config['endpoints'][1]
        logger.info(f'Client {host}:{port:d} disconnected from local namespace service')

    def notify_module_change(self):
        logger.debug('Local module server has detected a module state change and sends async '
                     'notifier signals to all clients')
        for callback in self._notifier_callbacks.values():
            callback()

    def exposed_get_pickle_module(self):
        return pickle if self._force_remote_calls_by_value else None

    def exposed_get_namespace_dict(self):
        """ Returns the instances of the currently active modules as well as a reference to the
        qudi application itself.

        @return dict: Names (keys) and object references (values)
        """
        mods = {name: instance for name, instance in
                self._module_manager.module_instances.items() if instance is not None}
        mods['qudi'] = self._qudi_main
        return mods

    def exposed_get_logger(self, name: str) -> logging.Logger:
        """ Returns a logger object for remote processes to log into the qudi logging facility """
        return get_logger(name)
