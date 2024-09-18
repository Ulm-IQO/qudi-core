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

__all__ = ['ScalarConstraint', 'DiscreteScalarConstraint']

from typing import Union, Optional, Tuple, Callable, Any, Set
from qudi.util.helpers import is_float, is_integer
import numpy as np


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
        """
        Returns the interval within values are valid in this constraint.

        Returns
        -------
        Tuple([int, float], [int, float])
        """
        return self._minimum, self._maximum

    @property
    def minimum(self) -> Union[int, float]:
        """
        Returns minimum allowed value.

        Returns
        -------
        int, float
        """
        return self._minimum

    @property
    def maximum(self) -> Union[int, float]:
        """
        Returns maximum allowed value.

        Returns
        -------
        int, float
        """
        return self._maximum

    @property
    def default(self) -> Union[int, float]:
        """
        Returns default value.

        Returns
        -------
        int, float
        """
        return self._default

    @property
    def increment(self) -> Union[None, int, float]:
        """
        Returns the increment between values that is normally used.
        This is often used for the increment in e.g. QSpinBox.

        Returns
        -------
        int, float
        """
        return self._increment

    @property
    def enforce_int(self) -> bool:
        """
        Returns whether only integer values are allowed.

        Returns
        -------
        bool
        """
        return self._enforce_int

    def check(self, value: Union[int, float]) -> None:
        """
        Method that checks whether the given value is allowed by the constraint by calling various checker functions.
        If a checker function fails it will raise an Exception, indicating what is wrong with the value.

        Parameters
        ----------
            int, float
                value to check

        Returns
        -------
        None
        """

        self.check_value_type(value)
        self.check_value_range(value)
        self.check_custom(value)

    def is_valid(self, value: Union[int, float]) -> bool:
        """
        Method that checks whether the given value is valid.

        Parameters
        ----------
            int, float
                value to check

        Returns
        -------
        bool
            Is the value valid or not
        """
        try:
            self.check(value)
        except (ValueError, TypeError):
            return False
        return True

    def clip(self, value: Union[int, float]) -> Union[int, float]:
        """
        Method that clips the given value at the bounds of the constraint.

        Parameters
        ----------
            int, float
                value to clip

        Returns
        -------
        int, float
            value if in bounds, or the minimum or maximum allowed value
        """
        return min(self._maximum, max(self._minimum, value))

    def copy(self) -> object:
        """
        Method copies this ScalarConstraint instance.

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

    def check_custom(self, value: Any) -> None:
        """
        Method that checks the given value with the supplied custom checker function.

        Parameters
        ----------
            int, float
                value to check

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If checker function returns False.
        """
        if (self._checker is not None) and (not self._checker(value)):
            raise ValueError(f'Custom checker failed to validate value "{value}"')

    def check_value_range(self, value: Union[int, float]) -> None:
        """
        Method that checks the given value if it is in bounds.

        Parameters
        ----------
            int, float
                value to check

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If value out of bounds.
        """
        if not (self._minimum <= value <= self._maximum):
            raise ValueError(f'Value "{value}" is out of bounds {self.bounds}')

    def check_value_type(self, value: Any) -> None:
        """
        Method that checks the given value if it is in bounds.

        Parameters
        ----------
            int, float
                value to check

        Returns
        -------
        None

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
        """
        Method that gives a readable representation of this constraint.

        Returns
        -------
        str
            Readable representation of the constraint.
        """
        cls = self.__class__.__name__
        module = self.__class__.__module__
        return f'{module}.{cls}(' \
               f'default={self.default}, ' \
               f'bounds={self.bounds}, ' \
               f'increment={self.increment}, ' \
               f'enforce_int={self.enforce_int}, ' \
               f'checker={self._checker})'

    def __copy__(self):
        """
        Returns the copy of this instance.

        Returns
        -------
        ScalarConstraint
            Copy of this instance
        """
        return self.copy()

    def __deepcopy__(self, memodict={}):
        """
        Returns the deepcopy of this instance.

        Returns
        -------
        ScalarConstraint
            Deepcopy of this instance
        """
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


class DiscreteScalarConstraint(ScalarConstraint):
    """ """

    def __init__(
        self,
        default: Union[int, float],
        value_set: Optional[Set[Union[int, float]]] = None,
        bounds: Optional[Tuple[Union[int, float], Union[int, float]]] = None,
        increment: Optional[Union[int, float]] = None,
        enforce_int: Optional[bool] = False,
        checker: Optional[Callable[[Union[int, float]], bool]] = None,
        precision: Optional[float] = None,
    ) -> None:
        """ """
        if value_set is not None:
            self._value_set = value_set
            if bounds is not None:
                raise ValueError(
                    "Parameters value_set and bounds are both set simultaneously. Don't specify bounds as they are calculated from min and max value of value_set."
                )
            bounds = (min(self._value_set), max(self._value_set))

        elif bounds is not None and increment is not None:
            bounds = sorted(bounds)
            self._value_set = set(np.arange(bounds[0], bounds[1], increment))

        else:
            raise ValueError(
                "Parameters value_set, bounds and increment are None. Please specify either value_set or bounds and increment."
            )

        self._precision = precision
        super().__init__(default, bounds, increment, enforce_int, checker)

        if not self.is_valid(self._default):
            raise ValueError(f"invalid default value ({self._default}) encountered")

    @property
    def value_set(self) -> Set[Union[int, float]]:
        """
        Returns the set of values that the constraint allows.

        Returns
        -------
        set([int, float])
        """
        return self._value_set

    @property
    def precision(self) -> float:
        """
        Returns the precision with which floating point discrete values are checked for equality.

        Returns
        -------
        float
        """
        return self._precision

    def check(self, value: Union[int, float]) -> None:
        """
        Method that utilizes the check function of ScalarConstraint and expands it by checking whether the given value is in the discrete value set.

        Parameters
        ----------
            int, float
                value to check

        Returns
        -------
        None
        """
        super().check(value)
        self.check_value_set(value)

    def check_value_set(self, value: Union[int, float]):
        """
        Method that checks whether the given value is in the discrete value set.

        Parameters
        ----------
            int, float
                value to check

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If value is not in discrete value set.
        """
        if value in self.value_set:
            return

        if self.precision is not None:
            for val in self.value_set:
                if abs(val - value) < abs(self.precision):
                    return

        raise ValueError(f"Value {value} is not in allowed discrete value set.")

    def copy(self) -> object:
        """
        Method copies this DiscreteScalarConstraint instance.

        Returns
        -------
        DiscreteScalarConstraint
            Copy of this instance
        """
        return DiscreteScalarConstraint(
            default=self.default,
            value_set=self.value_set,
            bounds=self.bounds,
            increment=self.increment,
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
            f"value_set={self.value_set}, "
            f"bounds={self.bounds}, "
            f"increment={self.increment}, "
            f"enforce_int={self.enforce_int}, "
            f"checker={self._checker},"
            f"precision={self.precision})"
        )
