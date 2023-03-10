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
import weakref
from functools import wraps
from inspect import signature, isfunction, ismethod

from qudi.util.mutex import Mutex
from qudi.util.models import DictTableModel
from qudi.util.network import netobtain
from qudi.core.logger import get_logger
from qudi.core.module import ModuleState

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

    def __init__(self, *args, module_manager, force_remote_calls_by_value=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._thread_lock = Mutex()
        self._module_manager = module_manager
        self._force_remote_calls_by_value = force_remote_calls_by_value
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

    def exposed_get_module_info(self, name: str) -> object:
        with self._thread_lock:
            self.__check_module_name(name)
            return self._module_manager.get_module_info(name)

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
                raise RuntimeError(f'Can not get module instance for shared module "{name}". '
                                   f'Module has not been activated.')
            if self._force_remote_calls_by_value:
                instance = ModuleRpycProxy(instance)
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

    def exposed_get_active_module_names(self) -> tuple:
        """ Returns the currently shared module names for all modules that are active """
        with self._thread_lock:
            return tuple(name for name in self.shared_modules if
                         self._module_manager.get_module_state(name) != ModuleState.DEACTIVATED)


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

    def exposed_get_namespace_dict(self):
        """ Returns the instances of the currently active modules as well as a reference to the
        qudi application itself.

        @return dict: Names (keys) and object references (values)
        """
        if self._force_remote_calls_by_value:
            mods = {name: ModuleRpycProxy(instance) for name, instance in
                    self._module_manager.module_instances.items() if instance is not None}
        else:
            mods = {name: instance for name, instance in
                    self._module_manager.module_instances.items() if instance is not None}
        mods['qudi'] = self._qudi_main
        return mods

    def exposed_get_logger(self, name: str) -> logging.Logger:
        """ Returns a logger object for remote processes to log into the qudi logging facility """
        return get_logger(name)


class ModuleRpycProxy:
    """ Instances of this class serve as proxies for qudi modules accessed via RPyC.
    It currently wraps all API methods (none- and single-underscore methods) to only receive
    parameters "by value", i.e. using qudi.util.network.netobtain. This will only work if all
    method arguments are "pickle-able".
    In addition all values passed to __setattr__ are also received "by value".

    Proxy class concept heavily inspired by this python recipe under PSF License:
    https://code.activestate.com/recipes/496741-object-proxying/
    """

    __slots__ = ['_obj_ref', '__weakref__']

    def __init__(self, obj):
        object.__setattr__(self, '_obj_ref', weakref.ref(obj))

    # proxying (special cases)
    def __getattribute__(self, name):
        obj = object.__getattribute__(self, '_obj_ref')()
        attr = getattr(obj, name)
        if not name.startswith('__') and ismethod(attr) or isfunction(attr):
            sig = signature(attr)
            if len(sig.parameters) > 0:

                @wraps(attr)
                def wrapped(*args, **kwargs):
                    sig.bind(*args, **kwargs)
                    args = [netobtain(arg) for arg in args]
                    kwargs = {name: netobtain(arg) for name, arg in kwargs.items()}
                    return attr(*args, **kwargs)

                wrapped.__signature__ = sig
                return wrapped
        return attr

    def __delattr__(self, name):
        obj = object.__getattribute__(self, '_obj_ref')()
        return delattr(obj, name)

    def __setattr__(self, name, value):
        obj = object.__getattribute__(self, '_obj_ref')()
        return setattr(obj, name, netobtain(value))

    # factories
    _special_names = (
        '__abs__', '__add__', '__and__', '__call__', '__cmp__', '__coerce__', '__contains__',
        '__delitem__', '__delslice__', '__div__', '__divmod__', '__eq__', '__float__',
        '__floordiv__', '__ge__', '__getitem__', '__getslice__', '__gt__', '__hash__', '__hex__',
        '__iadd__', '__iand__', '__idiv__', '__idivmod__', '__ifloordiv__', '__ilshift__',
        '__imod__', '__imul__', '__int__', '__invert__', '__ior__', '__ipow__', '__irshift__',
        '__isub__', '__iter__', '__itruediv__', '__ixor__', '__le__', '__len__', '__long__',
        '__lshift__', '__lt__', '__mod__', '__mul__', '__ne__', '__neg__', '__oct__', '__or__',
        '__pos__', '__pow__', '__radd__', '__rand__', '__rdiv__', '__rdivmod__', '__reduce__',
        '__reduce_ex__', '__repr__', '__reversed__', '__rfloorfiv__', '__rlshift__', '__rmod__',
        '__rmul__', '__ror__', '__rpow__', '__rrshift__', '__rshift__', '__rsub__', '__rtruediv__',
        '__rxor__', '__setitem__', '__setslice__', '__sub__', '__truediv__', '__xor__', 'next',
        '__str__', '__nonzero__'
    )

    @classmethod
    def _create_class_proxy(cls, theclass):
        """ creates a proxy for the given class
        """

        def make_method(method_name):

            def method(self, *args, **kw):
                obj = object.__getattribute__(self, '_obj_ref')()
                args = [netobtain(arg) for arg in args]
                kw = {key: netobtain(val) for key, val in kw.items()}
                return getattr(obj, method_name)(*args, **kw)

            return method

        # Add all special names to this wrapper class if they are present in the original class
        namespace = dict()
        for name in cls._special_names:
            if hasattr(theclass, name):
                namespace[name] = make_method(name)

        return type(f'{cls.__name__}({theclass.__name__})', (cls,), namespace)

    def __new__(cls, obj, *args, **kwargs):
        """ creates an proxy instance referencing `obj`. (obj, *args, **kwargs) are passed to this
        class' __init__, so deriving classes can define an __init__ method of their own.

        note: _class_proxy_cache is unique per class (each deriving class must hold its own cache)
        """
        theclass = cls._create_class_proxy(obj.__class__)
        return object.__new__(theclass)
