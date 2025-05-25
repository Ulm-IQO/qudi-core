# -*- coding: utf-8 -*-
"""
ConfigOption descriptor to be used in qudi objects.

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

__all__ = ['ConfigOption', 'MissingAction', 'QudiConfigOptionError']

from enum import Enum
from typing import Any, Optional, Callable, Union
from qudi.util.descriptors import DefaultAttribute


class QudiConfigOptionError(RuntimeError):
    """Error type related to qudi ConfigOption meta attribute functionality."""
    pass


class MissingAction(Enum):
    """Action policy for missing key in qudi configuration"""
    ERROR = 'error'
    WARN = 'warn'
    INFO = 'info'
    NOTHING = 'nothing'


class ConfigOption(DefaultAttribute):
    """
    This descriptor represents qudi object implementation-dependent configuration keys that can or
    must be configured in the qudi configuration for the specific qudi object. The value parsed
    from the configuration is then used to initialize this descriptor value on the owning qudi
    object instance.
    Qudi object attributes initialized in this way should be considered static and not change their
    value during runtime.

    Parameters
    ----------
    name : str, optional
        Customizable name key that will be used to reference it in the qudi configuration
        (defaults to attribute name).
    default : object, optional
        The default value to initialize if config option is not found in qudi configuration or if
        the initialization/conversion fails (default requires valid qudi config without fallback).
    missing : qudi.core.configoption.MissingAction, optional
        Keyword-only. Enum defining the behaviour of this config option in case it is missing from
        the qudi configuration (defaults to NOTHING if default value is set, ERROR otherwise).
    constructor : function, optional
        Keyword-only. Callable accepting the raw value from qudi configuration and converting it to
        the final value used to initialize this descriptor value (default is `None`). Can be used
        for complex initialization and sanity checking (by raising exceptions). The default value
        provided in this `__init__` will also be passed through the constructor upon construction.
    """

    _NO_VALUE = object()  # placeholder default argument

    @staticmethod
    def _sanitize_signature(func: Union[staticmethod, classmethod, Callable]) -> str:
        if isinstance(func, (staticmethod, classmethod)):
            return func.__func__.__name__
        elif callable(func):
            return func.__name__
        else:
            raise TypeError(
                'ConfigOption constructor must be callable, staticmethod or classmethod type'
            )

    def __init__(self,
                 name: Optional[str] = None,
                 default: Optional[Any] = _NO_VALUE,
                 *,
                 missing: Optional[Union[MissingAction, str]] = MissingAction.NOTHING,
                 constructor: Optional[Callable[[Any], Any]] = None):
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
        """
        Flag indicating if this ConfigOption can be initialized while missing from qudi
        configuration.
        """
        return self.missing_action != MissingAction.ERROR

    def __set_name__(self, owner, name):
        """Set attribute name as `name` if none has been given during `__init__`."""
        if self.name is None:
            self.name = name
        return super().__set_name__(owner, name)

    def construct(self, instance: object, value: Optional[Any] = _NO_VALUE) -> None:
        """
        Tries to initialize this descriptor value on the given qudi object instance.
        If no value is provided, the default value will be used instead. If no default has been
        provided, initialization will fail instead.
        If a constructor function has been set, call it on the value to initialize and proceed with
        the returned value. If the constructor raises an exception, initialization will fail.

        Parameters
        ----------
        instance : object
            The qudi object instance owning this config option, i.e. the instance to act on.
        value : object, optional
            Value to use for construction. This value usually comes from the qudi configuration.
            (default is the value provided in `__init__`)

        Raises
        ------
        QudiConfigOptionError
            If the construction fails due to MissingAction policy or exceptions in constructor
            callable.
        """
        # If no config value is given for construction, try to get the default value.
        # Raise exception if no default value is present and self.optional is False
        if value is self._NO_VALUE:
            cls = instance.__class__
            # Raise exception if no value is given and self.missing_action requires it
            if self.missing_action == MissingAction.ERROR:
                raise QudiConfigOptionError(
                    f'No value given to construct non-optional ConfigOption "{self.name}" on '
                    f'"{cls.__module__}.{cls.__name__}.{self.attr_name}"'
                ) from None
            # Take default value instead
            value = self.__get__(instance, instance.__class__)
            # Log messages if required by self.missing_action
            if self.missing_action != MissingAction.NOTHING:
                msg = (f'No value given to construct optional ConfigOption "{self.name}" on '
                       f'"{cls.__module__}.{cls.__name__}.{self.attr_name}".\n'
                       f'Using default value "{value}".')
                if self.missing_action == MissingAction.WARN:
                    instance.log.warning(msg)
                elif self.missing_action == MissingAction.INFO:
                    instance.log.info(msg)
        # Pass value to constructor and continue with returned value
        if self._constructor is not None:
            try:
                if isinstance(self._constructor, str):
                    value = getattr(instance, self._constructor)(value)
                else:
                    value = self._constructor(value)
            except Exception as err:
                raise QudiConfigOptionError(
                    f'Constructor callable failed during construction of ConfigOption '
                    f'"{self.name}" on "{cls.__module__}.{cls.__name__}.{self.attr_name}".'
                ) from err
        self.__set__(instance, value)

    def constructor(self,
                    func: Union[staticmethod, classmethod, Callable]
                    ) -> Union[staticmethod, classmethod, Callable]:
        """
        Decorator for declaring constructor function for this ConfigOption.

        Parameters
        ----------
        func : function
            Callable to be decorated and registered as constructor for this config option.

        Returns
        -------
        function
            The unaltered input function.
        """
        self._constructor = self._sanitize_signature(func)
        return func
