# -*- coding: utf-8 -*-

"""
Static file handler and mixin for handling qudi configuration files.

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

__all__ = ['FileHandler']


from typing import Any, Dict
from .validator import validate_config
from ._mixins import FileHandlerMixin as _FileHandlerMixin


class FileHandler(_FileHandlerMixin):
    """ Static standalone qudi configuration file handler. """

    @classmethod
    def load_config_file(cls, path: str) -> Dict[str, Any]:
        config = cls._load_config_file(path)
        validate_config(config)
        return config

    @classmethod
    def dump_config_file(cls, path: str, config: Dict[str, Any]) -> None:
        validate_config(config)
        cls._dump_config_file(path, config)
