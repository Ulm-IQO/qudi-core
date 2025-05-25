# -*- coding: utf-8 -*-
"""
StatusVar descriptor to be used in qudi objects.

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

__all__ = ['StatusVar']


from typing import Callable, Any, Optional, Union
from qudi.util.descriptors import DefaultAttribute


class StatusVar(DefaultAttribute):
    """
    Descriptor attribute for qudi objects to allow persistent storage of variable values in AppData
    on disk. Qudi object attributes initialized this way can be treated as normal member variables
    during runtime and will be dumped to file seemingly at random times.

    Parameters
    ----------
    name : str, optional
        Customizable name that will be used as key in the dumped AppData file (defaults to attribute
        name).
    default : object, optional
        The default value to initialize if no previous AppData could be found or if the
        initialization/construction fails (defaults to `None`).
    constructor : function, optional
        Keyword-only. Callable accepting the value loaded from AppData or default value and
        converting it to the final value used to initialize this descriptor value (not used by
        default). Can be used for complex initialization and sanity checking (by raising
        exceptions). The default value provided in this `__init__` will also be passed through the
        constructor upon construction.
    representer : function, optional
        Keyword-only. Callable accepting the current variable value and converting it to the final
        value used to dump to AppData file (not used by default). Can be used to bring a complex
        variable type into something more suitable to represent in YAML files. Make sure this
        callable does not raise or the variable can not be saved in AppData.
    """

    _NO_VALUE = object()  # placeholder default argument

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
            raise TypeError(
                'StatusVar constructor/representer must be callable, staticmethod or classmethod '
                'type.'
            )

    def __init__(self,
                 name: Optional[str] = None,
                 default: Optional[Any] = None,
                 *,
                 constructor: Optional[Callable] = None,
                 representer: Optional[Callable] = None):
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
        """Set attribute name as `name` if none has been given during `__init__`."""
        if self.name is None:
            self.name = name
        return super().__set_name__(owner, name)

    def construct(self, instance: object, value: Optional[Any] = _NO_VALUE) -> None:
        """
        Tries to initialize this descriptor value on the given qudi object instance.
        If no value is provided, the default value will be used instead.
        If a constructor function has been set, call it on the value to initialize and proceed with
        the returned value. If the constructor raises an exception, initialization will fail.

        Parameters
        ----------
        instance : object
            The qudi object instance owning this status variable, i.e. the instance to act on.
        value : object, optional
            Value to use for construction. This value usually comes from a qudi AppData file.
            (default is the value provided in `__init__`)
        """
        if value is self._NO_VALUE:
            value = super().__get__(instance, instance.__class__)
        if self._constructor is not None:
            if isinstance(self._constructor, str):
                value = getattr(instance, self._constructor)(value)
            else:
                value = self._constructor(value)
        super().__set__(instance, value)

    def represent(self, instance: object) -> Any:
        """
        Tries to convert the current descriptor value of the given qudi object instance to be ready
        for dumping to file.
        If no representer callable has been set, does nothing and just passes through the current
        value.

        Parameters
        ----------
        instance : object
            The qudi object instance owning this status variable, i.e. the instance to act on.

        Returns
        -------
        object
            The value to represent this variable in a qudi AppData file.
        """
        value = super().__get__(instance, instance.__class__)
        if self._representer is not None:
            if isinstance(self._representer, str):
                value = getattr(instance, self._representer)(value)
            else:
                value = self._representer(value)
        return value

    def constructor(self, func: Callable) -> Callable:
        """
        Decorator for declaring a constructor function for this status variable.

        Parameters
        ----------
        func : function
            Callable to be decorated and registered as constructor for this status variable.

        Returns
        -------
        function
            The unaltered input function.
        """
        self._constructor = self._sanitize_signature(func)
        return func

    def representer(self, func: Callable) -> Callable:
        """
        Decorator for declaring a representer function for this status variable.

        Parameters
        ----------
        func : function
            Callable to be decorated and registered as representer for this status variable.

        Returns
        -------
        function
            The unaltered input function.
        """
        self._representer = self._sanitize_signature(func)
        return func
