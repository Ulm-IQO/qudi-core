# -*- coding: utf-8 -*-
"""
Base classes to create a transparent proxy wrapper around any Python object.

Copyright (c) 2023, the qudi developers. See the AUTHORS.md file at the top-level directory of this
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

__all__ = ['ObjectProxy', 'CachedObjectProxy', 'CachedObjectRpycByValueProxy']

from typing import Any
from functools import wraps
from inspect import signature, isfunction, ismethod

from qudi.util.network import netobtain


class ObjectProxy:
    """ Base proxy class that can be easily customized in subclass by overwriting __getattribute__,
    __setattr__ and __delattr__.
    This base implementation is completely transparent and just makes proxied object access less
    efficient.

    Proxy class concept heavily inspired by this python recipe under PSF License:
    https://code.activestate.com/recipes/496741-object-proxying/
    """

    __slots__ = ['_obj', '__weakref__']

    def __init__(self, obj: Any):
        super().__init__()
        object.__setattr__(self, '_obj', obj)

    # proxying (special cases)
    def __getattribute__(self, name):
        return getattr(object.__getattribute__(self, '_obj'), name)

    def __delattr__(self, name):
        return delattr(object.__getattribute__(self, '_obj'), name)

    def __setattr__(self, name, value):
        return setattr(object.__getattribute__(self, '_obj'), name, value)

    def __nonzero__(self):
        return bool(object.__getattribute__(self, '_obj'))

    def __str__(self):
        return str(object.__getattribute__(self, '_obj'))

    def __repr__(self):
        return repr(object.__getattribute__(self, '_obj'))

    def __hash__(self):
        return hash(object.__getattribute__(self, '_obj'))

    # factories
    _special_names = [
        '__abs__', '__add__', '__and__', '__call__', '__cmp__', '__coerce__', '__contains__',
        '__delitem__', '__delslice__', '__div__', '__divmod__', '__eq__', '__float__',
        '__floordiv__', '__ge__', '__getitem__', '__getslice__', '__gt__', '__hex__',
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
        """ creates a proxy for the given class """

        def make_method(method_name):
            def method(self, *args, **kwargs):
                obj = object.__getattribute__(self, '_obj')
                return getattr(obj, method_name)(*args, **kwargs)
            return method

        # Add all special names to this wrapper class if they are present in the original class
        namespace = dict()
        for name in cls._special_names:
            if hasattr(obj_class, name) and not hasattr(cls, name):
                namespace[name] = make_method(name)

        return type(f'{cls.__name__}({obj_class.__name__})', (cls,), namespace)

    def __new__(cls, obj: Any, *args, **kwargs):
        """ creates a proxy instance referencing `obj` """
        return object.__new__(cls._create_class_proxy(type(obj)))


class CachedObjectProxy(ObjectProxy):
    """ Same as ObjectProxy but caches created proxy classes for more efficient use if the same
    object type is proxied multiple times.
    Be careful using this together with dynamic reload or mutation of proxied classes.
    """

    def __new__(cls, obj: Any, *args, **kwargs):
        """ Calls base class __new__ in case no proxy class has been created for the proxied
        object type. Uses cached class otherwise. """
        obj_cls = type(obj)
        try:
            proxy_cls = cls._class_proxy_cache[obj_cls]
            proxy_inst = object.__new__(proxy_cls)
        except AttributeError:
            proxy_inst = super().__new__(cls, obj, *args, **kwargs)
            cls._class_proxy_cache = {obj_cls: type(proxy_inst)}
        except KeyError:
            proxy_inst = super().__new__(cls, obj, *args, **kwargs)
            cls._class_proxy_cache[obj_cls] = type(proxy_inst)
        return proxy_inst


class CachedObjectRpycByValueProxy(CachedObjectProxy):
    """ Same as CachedObjectProxy but it wraps all API methods (none-underscore-named methods)
    to only receive parameters "by value" by using qudi.util.network.netobtain.
    This will only work if all method arguments are "pickle-able" and can take a very long time for
    large arrays.
    In addition, all values passed to __setattr__ are received "by value" as well.
    """
    def __getattribute__(self, name):
        attr = super().__getattribute__(name)
        if not name.startswith('_') and ismethod(attr) or isfunction(attr):
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

    def __setattr__(self, name, value):
        return super().__setattr__(name, netobtain(value))

    @classmethod
    def _create_class_proxy(cls, obj_class: type):
        """ creates a proxy for the given class """

        def make_method(method_name):
            def method(self, *args, **kwargs):
                obj = object.__getattribute__(self, '_obj')
                args = [netobtain(arg) for arg in args]
                kwargs = {key: netobtain(val) for key, val in kwargs.items()}
                return getattr(obj, method_name)(*args, **kwargs)

            return method

        # Add all special names to this wrapper class if they are present in the original class
        namespace = dict()
        for name in cls._special_names:
            if hasattr(obj_class, name) and not hasattr(cls, name):
                namespace[name] = make_method(name)

        return type(f'{cls.__name__}({obj_class.__name__})', (cls,), namespace)
