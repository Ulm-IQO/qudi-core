# -*- coding: utf-8 -*-
"""
Decorators and objects used for overloading attributes and interfacing them.

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

__all__ = ['OverloadedAttribute', 'OverloadProxy']

import weakref
import warnings
from typing import Any, Callable
from qudi.util.proxy import CachedObjectProxy


class _OverloadedAttributeMapper:
    def __init__(self):
        self._map_dict = dict()
        self._parent = lambda: None

    def add_mapping(self, key: str, obj: Any) -> None:
        self._map_dict[key] = obj

    def remove_mapping(self, key: str) -> None:
        del self._map_dict[key]

    @property
    def parent(self) -> Any:
        return self._parent()

    @parent.setter
    def parent(self, obj: Any) -> None:
        self._parent = weakref.ref(obj)

    def get_mapped(self, key: str) -> Any:
        if key not in self._map_dict:
            raise KeyError(f'No attribute overload found for key "{key}"')
        return self._map_dict[key]

    def __getitem__(self, key):
        mapped_obj = self.get_mapped(key)
        if hasattr(mapped_obj, '__get__'):
            return mapped_obj.__get__(self.parent)
        else:
            return mapped_obj

    def __setitem__(self, key, value):
        mapped_obj = self.get_mapped(key)
        if hasattr(mapped_obj, '__set__'):
            mapped_obj.__set__(self.parent, value)
        else:
            self._map_dict[key] = value

    def __delitem__(self, key):
        mapped_obj = self.get_mapped(key)
        if hasattr(mapped_obj, '__delete__'):
            mapped_obj.__delete__(self.parent)
        else:
            del self._map_dict[key]


class OverloadedAttribute:
    def __init__(self):
        self._attr_mapper = _OverloadedAttributeMapper()

    def overload(self, key: str) -> Callable[[Any], Any]:
        def decorator(attr):
            self._attr_mapper.add_mapping(key, attr)
            return self
        return decorator

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        self._attr_mapper.parent = instance
        return self._attr_mapper

    def __set__(self, instance, value):
        raise AttributeError('can\'t set attribute')

    def __delete__(self, instance):
        raise AttributeError('can\'t delete attribute')

    def setter(self, key: str) -> Callable[[Any], Any]:
        obj = self._attr_mapper.get_mapped(key)

        def decorator(attr):
            self._attr_mapper.add_mapping(key, obj.setter(attr))
            return self

        return decorator

    def getter(self, key: str) -> Callable[[Any], Any]:
        obj = self._attr_mapper.get_mapped(key)

        def decorator(attr):
            self._attr_mapper.add_mapping(key, obj.getter(attr))
            return self

        return decorator

    def deleter(self, key: str) -> Callable[[Any], Any]:
        obj = self._attr_mapper.get_mapped(key)

        def decorator(attr):
            self._attr_mapper.add_mapping(key, obj.deleter(attr))
            return self

        return decorator


class OverloadProxy(CachedObjectProxy):
    """ Instances of this class serve as proxies for objects containing attributes of type
    OverloadedAttribute. It can be used to hide the overloading mechanism by fixing the overloaded
    attribute access key in a OverloadProxy instance. This allows for interfacing an overloaded
    attribute in the object represented by this proxy by normal "pythonic" means without the
    additional key-mapping lookup usually required by OverloadedAttribute.
    """
    __warning_sent = False

    __slots__ = ['_overload_key']

    def __init__(self, obj: Any, overload_key: str):
        super().__init__(obj)
        object.__setattr__(self, '_overload_key', overload_key)

    # proxying (special cases)
    def __getattribute__(self, name):
        attr = super().__getattribute__(name)
        if isinstance(attr, _OverloadedAttributeMapper):
            return attr[object.__getattribute__(self, '_overload_key')]
        return attr

    def __delattr__(self, name):
        attr = super().__getattribute__(name)
        if isinstance(attr, _OverloadedAttributeMapper):
            del attr[object.__getattribute__(self, '_overload_key')]
            return
        super().__delattr__(name)

    def __setattr__(self, name, value):
        attr = super().__getattribute__(name)
        if isinstance(attr, _OverloadedAttributeMapper):
            attr[object.__getattribute__(self, '_overload_key')] = value
            return
        super().__setattr__(name, value)

    def __call__(self):
        if not OverloadProxy.__warning_sent:
            warnings.warn(
                'Calling a qudi module Connector meta attribute has been deprecated and will be '
                'removed in the future. Please use the connected module directly as a normal '
                'attribute.',
                DeprecationWarning,
                stacklevel=2
            )
            OverloadProxy.__warning_sent = True
        return self
