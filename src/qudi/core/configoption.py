# -*- coding: utf-8 -*-
"""
ConfigOption object to be used in qudi modules. The value of each ConfigOption can
(if it has a default value) or must be specified by the user in the config file.
Usually these values should be constant for the duration of a qudi session.

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

__all__ = ['ConfigOption', 'MissingAction']

from enum import Enum
from typing import Any, Optional, Callable, Union
from qudi.util.descriptors import DefaultAttribute


class MissingAction(Enum):
    """ Representation for missing ConfigOption """
    ERROR = 'error'
    WARN = 'warn'
    INFO = 'info'
    NOTHING = 'nothing'


class ConfigOption(DefaultAttribute):
    """ This class represents a configuration entry in the config file that is loaded before
    module initialisation.
    """

    _NO_VALUE = object()

    def __init__(self,
                 name: Optional[str] = None,
                 default: Optional[Any] = _NO_VALUE,
                 *,
                 missing: Optional[Union[MissingAction, str]] = MissingAction.NOTHING,
                 constructor: Optional[Callable] = None):
        """ Create a ConfigOption object.

        @param name: identifier of the option in the configuration file
        @param default: default value for the case that the option is not set in the config file
        @param missing: action to take when the option is not set. 'nothing' does nothing, 'warn'
                        logs a warning, 'error' logs an error and prevents the module from loading
        @param constructor: constructor function for complex config option behaviour
        """
        if default is self._NO_VALUE:
            super().__init__()
        else:
            super().__init__(default=default)
        self.name = name
        if default is self._NO_VALUE:
            self.missing_action = MissingAction.ERROR
        else:
            self.missing_action = MissingAction(missing)
        if constructor is None:
            self._constructor = None
        elif callable(constructor):
            self._constructor = constructor
        else:
            self._constructor = self._sanitize_signature(constructor)

    @property
    def optional(self) -> bool:
        return self.missing_action != MissingAction.ERROR

    def __set_name__(self, owner, name):
        if self.name is None:
            self.name = name
        return super().__set_name__(owner, name)

    def construct(self, instance: object, value: Optional[Any] = _NO_VALUE) -> None:
        # If no config value is given for construction, try to get the default value.
        # Raise exception if no default value is present and self.optional is False
        if value is self._NO_VALUE:
            try:
                value = self.__get__(instance, instance.__class__)
            except AttributeError:
                cls = instance.__class__
                raise RuntimeError(
                    f'No value given to construct non-optional ConfigOption "{self.name}" on '
                    f'"{cls.__module__}.{cls.__name__}.{self.attr_name}"'
                ) from None
        if self._constructor is not None:
            if isinstance(self._constructor, str):
                value = getattr(instance, self._constructor)(value)
            else:
                value = self._constructor(value)
        self.__set__(instance, value)

    def constructor(self,
                    func: Union[staticmethod, classmethod, Callable]
                    ) -> Union[staticmethod, classmethod, Callable]:
        """ This is the decorator for declaring constructor function for this StatusVar.

        @param func: constructor function for this StatusVar
        @return: return the original function so this can be used as a decorator
        """
        self._constructor = self._sanitize_signature(func)
        return func

    @staticmethod
    def _sanitize_signature(func: Union[staticmethod, classmethod, Callable]) -> str:
        if isinstance(func, (staticmethod, classmethod)):
            return func.__func__.__name__
        elif callable(func):
            return func.__name__
        else:
            raise TypeError('ConfigOption constructor must be callable, staticmethod or '
                            'classmethod type')

