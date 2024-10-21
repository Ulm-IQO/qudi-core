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

__all__ = ['StatusVar']


from typing import Callable, Any, Optional, Union
from qudi.util.descriptors import DefaultAttribute


class StatusVar(DefaultAttribute):
    """ This class defines a status variable that is loaded before activation and saved after
    deactivation.
    """

    _NO_VALUE = object()

    def __init__(self,
                 name: Optional[str] = None,
                 default: Optional[Any] = None,
                 *,
                 constructor: Optional[Callable] = None,
                 representer: Optional[Callable] = None):
        """
        @param name: identifier of the status variable when stored
        @param default: default value for the status variable when a saved version is not present
        @param constructor: constructor function for variable; use for type checks or conversion
        @param representer: representer function for status variable; use for saving conversion
        """
        super().__init__(default=default)
        self.name = name
        if constructor is None:
            self._constructor = None
        elif callable(constructor):
            self._constructor = constructor
        else:
            self._constructor = self._sanitize_signature(constructor)
        if representer is None:
            self._representer = None
        elif callable(representer):
            self._representer = constructor
        else:
            self._representer = self._sanitize_signature(representer)

    def __set_name__(self, owner, name):
        if self.name is None:
            self.name = name
        return super().__set_name__(owner, name)

    def construct(self, instance: object, value: Optional[Any] = _NO_VALUE) -> None:
        if value is self._NO_VALUE:
            value = super().__get__(instance, instance.__class__)
        if self._constructor is not None:
            if isinstance(self._constructor, str):
                value = getattr(instance, self._constructor)(value)
            else:
                value = self._constructor(value)
        super().__set__(instance, value)

    def represent(self, instance: object) -> Any:
        value = super().__get__(instance, instance.__class__)
        if self._representer is not None:
            if isinstance(self._representer, str):
                value = getattr(instance, self._representer)(value)
            else:
                value = self._representer(value)
        return value

    def constructor(self, func: Callable) -> Callable:
        """ This is the decorator for declaring constructor function for this StatusVar.

        @param func: constructor function for this StatusVar
        @return: return the original function so this can be used as a decorator
        """
        self._constructor = self._sanitize_signature(func)
        return func

    def representer(self, func: Callable) -> Callable:
        """ This is the decorator for declaring a representer function for this StatusVar.

        @param func: representer function for this StatusVar
        @return: return the original function so this can be used as a decorator
        """
        self._representer = self._sanitize_signature(func)
        return func

    @staticmethod
    def _sanitize_signature(func: Union[staticmethod, classmethod, Callable]) -> str:
        # in case of staticmethod and classmethod objects
        if isinstance(func, (staticmethod, classmethod)):
            return func.__func__.__name__
        elif callable(func):
            name = func.__name__
            if name.startswith('__'):
                cls_name = func.__qualname__.rsplit('.', 2)[-2]
                name = f'_{cls_name}{name}'
            return name
        else:
            raise TypeError('StatusVar constructor/representer must be callable, staticmethod or '
                            'classmethod type')
