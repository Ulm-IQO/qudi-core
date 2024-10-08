# -*- coding: utf-8 -*-
"""
Connector object to establish connections between qudi objects.

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

__all__ = ['Connector', 'QudiConnectionError']

import importlib
from typing import Union
from qudi.util.overload import OverloadProxy


class QudiConnectionError(RuntimeError):
    pass


class Connector:
    """ A connector used to connect qudi objects with each other """

    def __init__(self, interface: type, name: str = None, optional: bool = False):
        """
        @param str interface: name of the interface class to connect to
        @param str name: optional, name of the connector in qudi config. Will set attribute name if
                         omitted.
        @param bool optional: optional, flag indicating if the connection is mandatory (False)
        """
        if not isinstance(interface, type):
            raise TypeError('Parameter "interface" must be an interface class')
        if name is not None:
            if not isinstance(name, str):
                raise TypeError('Parameter "name" must be str type or None')
            elif len(name) < 1:
                raise ValueError('Parameter "name" must be non-empty string')
        if not isinstance(optional, bool):
            raise TypeError('Parameter "optional" must be bool type')
        super().__init__()
        self.interface = interface
        self.name = name
        self.optional = optional
        self.attr_name = None

    def __set_name__(self, owner, name):
        if self.name is None:
            self.name = name
        self.attr_name = name

    def __get__(self, instance, owner) -> Union[None, OverloadProxy, 'Connector']:
        try:
            return instance.__dict__[self.attr_name]
        except KeyError:
            if self.optional:
                return None
            else:
                interface = f'{self.interface.__module__}.{self.interface.__qualname__}'
                raise QudiConnectionError(
                    f'Connector "{self.name}" (interface "{interface}") is not connected.'
                ) from None
        except AttributeError:
            return self

    def __delete__(self, instance):
        raise AttributeError('Connector attribute can not be deleted')

    def __set__(self, instance, value):
        raise AttributeError('Connector attribute can not be overwritten')

    def __repr__(self):
        connector = f'{self.__class__.__module__}.{self.__class__.__qualname__}'
        interface = f'{self.interface.__module__}.{self.interface.__qualname__}'
        return f'{connector}({interface}, "{self.name}", {self.optional})'

    def connect(self, instance: object, target: object) -> None:
        """ Check if target is connectible by this connector and connect. """
        if self.is_connected(instance):
            raise QudiConnectionError(
                f'Connector "{self.name}" on "{instance.__class__.__module__}.'
                f'{instance.__class__.__qualname__}.{self.attr_name}" already connected to a target'
            )
        elif target is None:
            if not self.optional:
                raise QudiConnectionError(
                    f'No target given for mandatory connector "{self.name}" on '
                    f'"{instance.__class__.__module__}.{instance.__class__.__qualname__}.'
                    f'{self.attr_name}"'
                )
        elif not self._target_complies_with_interface(target):
            raise QudiConnectionError(
                f'Connector target "{target}" is no instance of "{self.interface.__module__}.'
                f'{self.interface.__qualname__}" required by connector "{self.name}" on '
                f'"{instance.__class__.__module__}.{instance.__class__.__qualname__}.'
                f'{self.attr_name}"'
            )
        else:
            instance.__dict__[self.attr_name] = OverloadProxy(target, self.interface)

    def disconnect(self, instance: object) -> None:
        """ Disconnect connector. """
        try:
            del instance.__dict__[self.attr_name]
        except (KeyError, AttributeError):
            pass

    def is_connected(self, instance: object) -> bool:
        """ Checks if the given module instance has this Connector connected to a target module. """
        try:
            return instance.__dict__[self.attr_name] is not None
        except (KeyError, AttributeError):
            return False

    def _target_complies_with_interface(self, target) -> bool:
        target_qualname = type(target).__qualname__
        if not target_qualname.startswith('qudi.'):
            target_qualname = f'{type(target).__module__}.{target_qualname}'
        module_url, class_name = target_qualname.rsplit('.', 1)
        mod = importlib.import_module(module_url)
        target_cls = getattr(mod, class_name)
        return issubclass(target_cls, self.interface)


