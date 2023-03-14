# -*- coding: utf-8 -*-
"""
Connector object to establish connections between qudi modules.

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

__all__ = ['Connector', 'ModuleConnectionError']

from typing import Any, Type, Union
from qudi.util.overload import OverloadProxy


class ModuleConnectionError(RuntimeError):
    pass


class Connector:
    """ A connector used to connect qudi modules with each other.
    """

    def __init__(self, interface: Union[str, Type], name: str = None, optional: bool = False):
        """
        @param str interface: name of the interface class to connect to
        @param str name: optional, name of the connector in qudi config. Will set attribute name if
                         omitted.
        @param bool optional: optional, flag indicating if the connection is mandatory (False)
        """
        if not isinstance(interface, (str, type)):
            raise TypeError(
                'Parameter "interface" must be an interface class or the class name as str'
            )
        if name is not None:
            if not isinstance(name, str):
                raise TypeError('Parameter "name" must be str type or None')
            elif len(name) < 1:
                raise ValueError('Parameter "name" must be non-empty string')
        if not isinstance(optional, bool):
            raise TypeError('Parameter "optional" must be bool type')
        super().__init__()
        self.interface = interface if isinstance(interface, str) else interface.__name__
        self.name = name
        self.optional = optional
        self.attr_name = None

    def __set_name__(self, owner, name):
        if self.name is None:
            self.name = name
        self.attr_name = name

    def __get__(self, instance, owner):
        try:
            return instance.__dict__[self.attr_name]
        except KeyError:
            if self.optional:
                return None
            raise ModuleConnectionError(
                f'Connector "{self.name}" (interface "{self.interface}") is not connected.'
            ) from None
        except AttributeError:
            return self

    def __delete__(self, instance):
        raise AttributeError('Connector attribute can not be deleted')

    def __set__(self, instance, value):
        raise AttributeError('Connector attribute can not be overwritten')

    def __repr__(self):
        return f'{self.__module__}.Connector("{self.interface}", "{self.name}", {self.optional})'

    def connect(self, instance: object, target: Any) -> None:
        """ Check if target is connectible by this connector and connect. """
        bases = {cls.__name__ for cls in target.__class__.mro()}
        if self.interface not in bases and target.__class__.__name__ != 'RemoteProxy':
            raise ModuleConnectionError(
                f'Module "{target}" does not implement interface "{self.interface}" required by '
                f'connector "{self.name}". Connection failed.'
            )
        if self.is_connected(instance):
            raise ModuleConnectionError(
                f'Connector "{self.name}" already connected to a target module. Connection failed.'
            )
        instance.__dict__[self.attr_name] = OverloadProxy(target, self.interface)

    def disconnect(self, instance: object) -> None:
        """ Disconnect connector. """
        try:
            del instance.__dict__[self.attr_name]
        except KeyError:
            pass

    def is_connected(self, instance: object) -> bool:
        """ Checks if the given module instance has this Connector connected to a target module. """
        try:
            return self.__get__(instance, instance.__class__) is not None
        except ModuleConnectionError:
            return False
