# -*- coding: utf-8 -*-
"""
StatusVar object for qudi modules to allow storing of application status variables on disk.
These variables get stored during deactivation of qudi modules and loaded back in during activation.

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

__all__ = ["StatusVar"]

import copy
import inspect
from typing import Callable, Any, Optional


class StatusVar:
    """This class defines a status variable that is loaded before activation and saved after
    deactivation.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        default: Optional[Any] = None,
        *,
        constructor: Optional[Callable] = None,
        representer: Optional[Callable] = None,
    ):
        """
        Parameters
        ----------
        name : str
            Identifier of the status variable when stored.
        default : Any
            Default value for the status variable when a saved version is not present.
        constructor : callable
            Constructor function for the variable; use for type checks or conversion.
        representer : callable
            Representer function for the status variable; use for saving conversion.
        """
        self.name = name
        self.default = default
        self.constructor_function = None
        self.representer_function = None
        if constructor is not None:
            self.constructor(constructor)
        if representer is not None:
            self.representer(representer)

    def __set_name__(self, owner, name):
        if self.name is None:
            self.name = name

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memodict={}):
        return self.copy()

    def copy(self, **kwargs):
        """Create a new instance of StatusVar with copied and updated values.

        Parameters
        ----------
        **kwargs : dict
            Additional or overridden parameters for the constructor of this class.
        """
        newargs = {
            "name": self.name,
            "default": copy.deepcopy(self.default),
            "constructor": self.constructor_function,
            "representer": self.representer_function,
        }
        newargs.update(kwargs)
        return StatusVar(**newargs)

    def constructor(self, func: Callable) -> Callable:
        """This is the decorator for declaring constructor function for this StatusVar.

        Parameters
        ----------
        func : callable
            Constructor function for this StatusVar.

        Returns
        -------
        callable
            The original function so this can be used as a decorator.
        """
        self.constructor_function = self._assert_func_signature(func)
        return func

    def representer(self, func: Callable) -> Callable:
        """This is the decorator for declaring a representer function for this StatusVar.

        Parameters
        ----------
        func : callable
            Representer function for this StatusVar.

        Returns
        -------
        callable
            The original function so this can be used as a decorator.
        """
        self.representer_function = self._assert_func_signature(func)
        return func

    @staticmethod
    def _assert_func_signature(func: Callable) -> Callable:
        assert callable(func), "StatusVar constructor/representer must be callable"
        params = tuple(inspect.signature(func).parameters)
        assert 0 < len(params) < 3, (
            "StatusVar constructor/representer must be function with "
            "1 (static) or 2 (bound method) parameters."
        )
        if len(params) == 1:

            def wrapper(instance, value):
                return func(value)

            return wrapper
        return func
