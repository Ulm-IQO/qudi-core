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

__all__ = ["Connector"]

import weakref
from typing import Any, Type, Union
from qudi.util.overload import OverloadProxy


class Connector:
    """A connector used to connect qudi modules with each other."""

    def __init__(
        self, interface: Union[str, Type], name: str = None, optional: bool = False
    ):
        """Initialize a Connector instance.

        Parameters
        ----------
        interface : Union[str, Type]
            Name of the interface class to connect to or the interface class itself.
        name : str, optional
            Name of the connector in qudi config. Will set attribute name if omitted.
        optional : bool, optional
            Flag indicating if the connection is mandatory (False by default).

        Raises
        ------
        AssertionError
            If `interface` is not a string or a type.
            If `name` is not `None` or a non-empty string.
            If `optional` is not a boolean.
        """
        assert isinstance(
            interface, (str, type)
        ), 'Parameter "interface" must be an interface class or the class name as str.'
        assert name is None or (
            isinstance(name, str) and name
        ), 'Parameter "name" must be non-empty str or None.'
        assert isinstance(optional, bool), 'Parameter "optional" must be bool type.'
        self.interface = interface if isinstance(interface, str) else interface.__name__
        self.name = name
        self.optional = optional
        self._obj_proxy = None
        self._obj_ref = lambda: None

    def __set_name__(self, owner, name):
        if self.name is None:
            self.name = name

    def __call__(self) -> Any:
        """Return reference to the module that this connector is connected to."""
        if self.is_connected:
            return self._obj_proxy
        if self.optional:
            return None
        raise RuntimeError(
            f'Connector "{self.name}" (interface "{self.interface}") is not connected.'
        )

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memodict={}):
        return self.copy()

    def __repr__(self):
        return f'{self.__module__}.Connector("{self.interface}", "{self.name}", {self.optional})'

    def __module_died_callback(self, ref=None):
        self.disconnect()

    @property
    def is_connected(self) -> bool:
        """Read-only property to check if the Connector instance is connected to a target module.

        Returns
        -------
        bool
            Connection status flag.
            - True: Connected
            - False: Disconnected
        """
        return self._obj_proxy is not None

    def connect(self, target: Any) -> None:
        """Check if target is connectible by this connector and connect."""
        bases = {cls.__name__ for cls in target.__class__.mro()}
        if self.interface not in bases:
            raise RuntimeError(
                f'Module "{target}" connected to connector "{self.name}" does not implement '
                f'interface "{self.interface}".'
            )
        self._obj_proxy = OverloadProxy(target, self.interface)
        self._obj_ref = weakref.ref(target, self.__module_died_callback)

    def disconnect(self) -> None:
        """Disconnect connector."""
        self._obj_proxy = None

    def copy(self, **kwargs):
        """Create a new instance of Connector with copied values and update"""
        return Connector(
            kwargs.get("interface", self.interface),
            kwargs.get("name", self.name),
            kwargs.get("optional", self.optional),
        )
