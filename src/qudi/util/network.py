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

__all__ = ['netobtain', 'netdeliver', 'RpycByValueProxy']


import pickle as _pickle
import inspect as _inspect
from rpyc.core.netref import BaseNetref as _BaseNetref
from typing import Any, Optional
from types import ModuleType


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


class RpycByValueProxy:
    """ Instances of this class serve as proxies for qudi modules accessed via RPyC.
    It wraps all methods and attributes to send parameters and receive values "by value" instead
    of rpyc netref proxy objects. Therefore, all values are pickled by the sender and un-pickled by
    the receiver.

    Proxy class concept heavily inspired by this python recipe under PSF License:
    https://code.activestate.com/recipes/496741-object-proxying/
    """

    __slots__ = ['_obj', '_remote_pickle', '__weakref__']

    def __init__(self, obj: Any, remote_pickle: Optional[ModuleType] = None):
        object.__setattr__(self, '_obj', obj)
        object.__setattr__(self, '_remote_pickle', remote_pickle)

    # proxying (special cases)
    def __getattribute__(self, name):
        obj = object.__getattribute__(self, '_obj')
        remote_pickle = object.__getattribute__(self, '_remote_pickle')
        attr = getattr(obj, name)
        if remote_pickle is None:
            return attr
        if not name.startswith('__'):
            if _inspect.ismethod(attr) or _inspect.isfunction(attr):
                sig = _inspect.signature(attr)

                def _by_value_call(*args, **kwargs):
                    sig.bind(*args, **kwargs)
                    args = tuple(netdeliver(value, remote_pickle) for value in args)
                    kwargs = {
                        key: netdeliver(value, remote_pickle) for key, value in kwargs.items()
                    }
                    return netobtain(attr(*args, **kwargs), remote_pickle)

                _by_value_call.__signature__ = sig
                return _by_value_call
            else:
                return netobtain(attr, remote_pickle)
        return attr

    def __delattr__(self, name):
        obj = object.__getattribute__(self, '_obj')
        return delattr(obj, name)

    def __setattr__(self, name, value):
        obj = object.__getattribute__(self, '_obj')
        remote_pickle = object.__getattribute__(self, '_remote_pickle')
        if remote_pickle is None:
            return setattr(obj, name, value)
        return setattr(obj, name, netdeliver(value, remote_pickle))

    def __nonzero__(self):
        return bool(object.__getattribute__(self, '_obj'))

    def __str__(self):
        return str(object.__getattribute__(self, '_obj'))

    def __repr__(self):
        return repr(object.__getattribute__(self, '_obj'))

    # factories
    _special_names = [
        '__abs__', '__add__', '__and__', '__call__', '__cmp__', '__coerce__', '__contains__',
        '__delitem__', '__delslice__', '__div__', '__divmod__', '__eq__', '__float__',
        '__floordiv__', '__ge__', '__getitem__', '__getslice__', '__gt__', '__hash__', '__hex__',
        '__iadd__', '__iand__', '__idiv__', '__idivmod__', '__ifloordiv__', '__ilshift__',
        '__imod__', '__imul__', '__int__', '__invert__', '__ior__', '__ipow__', '__irshift__',
        '__isub__', '__iter__', '__itruediv__', '__ixor__', '__le__', '__len__', '__long__',
        '__lshift__', '__lt__', '__mod__', '__mul__', '__ne__', '__neg__', '__oct__', '__or__',
        '__pos__', '__pow__', '__radd__', '__rand__', '__rdiv__', '__rdivmod__', '__reduce__',
        '__reduce_ex__', '__reversed__', '__rfloorfiv__', '__rlshift__', '__rmod__',
        '__rmul__', '__ror__', '__rpow__', '__rrshift__', '__rshift__', '__rsub__', '__rtruediv__',
        '__rxor__', '__setitem__', '__setslice__', '__sub__', '__truediv__', '__xor__', 'next',
    ]

    @classmethod
    def _create_class_proxy(cls, obj_class: type):
        """ creates a proxy for the given class
        """

        def make_method(method_name):
            def method(self, *args, **kwargs):
                obj = object.__getattribute__(self, '_obj')
                remote_pickle = object.__getattribute__(self, '_remote_pickle')
                if remote_pickle is not None:
                    args = tuple(netdeliver(value, remote_pickle) for value in args)
                    kwargs = {
                        key: netdeliver(value, remote_pickle) for key, value in kwargs.items()
                    }
                return getattr(obj, method_name)(*args, **kwargs)
            return method

        # Add all special names to this wrapper class if they are present in the original class
        namespace = dict()
        for name in cls._special_names:
            if hasattr(obj_class, name):
                namespace[name] = make_method(name)

        return type(f'{cls.__name__}({obj_class.__name__})', (cls,), namespace)

    def __new__(cls, obj: Any, *args, **kwargs):
        """ creates a proxy instance referencing `obj`. (obj, *args, **kwargs) are passed to this
        class' __init__, so deriving classes can define an __init__ method of their own.

        note: _class_proxy_cache is unique per class (each deriving class must hold its own cache)
        """
        return object.__new__(cls._create_class_proxy(obj.__class__))
