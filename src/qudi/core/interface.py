# -*- coding: utf-8 -*-
"""
Decorators and objects used for qudi interfaces

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

__all__ = ('ScalarConstraint',)

import warnings
warnings.warn('The "qudi.core.interface" module is deprecated and will soon be removed in future '
              'releases. Please use the objects contained in "qudi.util.constraints" instead.',
              DeprecationWarning,
              stacklevel=2)


class ScalarConstraint:
    """
    Constraint definition for a scalar variable hardware parameter.
    """
    def __init__(self, min=0.0, max=0.0, step=0.0, default=0.0, unit=''):
        # allowed minimum value for parameter
        self.min = min
        # allowed maximum value for parameter
        self.max = max
        # allowed step size for parameter value changes (for spinboxes etc.)
        self.step = step
        # the default value for the parameter
        self.default = default
        # the unit of the parameter value(optional)
        self.unit = unit
        return
