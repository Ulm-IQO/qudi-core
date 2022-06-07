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

from typing import Union, Optional, Tuple
from qudi.util.helpers import is_float, is_integer


class ScalarConstraint:
    """
    """
    def __init__(self,
                 default: Union[int, float],
                 bounds: Tuple[Union[int, float], Union[int, float]],
                 increment: Optional[Union[int, float]] = None
                 ) -> None:
        """
        """
        if not (is_integer(default) or is_float(default)):
            raise TypeError('default value must be int or float type')
        if not all(is_integer(val) or is_float(val) for val in bounds):
            raise TypeError('bounds must contain only int or float type values')
        if not ((increment is None) or is_integer(increment) or is_float(increment)):
            raise TypeError('increment value must be int or float type (or None)')
        self._default = default
        self._minimum, self._maximum = sorted(bounds)
        self._increment = increment if increment else None
        if not self.in_range(self._default):
            raise ValueError(f'default value ({self._default}) outside of bounds '
                             f'[{self._minimum}, {self._maximum}]')

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

    def in_range(self, value: Union[int, float]) -> bool:
        return self._minimum <= value <= self._maximum

    def clip(self, value: Union[int, float]) -> Union[int, float]:
        return min(self._maximum, max(self._minimum, value))
