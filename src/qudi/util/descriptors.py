# -*- coding: utf-8 -*-
"""
Descriptor objects that can be used to simplify common tasks related to object attributes.

Copyright (c) 2023, the qudi developers. See the AUTHORS.md file at the top-level directory of this
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

__all__ = ['BaseAttribute', 'DefaultAttribute', 'ReadOnlyAttribute', 'TypedAttribute',
           'CheckedAttribute', 'DefaultMixin', 'ReadOnlyMixin', 'TypedMixin', 'ValidateMixin']

from typing import Any, Optional, Iterable, Type, Callable, Union
from inspect import isclass, isfunction


class DefaultMixin:
    """ Mixin for BaseAttribute introducing optional default value behaviour in __get__.
    If no default value is specified, fall back to raising AttributeError.
    """
    _no_default = object()  # unique placeholder

    def __init__(self, default: Optional[Any] = _no_default, **kwargs):
        super().__init__(**kwargs)
        self.default = default

    def __get__(self, instance, owner):
        try:
            return super().__get__(instance, owner)
        except AttributeError:
            if self.default is self._no_default:
                raise
            return self.default

    def __delete__(self, instance):
        try:
            super().__delete__(instance)
        except AttributeError:
            pass


class ReadOnlyMixin:
    """ Mixin for BaseAttribute introducing read-only access """
    def __delete__(self, instance):
        raise AttributeError('Read-only attribute can not be deleted')

    def __set__(self, instance, value):
        raise AttributeError('Read-only attribute can not be overwritten')

    def set_value(self, instance: object, value: Any) -> None:
        super().__set__(instance, value)


class TypedMixin:
    """ Mixin for BaseAttribute introducing optional type checking via isinstance builtin """
    def __init__(self, valid_types: Optional[Iterable[Type]] = None, **kwargs):
        super().__init__(**kwargs)
        self.valid_types = None if valid_types is None else tuple(valid_types)
        if self.valid_types and not all(isclass(typ) for typ in self.valid_types):
            raise TypeError('valid_types must be iterable of types (classes)')

    def __set__(self, instance, value):
        self.check_type(value)
        super().__set__(instance, value)

    def check_type(self, value: Any) -> None:
        if self.valid_types and not isinstance(value, self.valid_types):
            raise TypeError(
                f'Value must be of type(s) [{", ".join(t.__name__ for t in self.valid_types)}]'
            )


class ValidateMixin:
    """ Mixin for BaseAttribute introducing optional validation via registering static and/or
    bound validator methods.
    Bound methods are best registered via the "validator" decorator (cooperative with
    staticmethod/classmethod decorator)
    """
    def __init__(self,
                 static_validators: Optional[Iterable[Callable[[Any], None]]] = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.static_validators = list() if static_validators is None else list(static_validators)
        self.bound_validators = list()
        if not all(callable(val) for val in self.static_validators):
            raise TypeError('static_validators must be iterable of callables')

    def __set__(self, instance, value):
        self.validate(value, instance)
        super().__set__(instance, value)

    def validator(self,
                  func: Union[staticmethod, classmethod, Callable[[Any], None]]
                  ) -> Union[staticmethod, classmethod, Callable[[Any], None]]:
        """ Decorator to register either a static or bound validator """
        # Use function reference directly if static
        if isinstance(func, staticmethod):
            self.static_validators.append(func.__func__)
            return func

        # In case of bound methods (class/instance) just use the attribute name string
        if isinstance(func, classmethod):
            func_obj = func.__func__
        elif isfunction(func):
            func_obj = func
            if func_obj.__qualname__ == func_obj.__name__:
                # Not a class member, thus probably static
                self.static_validators.append(func)
                return func
        else:
            raise TypeError('validator must either be function, staticmethod or classmethod object')

        # Take care of name mangling for private members
        if func_obj.__name__.startswith('__'):
            cls_name = func_obj.__qualname__.rsplit('.', 1)[0]
            self.bound_validators.append(f'_{cls_name}{func_obj.__name__}')
        else:
            self.bound_validators.append(func_obj.__name__)
        return func

    def validate(self, value: Any, instance: Optional[Any] = None) -> None:
        try:
            for func in self.static_validators:
                func(value)
            for func_name in self.bound_validators:
                try:
                    func = getattr(instance, func_name)
                except AttributeError:
                    raise AttributeError(
                        f'Registered bound validator "{func_name}" not found in {instance}'
                    ) from None
                func(value)
        except Exception as err:
            raise ValueError(f'Value "{value}" did not pass validation') from err


class BaseAttribute:
    """ Base descriptor class implementing trivial get/set/delete behaviour for an instance
    attribute.
    """
    def __init__(self):
        super().__init__()
        self.attr_name = None

    def __set_name__(self, owner, name):
        self.attr_name = name

    def __get__(self, instance, owner):
        try:
            return instance.__dict__[self.attr_name]
        except KeyError:
            raise AttributeError(self.attr_name) from None
        except AttributeError:
            return self

    def __delete__(self, instance):
        try:
            del instance.__dict__[self.attr_name]
        except KeyError:
            raise AttributeError(self.attr_name) from None

    def __set__(self, instance, value):
        instance.__dict__[self.attr_name] = value


class DefaultAttribute(DefaultMixin, BaseAttribute):
    """ Attribute that can be given a default value which is used if not explicitly initialized by
    the instance.

    Example usage:

        class Test:
            variable_a = DefaultAttribute(42)
            variable_b = DefaultAttribute()
            def __init__(self):
                self.variable_b = self.variable_a - 42
                assert self.variable_a == 42
                assert self.variable_b == 0
    """
    def __init__(self, default: Optional[Any] = DefaultMixin._no_default):
        super().__init__(default=default)


class ReadOnlyAttribute(ReadOnlyMixin, DefaultAttribute):
    """ Extension of DefaultAttribute to be read-only. A non-default value can be set by calling
    "set_value(instance, value)" on the descriptor instance.

    Example usage:

        class Test:
            variable_a = ReadOnlyAttribute(42)
            variable_b = ReadOnlyAttribute()
            def __init__(self):
                self.__class__.variable_b.set_value(self, self.variable_a - 42)
                assert self.variable_a == 42
                assert self.variable_b == 0
                # The following would raise an AttributeError
                # self.variable_b = 0
    """
    pass


class TypedAttribute(TypedMixin, DefaultAttribute):
    """ Extension of DefaultAttribute including type checking via isinstance. A given default
    value is not type-checked.

    Example usage:

        class Test:
            variable_a = TypedAttribute([int, float])
            variable_b = TypedAttribute([str], None)
            def __init__(self):
                assert self.variable_b is None
                self.variable_a = 42
                self.variable_b = 'hello world'
                assert self.variable_a == 42
                assert self.variable_b == 'hello world'
                # The following would raise TypeError
                # self.variable_a = self.variable_b = None
    """
    def __init__(self,
                 valid_types: Optional[Iterable[Type]] = None,
                 default: Optional[Any] = DefaultAttribute._no_default):
        super().__init__(valid_types=valid_types, default=default)


class CheckedAttribute(TypedMixin, ValidateMixin, DefaultAttribute):
    """ Extension of DefaultAttribute including optional validation via static or bound validator
    methods as well as optional type checking via "isinstance".
    A given default value is not validated. Type checking is performed before validation.
    Register bound validator methods via the CheckedAttribute.validator decorator. This decorator
    can be combined with classmethod/staticmethod decorators in any order.

    Example usage:

        def my_static_validator(value):
            if not (0 <= value <= 100):
                raise ValueError('Value must be number between 0 and 100')

        class Test:
            variable_a = CheckedAttribute([my_static_validator], [int, float], 0)
            variable_b = CheckedAttribute(valid_types=[str])
            _valid_strings = ['A', 'B', 'C']

            def __init__(self):
                self.variable_a = 66.7
                self.variable_b = 'B'
                assert self.variable_a == 66.7
                assert self.variable_b == 'B'
                # The following would raise ValueError
                # self.variable_a = 101
                # self.variable_b = 'D'

            @variable_b.validator
            @classmethod
            def _validate_variable_b(cls, value):
                if value not in cls._valid_strings:
                    raise ValueError(f'Invalid string. Valid strings are: {cls._valid_strings}')
    """
    def __init__(self,
                 static_validators: Optional[Iterable[Callable[[Any], None]]] = None,
                 valid_types: Optional[Iterable[Type]] = None,
                 default: Optional[Any] = DefaultAttribute._no_default):
        super().__init__(static_validators=static_validators,
                         valid_types=valid_types,
                         default=default)
