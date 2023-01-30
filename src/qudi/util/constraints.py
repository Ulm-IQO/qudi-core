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

__all__ = ['ScalarConstraint']

from typing import Union, Optional, Tuple, Callable, Any
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
        self._check_value_type(default)
        for value in bounds:
            self._check_value_type(value)
        if increment is not None:
            self._check_value_type(increment)
        if checker is not None and not callable(checker):
            raise TypeError('checker must be eithe None or a callable accepting a single scalar '
                            'and returning a bool.')
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

    def is_valid(self, value: Union[int, float]) -> bool:
        try:
            self._check_value_type(value)
        except TypeError:
            return False

        if self._minimum <= value <= self._maximum:
            if self._checker is None:
                return True
            else:
                return self._checker(value)
        return False

    def clip(self, value: Union[int, float]) -> Union[int, float]:
        return min(self._maximum, max(self._minimum, value))

    def copy(self) -> object:
        return ScalarConstraint(default=self.default,
                                bounds=self.bounds,
                                increment=self.increment,
                                enforce_int=self.enforce_int,
                                checker=self._checker)

    def _check_value_type(self, value: Any) -> None:
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
