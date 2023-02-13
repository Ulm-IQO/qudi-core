# -*- coding: utf-8 -*-
"""
This file contains Qudi methods for handling real-world values with units.

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

__all__ = ['ScalarConstraint', 'CheckedAttribute', 'TypedAttribute']

from inspect import isclass, signature
from typing import Union, Optional, Tuple, Callable, Any, Type, Iterable
from qudi.util.helpers import is_float, is_integer


class ScalarConstraint:
    """
    """
    def __init__(self,
                 default: Union[int, float],
                 bounds: Tuple[Union[int, float], Union[int, float]],
                 increment: Optional[Union[int, float]] = None,
                 enforce_int: Optional[bool] = False,
                 checker: Optional[Callable[[Union[int, float]], bool]] = None
                 ) -> None:
        """
        """
        self._enforce_int = bool(enforce_int)
        self.check_value_type(default)
        for value in bounds:
            self.check_value_type(value)
        if increment is not None:
            self.check_value_type(increment)
        if checker is not None and not callable(checker):
            raise TypeError('checker must be either None or a callable accepting a single scalar '
                            'and returning a valid-flag bool or raising ValueError')
        self._default = default
        self._minimum, self._maximum = sorted(bounds)
        self._increment = increment
        self._checker = checker

        if not self.is_valid(self._default):
            raise ValueError(f'invalid default value ({self._default}) encountered')

    @property
    def bounds(self) -> Tuple[Union[int, float], Union[int, float]]:
        return self._minimum, self._maximum

    @property
    def minimum(self) -> Union[int, float]:
        return self._minimum

    @property
    def maximum(self) -> Union[int, float]:
        return self._maximum

    @property
    def default(self) -> Union[int, float]:
        return self._default

    @property
    def increment(self) -> Union[None, int, float]:
        return self._increment

    @property
    def enforce_int(self) -> bool:
        return self._enforce_int

    def check(self, value: Union[int, float]) -> None:
        self.check_value_type(value)
        self.check_value_range(value)
        self.check_custom(value)

    def is_valid(self, value: Union[int, float]) -> bool:
        try:
            self.check(value)
        except (ValueError, TypeError):
            return False
        return True

    def clip(self, value: Union[int, float]) -> Union[int, float]:
        return min(self._maximum, max(self._minimum, value))

    def copy(self) -> object:
        return ScalarConstraint(default=self.default,
                                bounds=self.bounds,
                                increment=self.increment,
                                enforce_int=self.enforce_int,
                                checker=self._checker)

    def check_custom(self, value: Any) -> None:
        if (self._checker is not None) and (not self._checker(value)):
            raise ValueError(f'Custom checker failed to validate value "{value}"')

    def check_value_range(self, value: Union[int, float]) -> None:
        if not (self._minimum <= value <= self._maximum):
            raise ValueError(f'Value "{value}" is out of bounds {self.bounds}')

    def check_value_type(self, value: Any) -> None:
        if self._enforce_int:
            if not is_integer(value):
                raise TypeError(f'values must be int type (received {value})')
        else:
            if not (is_integer(value) or is_float(value)):
                raise TypeError(f'values must be int or float type (received {value})')

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        module = self.__class__.__module__
        return f'{module}.{cls}(' \
               f'default={self.default}, ' \
               f'bounds={self.bounds}, ' \
               f'increment={self.increment}, ' \
               f'enforce_int={self.enforce_int}, ' \
               f'checker={self._checker})'

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memodict={}):
        new_obj = self.copy()
        memodict[id(self)] = new_obj
        return new_obj

    # Backwards compatibility properties:
    @default.setter
    def default(self, value: Union[int, float]):
        if not self.is_valid(value):
            raise ValueError(f'invalid default value ({value}) encountered')
        self._default = value

    @property
    def min(self) -> Union[int, float]:
        return self._minimum

    @min.setter
    def min(self, value: Union[int, float]):
        self._minimum = value

    @property
    def max(self) -> Union[int, float]:
        return self._maximum

    @max.setter
    def max(self, value: Union[int, float]):
        self._maximum = value

    @property
    def step(self) -> Union[None, int, float]:
        return self._increment

    @step.setter
    def step(self, value: Union[None, int, float]):
        self._increment = value


class CheckedAttribute:
    """ Descriptor to perform customizable, automatic sanity checks on a class attribute value
    assignment. Performs sanity checking via provided validator callables.

    Example usage:

        def custom_validate(value):
            if not value.startswith('foo') or not value.endswith('bar'):
                raise ValueError('String must start with "foo" and end with "bar"')

        class Test:
            my_custom = CheckedAttribute([custom_validate])
            def __init__(self):
                self.my_custom = 'foo bar'
                # Following assignment would raise
                # self.my_custom = 'This fails validator'
    """
    def __init__(self, static_validators: Optional[Iterable[Callable[[Any], None]]] = None):
        self.attr_name = ''
        self.static_validators = list() if static_validators is None else list(static_validators)
        self.bound_validators = list()
        if not all(callable(val) for val in self.static_validators):
            raise TypeError('static_validators must be iterable of callables')

    def __set_name__(self, owner, name):
        self.attr_name = name

    def __get__(self, instance, owner):
        if instance:
            try:
                return instance.__dict__[self.attr_name]
            except KeyError:
                raise AttributeError(self.attr_name) from None
        else:
            return self

    def __delete__(self, instance):
        try:
            del instance.__dict__[self.attr_name]
        except KeyError:
            raise AttributeError(self.attr_name) from None

    def __set__(self, instance, value):
        # Custom validator evaluation
        try:
            for validator in self.static_validators:
                validator(value)
            for bound_name in self.bound_validators:
                try:
                    validator = getattr(instance, bound_name)
                except AttributeError:
                    raise AttributeError(
                        f'Registered bound validator "{bound_name}" not found in {instance}'
                    ) from None
                validator(value)
        except Exception as err:
            raise ValueError(f'Value of "{self.attr_name}" did not pass validation:') from err
        instance.__dict__[self.attr_name] = value

    def validator(self, func: Union[Callable[[Any, Any], None], Callable[[Any], None]]) -> Callable:
        """ Decorator to register either a static or bound validator """
        if callable(func):
            if len(signature(func).parameters) == 1:
                self.static_validators.append(func)
            else:
                self.bound_validators.append(func.__name__)
        else:
            self.bound_validators.append(func.__func__.__name__)
        return func


class TypedAttribute(CheckedAttribute):
    """ Extends CheckedAttribute so that you can easily include type checking via isinstance()
    builtin before the optional user-provided checker functions are called.

    Example usage:

        def custom_validate(value):
            if not value.startswith('foo') or not value.endswith('bar'):
                raise ValueError('String must start with "foo" and end with "bar"')

        class Test:
            my_string = CheckedAttribute([str])
            my_number = CheckedAttribute([int, float])
            my_custom = CheckedAttribute([str], static_validators=[custom_validate])
            def __init__(self):
                self.my_string = 'I am a test string'
                self.my_number = 42
                self.my_custom = 'foo bar'
                # Following assignments would raise
                # self.my_string = 42
                # self.my_number = None
                # self.my_custom = 'It is a string but it fails custom validator'
    """
    def __init__(self, valid_types: Optional[Iterable[Type]] = None, **kwargs):
        self.valid_types = tuple() if valid_types is None else tuple(valid_types)
        if not all(isclass(typ) for typ in self.valid_types):
            raise TypeError('valid_types must be iterable of types (classes)')
        kwargs['static_validators'] = [self.check_types, *kwargs.get('static_validators', list())]
        super().__init__(**kwargs)

    def check_types(self, value: Any) -> None:
        if self.valid_types and not isinstance(value, self.valid_types):
            raise TypeError(f'{self.attr_name} value must be of type(s) '
                            f'{[typ.__name__ for typ in self.valid_types]}')
