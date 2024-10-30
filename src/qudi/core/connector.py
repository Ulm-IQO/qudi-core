# -*- coding: utf-8 -*-
"""
Connector descriptor used to establish connections between qudi objects.

Copyright (c) 2021-2024, the qudi developers. See the AUTHORS.md file at the top-level directory of
this distribution and on <https://github.com/Ulm-IQO/qudi-core/>.

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
    """Error type related to qudi Connector meta attribute functionality."""
    pass


class Connector:
    """
    Descriptor object used to connect qudi objects with each other.

    Parameters
    ----------
    interface : type
        Interface type to enforce for this connector. The connection target will be checked to be
        an instance of this interface.
    name : str, optional
        Customizable connector name that will be used to reference it in the qudi module
        configuration (defaults to attribute name).
    optional : bool, optional
        If this flag is set to `True`, the connector will not raise an exception if no target is
        connected to it (defaults to `False`).
    """

    def __init__(self, interface: type, name: str = None, optional: bool = False):
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
        """Set attribute name as `name` if none has been given during `__init__`."""
        if self.name is None:
            self.name = name
        self.attr_name = name

    def __get__(self, instance, owner) -> Union[None, OverloadProxy, 'Connector']:
        """
        If called on a class, will return this descriptor instance itself. If called on an instance,
        will return the connection target (or `None` if optional and not connected).

        Raises
        ------
        QudiConnectionError
            If the connector is not optional but no target is connected.
        """
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
        """
        Connect the target qudi object instance to the object instance owning this connector and
        check if it is an instance of the specified interface

        Parameters
        ----------
        instance : object
            The qudi object instance owning this connector, i.e. the instance to act on.
        target : object, optional
            Qudi object instance to connect to this connector as target.

        Raises
        ------
        QudiConnectionError
            If the target can not be connected (already connected, wrong interface, is `None` but
            not optional).
        """
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
        """
        Disconnect the connector target from the object instance owning this connector. Ignored if
        not connected in the first place.

        Parameters
        ----------
        instance : object
            The qudi object instance owning this connector, i.e. the instance to act on.
        """
        try:
            del instance.__dict__[self.attr_name]
        except (KeyError, AttributeError):
            pass

    def is_connected(self, instance: object) -> bool:
        """
        Checks if the given module instance has this connector connected to a target object
        instance.

        Parameters
        ----------
        instance : object
            The qudi object instance owning this connector, i.e. the instance to act on.

        Returns
        -------
        bool
            `True` if a target instance has been connected, `False` otherwise.
        """
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
