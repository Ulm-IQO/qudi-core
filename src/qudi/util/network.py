# -*- coding: utf-8 -*-
"""
Check if something is a rpyc remotemodules object and transfer it

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

__all__ = ['netobtain', 'netdeliver', 'wrap_remote_call_by_value', 'RpycByValueProxy']


import pickle as _pickle
import inspect as _inspect
from rpyc.core.netref import BaseNetref as _BaseNetref
from typing import Any, Optional, Callable
from types import ModuleType
from qudi.util.proxy import ObjectProxy


def __contains_netref(obj) -> bool:
    if isinstance(obj, _BaseNetref):
        return True
    elif isinstance(obj, (tuple, frozenset)):
        return any(__contains_netref(it) for it in obj)
    return False


def netobtain(remote_obj: Any,
              remote_pickle: Optional[ModuleType] = None,
              silent_skip: Optional[bool] = True) -> Any:
    if not __contains_netref(remote_obj):
        return remote_obj
    if remote_pickle is None:
        remote_pickle = _pickle
    try:
        return _pickle.loads(
            remote_pickle.dumps(remote_obj, 5, fix_imports=False),
            fix_imports=False
        )
    except TypeError:
        if silent_skip:
            # In case pickling is not possible, skip pickling silently
            return remote_obj
        else:
            raise


def netdeliver(local_obj: Any,
               remote_pickle: ModuleType,
               silent_skip: Optional[bool] = True) -> Any:
    try:
        return remote_pickle.loads(
            _pickle.dumps(local_obj, 5, fix_imports=False),
            fix_imports=False
        )
    except TypeError:
        if silent_skip:
            # In case pickling is not possible, skip pickling silently
            return local_obj
        else:
            raise


def wrap_remote_call_by_value(func: Callable,
                              remote_pickle: ModuleType,
                              silent_skip: Optional[bool] = True):
    sig = _inspect.signature(func)

    def _by_value_wrapper(*args, **kwargs):
        sig.bind(*args, **kwargs)
        args = tuple(netdeliver(value, remote_pickle, silent_skip) for value in args)
        kwargs = {
            key: netdeliver(value, remote_pickle, silent_skip) for key, value in kwargs.items()
        }
        return netobtain(func(*args, **kwargs), remote_pickle, silent_skip)

    _by_value_wrapper.__signature__ = sig
    return _by_value_wrapper


class RpycByValueProxy(ObjectProxy):
    """ Instances of this class serve as proxies for qudi modules accessed via RPyC.
    It wraps all methods and attributes to send parameters and receive values "by value" instead
    of rpyc netref proxy objects. Therefore, all values are pickled by the sender and un-pickled by
    the receiver.

    Proxy class concept heavily inspired by this python recipe under PSF License:
    https://code.activestate.com/recipes/496741-object-proxying/
    """

    __slots__ = ['_remote_pickle']

    def __init__(self, obj: Any, remote_pickle: Optional[ModuleType] = None):
        super().__init__(obj)
        object.__setattr__(self, '_remote_pickle', remote_pickle)

    # proxying (special cases)
    def __getattribute__(self, name):
        remote_pickle = object.__getattribute__(self, '_remote_pickle')
        attr = super().__getattribute__(name)
        if remote_pickle is None:
            return attr
        if not name.startswith('__'):
            if _inspect.ismethod(attr) or _inspect.isfunction(attr):
                return wrap_remote_call_by_value(attr, remote_pickle)
            else:
                return netobtain(attr, remote_pickle)
        return attr

    def __setattr__(self, name, value):
        remote_pickle = object.__getattribute__(self, '_remote_pickle')
        if remote_pickle is not None:
            value = netdeliver(value, remote_pickle)
        return super().__setattr__(name, value)
