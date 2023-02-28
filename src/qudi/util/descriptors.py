# -*- coding: utf-8 -*-
"""
Descriptor objects that can be used to simplify common tasks related to object attributes.

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

__all__ = ['BaseAttribute', 'DefaultAttribute', 'ReadOnlyAttribute', 'DefaultMixin',
           'ReadOnlyMixin']

from copy import deepcopy
from typing import Any, Optional


class BaseAttribute:
    """ Base descriptor class implementing trivial get/set/delete behaviour for an instance
    attribute.
    """
    def __init__(self):
        super().__init__()
        self.attr_name = None

    def __set_name__(self, owner, name):
        self.attr_name = name

    def __get__(self, instance, owner):
        try:
            return instance.__dict__[self.attr_name]
        except KeyError:
            raise AttributeError(self.attr_name) from None
        except AttributeError:
            return self

    def __delete__(self, instance):
        try:
            del instance.__dict__[self.attr_name]
        except KeyError:
            raise AttributeError(self.attr_name) from None

    def __set__(self, instance, value):
        instance.__dict__[self.attr_name] = value


class DefaultMixin:
    """ Combine with other descriptor objects for default value behaviour in __get__. If no default
    value is specified, fall back to raising AttributeError.
    """
    _no_default = object()  # unique placeholder

    def __init__(self, *args, default: Optional[Any] = _no_default, **kwargs):
        super().__init__(*args, **kwargs)
        self.default = default

    def __get__(self, instance, owner):
        try:
            return super().__get__(instance, owner)
        except AttributeError:
            if self.default is self._no_default:
                raise
            super().__set__(instance, deepcopy(self.default))
            return super().__get__(instance, owner)

    def __delete__(self, instance):
        try:
            super().__delete__(instance)
        except AttributeError:
            pass


class ReadOnlyMixin:
    def __delete__(self, instance):
        raise AttributeError('Read-only attribute can not be deleted')

    def __set__(self, instance, value):
        raise AttributeError('Read-only attribute can not be overwritten')

    def set_value(self, instance: object, value: Any) -> None:
        super().__set__(instance, value)


class DefaultAttribute(DefaultMixin, BaseAttribute):
    """
    """
    def __init__(self, default: Optional[Any] = DefaultMixin._no_default):
        super().__init__(default=default)


class ReadOnlyAttribute(ReadOnlyMixin, DefaultAttribute):
    """
    """
    def __init__(self, value: Any):
        super().__init__(default=value)
