# -*- coding: utf-8 -*-
"""
Some sample value converters 

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

__all__ = ['NdarrayConverter','DatetimeConverter', 'FitParametersConverter']

import math
import numpy as np
from datetime import datetime
from typing import Any
import lmfit
from qudi.util.data_conversion import ValueConverter


class NdarrayConverter(ValueConverter):
    """Sample converter class for numpy ndarray to pass it as is

    qudi.util.yaml already stores ndarrays natively, so no conversion is needed.
    The converter exists because cattrs cannot structure an unknown type without one.
    
    """
    target = np.ndarray

    def unstructure(self, obj: np.ndarray) -> np.ndarray:
        return obj
    
    def structure(self, value:Any, type_:type) -> np.ndarray:
        return value


class DatetimeConverter(ValueConverter):
    """Datetimes are stored as native YAML timestamps; strings are accepted when loading."""
    target = datetime

    def unstructure(self, obj: datetime) -> datetime:
        return obj  # YAML stores it natively

    def structure(self, value: Any, type_: type) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)  # hand-edited or quoted values


class FitParametersConverter(ValueConverter):
    """Stores lmfit.Parameters as a readable mapping of parameter name to its settings."""
    target = lmfit.Parameters

    def unstructure(self, obj: lmfit.Parameters) -> dict[str, dict[str, Any]]:
        params = {}
        for name, param in obj.items():
            settings = {'value': param.value, 'vary': param.vary}
            if param.min != -math.inf:
                settings['min'] = param.min
            if param.max != math.inf:
                settings['max'] = param.max
            params[name] = settings
        return params

    def structure(self, value: dict[str, dict[str, Any]], type_: type) -> lmfit.Parameters:
        params = lmfit.Parameters()
        for name, settings in value.items():
            params.add(name, **settings)
        return params