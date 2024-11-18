# -*- coding: utf-8 -*-
"""
Check if something is a rpyc remotemodules object and transfer it

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

__all__ = ['netobtain']

import rpyc.core.netref as _netref
import rpyc.utils.classic as _classic


def netobtain(obj):
    """
    """
    if isinstance(obj, _netref.BaseNetref):
        return _classic.obtain(obj)
    return obj
