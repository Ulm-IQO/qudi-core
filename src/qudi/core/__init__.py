# -*- coding: utf-8 -*-
"""
This file contains the Qudi Manager class.

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

__all__ = ['StatusVar', 'ConfigOption', 'Connector', 'Base', 'LogicBase', 'GuiBase', 'get_logger']

import os
from importlib import metadata
__version__ = metadata.version('qudi-core')

# Set QT_API environment variable to PySide6
os.environ['QT_API'] = 'pyside6'

from qudi.core.statusvariable import StatusVar
from qudi.core.configoption import ConfigOption
from qudi.core.connector import Connector
from qudi.core.module import Base, LogicBase, GuiBase
from qudi.core.logger import get_logger
