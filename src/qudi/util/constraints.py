# -*- coding: utf-8 -*-
"""
This file contains Qudi methods for handling real-world values with units.

Copyright (c) 2021-2024, the qudi developers. See the AUTHORS.md file at the top-level directory of
this distribution and on <https://github.com/Ulm-IQO/qudi-core/>

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

__all__ = ['ScalarConstraint', 'DiscreteScalarConstraint']

import warnings
from bisect import bisect_left
from typing import Union, Optional, Tuple, Callable, Any, Iterable

from qudi.util.helpers import is_float, is_integer



class ScalarConstraint:
    """
    Immutable helper object representing the numeric constraints for a scalar number within a
    certain continuous value range.
    Has built-in helper methods to check values against the constraints or clip them to the nearest
    allowed value.

    Attributes
    ----------
    bounds
    minimum
    maximum
    default
    increment
    enforce_int

    Parameters
    ----------
    default : int or float
        Default value to use for this scalar.
    bounds : tuple
        Min and max boundary (inclusive) for the allowed value range.
    increment : int or float, optional
        Default natural step size for value changes. Only used as additional information and not
        for value checking.
    enforce_int : bool, optional
        Flag indicating if this scalar should be enforced to be of integer type
    checker : callable, optional
        Custom checker function to accept a scalar value and raise ValueError or TypeError on fail.
    """
    def __init__(self,
                 default: Union[int, float],
                 bounds: Tuple[Union[int, float], Union[int, float]],
                 increment: Optional[Union[int, float]] = None,
                 enforce_int: Optional[bool] = False,
                 checker: Optional[Callable[[Union[int, float]], bool]] = None
                 ) -> None:
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
        """
        Interval (inclusive) for valid value range.

        Returns
        -------
        int or float
            Minimum allowed value
        int or float
            Maximum allowed value
        """
        return self._minimum, self._maximum

    @property
    def minimum(self) -> Union[int, float]:
        """
        Minimum allowed value.

        Returns
        -------
        int or float
        """
        return self._minimum

    @property
    def maximum(self) -> Union[int, float]:
        """
        Maximum allowed value.

        Returns
        -------
        int or float
        """
        return self._maximum

    @property
    def default(self) -> Union[int, float]:
        """
        Default fallback value.

        Returns
        -------
        int or float
        """
        return self._default

    @property
    def increment(self) -> Union[None, int, float]:
        """
        Natural increment to increase/decrease values. This is often used in a GUI, e.g. QSpinBox.

        Returns
        -------
        int or float
        """
        return self._increment

    @property
    def enforce_int(self) -> bool:
        """
        Flag indicating if this scalar should be enforced to be of integer type

        Returns
        -------
        bool
        """
        return self._enforce_int

    def check(self, value: Union[int, float]) -> None:
        """
        Checks whether the given value is allowed by the constraint by calling various checker
        functions. If a checker function fails it will raise an Exception, indicating what is wrong
        with the checked value.

        Parameters
        ----------
        value : int or float
            value to check

        Raises
        ------
        ValueError
            If the value is incompatible with the constraints
        TypeError
            If the value type is incompatible with the constraints, e.g. in case of
            enforce_int == True
        """
        self.check_value_type(value)
        self.check_value_range(value)
        self.check_custom(value)

    def is_valid(self, value: Union[int, float]) -> bool:
        """
        Checks whether the given value is valid.

        Parameters
        ----------
        value : int or float
            value to check

        Returns
        -------
        bool
        """
        try:
            self.check(value)
        except (ValueError, TypeError):
            return False
        return True

    def clip(self, value: Union[int, float]) -> Union[int, float]:
        """
        Clips the given value to the nearest valid value.

        Parameters
        ----------
        value : int or float
            value to clip

        Returns
        -------
        int or float
        """
        return min(self._maximum, max(self._minimum, value))

    def copy(self) -> object:
        """
        Copies this ScalarConstraint instance.

        Returns
        -------
        ScalarConstraint
            Copy of this instance
        """
        return ScalarConstraint(default=self.default,
                                bounds=self.bounds,
                                increment=self.increment,
                                enforce_int=self.enforce_int,
                                checker=self._checker)

    def check_custom(self, value: Union[int, float]) -> None:
        """
        Checks the given value with the supplied custom checker function.

        Parameters
        ----------
        value : int or float
            value to check

        Raises
        ------
        ValueError
            If custom checker fails to validate.
        TypeError
            If custom checker fails to validate.
        """
        if (self._checker is not None) and (not self._checker(value)):
            raise ValueError(f'Custom checker failed to validate {value}')

    def check_value_range(self, value: Union[int, float]) -> None:
        """
        Checks the given value if it is in bounds.

        Parameters
        ----------
        value : int or float
            value to check

        Raises
        ------
        ValueError
            If value out of bounds.
        """
        if not (self._minimum <= value <= self._maximum):
            raise ValueError(f'Value "{value}" is out of bounds {self.bounds}')

    def check_value_type(self, value: Any) -> None:
        """
        Checks the given value if it is in bounds.

        Parameters
        ----------
        value : int or float
            value to check

        Raises
        ------
        TypeError
            If value is not int or float or if _enforce_int is set if it is not int.
        """
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
        """
        .. deprecated:: 1.3.0
            constraints should be immutable. Pass all values to :py:func:`__init__` instead.
        """
        warnings.warn('ScalarConstraint should be immutable. Pass all values to __init__ instead.',
                      DeprecationWarning,
                      stacklevel=2)
        if not self.is_valid(value):
            raise ValueError(f'invalid default value ({value}) encountered')
        self._default = value

    @property
    def min(self) -> Union[int, float]:
        """
        .. deprecated:: 1.3.0
            ScalarConstraint.min will be removed in the near future. Use ScalarConstraint.minimum
            instead.
        """
        warnings.warn('ScalarConstraint.min will be removed in the near future. '
                      'Use ScalarConstraint.minimum instead.',
                      DeprecationWarning,
                      stacklevel=2)
        return self._minimum

    @min.setter
    def min(self, value: Union[int, float]):
        """
        .. deprecated:: 1.3.0
            constraints should be immutable. Pass all values to :py:func:`__init__` instead.
        """
        warnings.warn('ScalarConstraint should be immutable. Pass all values to __init__ instead.',
                      DeprecationWarning,
                      stacklevel=2)
        self._minimum = value

    @property
    def max(self) -> Union[int, float]:
        """
        .. deprecated:: 1.3.0
            ScalarConstraint.max will be removed in the near future. Use ScalarConstraint.maximum
            instead.
        """
        warnings.warn('ScalarConstraint.max will be removed in the near future. '
                      'Use ScalarConstraint.maximum instead.',
                      DeprecationWarning,
                      stacklevel=2)
        return self._maximum

    @max.setter
    def max(self, value: Union[int, float]):
        """
        .. deprecated:: 1.3.0
            constraints should be immutable. Pass all values to :py:func:`__init__` instead.
        """
        warnings.warn('ScalarConstraint should be immutable. Pass all values to __init__ instead.',
                      DeprecationWarning,
                      stacklevel=2)
        self._maximum = value

    @property
    def step(self) -> Union[None, int, float]:
        """
        .. deprecated:: 1.3.0
            ScalarConstraint.step will be removed in the near future. Use ScalarConstraint.increment
            instead.
        """
        warnings.warn('ScalarConstraint.step will be removed in the near future. '
                      'Use ScalarConstraint.increment instead.',
                      DeprecationWarning,
                      stacklevel=2)
        return self._increment

    @step.setter
    def step(self, value: Union[None, int, float]):
        """
        .. deprecated:: 1.3.0
            constraints should be immutable. Pass all values to :py:func:`__init__` instead.
        """
        warnings.warn('ScalarConstraint should be immutable. Pass all values to __init__ instead.',
                      DeprecationWarning,
                      stacklevel=2)
        self._increment = value


class DiscreteScalarConstraint(ScalarConstraint):
    """
    Specialization of ScalarConstraint for arbitrary discrete sets of allowed scalar values.

    Attributes
    ----------
    allowed_values
    precision
    default
    enforce_int

    Parameters
    ----------
    default : int or float
        Default value to use for this scalar.
    allowed_values : iterable
        Complete collection of allowed scalar values.
    precision : float, optional
        Maximum deviation a checked value is allowed to have from the nearest valid value (default
        is exact matching)
    enforce_int : bool, optional
        Flag indicating if this scalar should be enforced to be of integer type
    checker : callable, optional
        Custom checker function to accept a scalar value and raise ValueError or TypeError on fail.
    """

    def __init__(
        self,
        default: Union[int, float],
        allowed_values: Iterable[Union[int, float]],
        precision: Optional[float] = None,
        enforce_int: Optional[bool] = False,
        checker: Optional[Callable[[Union[int, float]], bool]] = None,
    ) -> None:
        # sort tuple for efficient checking
        self._allowed_values = tuple(sorted(set(allowed_values)))
        self._precision = None if (precision is None or precision == 0) else abs(precision)
        if len(self._allowed_values) == 0:
            raise ValueError('Must provide at least one allowed value')
        if not all(isinstance(val, int) for val in self._allowed_values):
            raise TypeError('Allowed values must be int type for `enforce_int == True`')
        super().__init__(
            default=default,
            bounds=(min(self._allowed_values), max(self._allowed_values)),
            enforce_int=enforce_int,
            checker=checker,
        )

    @property
    def allowed_values(self) -> Tuple[Union[int, float], ...]:
        """
        Discrete collection of values that the constraint allows.

        Returns
        -------
        tuple
        """
        return self._allowed_values

    @property
    def precision(self) -> float:
        """
        Precision with which floating point discrete values are checked for equality.

        Returns
        -------
        float
        """
        return self._precision

    def check(self, value: Union[int, float]) -> None:
        super().check(value)
        self.check_allowed_values(value)

    def check_allowed_values(self, value: Union[int, float]) -> None:
        """
        Method that checks whether the given value is in the set of allowed discrete values.

        Parameters
        ----------
        value : int or float
            value to check

        Raises
        ------
        ValueError
            If value is not in discrete value set.
        """
        closest_allowed = self._find_closest_value(value)
        # Use == operator here since checking for identity can lead to problems with proxy objects
        if closest_allowed != value:
            if self.precision is not None and abs(closest_allowed - value) < self.precision:
                pass
            else:
                raise ValueError(f"Value {value} is not in allowed discrete value set.")

    def clip(self, value: Union[int, float]) -> Union[int, float]:
        return self._find_closest_value(value)

    def copy(self) -> 'DiscreteScalarConstraint':
        """
        Method copies this DiscreteScalarConstraint instance.

        Returns
        -------
        DiscreteScalarConstraint
            Copy of this instance
        """
        return DiscreteScalarConstraint(
            default=self.default,
            allowed_values=self.allowed_values,
            enforce_int=self.enforce_int,
            checker=self._checker,
            precision=self.precision,
        )

    def __repr__(self) -> str:
        """
        Method that gives a readable representation of this constraint.

        Returns
        -------
        str
            Readable representation of the constraint.
        """
        cls = self.__class__.__name__
        module = self.__class__.__module__
        return (
            f"{module}.{cls}("
            f"default={self.default}, "
            f"allowed_values={self.allowed_values}, "
            f"enforce_int={self.enforce_int}, "
            f"checker={self._checker},"
            f"precision={self.precision})"
        )

    def _find_closest_value(self, value: Union[int, float]) -> Union[int, float]:
        """Find allowed value closest to given value"""
        pos = bisect_left(self._allowed_values, value)
        if pos == 0:
            closest = self._allowed_values[pos]
        elif pos == len(self._allowed_values):
            closest = self._allowed_values[-1]
        else:
            before = self._allowed_values[pos - 1]
            after = self._allowed_values[pos]
            if value - before >= after - value:
                closest = after
            else:
                closest = before
        return closest
