# -*- coding: utf-8 -*-

"""
This file contains an object representing a qudi configuration.
Qudi configurations are stored in YAML file format.

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

__all__ = ['Configuration']

import copy
from PySide2 import QtCore
from typing import Any, Optional, MutableMapping, Union
from collections.abc import MutableMapping as _MutableMapping
from qudi.core.meta import ABCQObjectMeta as _ABCQObjectMeta

from .validator import validate_config as _validate_config
from ._mixins import ModuleConfigMixin as _ModuleConfigMixin
from ._mixins import FileHandlerMixin as _FileHandlerMixin


class Configuration(_FileHandlerMixin,
                    _ModuleConfigMixin,
                    _MutableMapping,
                    QtCore.QObject,
                    metaclass=_ABCQObjectMeta):
    """
    """
    sigConfigChanged = QtCore.Signal(object)

    def __init__(self, config: Optional[MutableMapping[str, Any]] = None):
        super().__init__()

        self._file_path = None
        self._config = None

        # initialize and validate config dict
        self.set_config(config)

    @property
    def config_map(self) -> MutableMapping[str, Any]:
        return copy.deepcopy(self._config)

    def set_config(self, config: Union[None, MutableMapping[str, Any]]) -> None:
        new_config = dict() if config is None else copy.deepcopy(config)
        _validate_config(new_config)
        self._config = new_config
        self.sigConfigChanged.emit(self)

    @property
    def file_path(self):
        return self._file_path

    def __repr__(self) -> str:
        return f'Configuration({repr(self._config)})'

    def __str__(self) -> str:
        return f'Configuration({str(self._config)})'

    def __getitem__(self, key: str) -> Any:
        try:
            return copy.deepcopy(self._config['global'][key])
        except KeyError:
            return copy.deepcopy(self._config[key])

    def __setitem__(self, key: str, value: Any) -> None:
        new_config = self.config_map
        if key in new_config:
            new_config[key] = value
        else:
            new_config['global'][key] = value
        self.set_config(new_config)

    def __delitem__(self, key: str) -> None:
        new_config = self.config_map
        try:
            del new_config[key]
        except KeyError:
            del new_config['global'][key]
        self.set_config(new_config)

    def __iter__(self):
        for key, sub_cfg in self.config_map.items():
            if key == 'global':
                yield from sub_cfg
            else:
                yield key

    def __len__(self) -> int:
        return len(self._config) + len(self._config['global']) - 1

    def load_config(self, file_path=None, set_default=False):
        file_path = self._file_path if file_path is None else file_path
        # Try to restore last loaded config file path if possible
        if file_path is None:
            try:
                file_path = self.get_saved_config_path()
            except FileNotFoundError:
                try:
                    file_path = self.get_default_config_path()
                except FileNotFoundError:
                    pass
        if file_path is None:
            raise ValueError('No file path defined for configuration to load')

        # Load YAML file from disk.
        config = self._load_config_file(file_path)
        # validate config, add missing default values and set as current config.
        old_path = self._file_path
        try:
            self._file_path = file_path
            self.set_config(config)
        except:
            self._file_path = old_path
            raise

        # Write current config file path to load.cfg in AppData if requested
        if set_default:
            self.set_default_config_path(file_path)

    def dump_config(self, file_path=None):
        file_path = self._file_path if file_path is None else file_path
        if file_path is None:
            raise ValueError('No file path defined for qudi configuration to dump into')
        config = self.config_map
        _validate_config(config)
        self._dump_config_file(file_path, config)
        self._file_path = file_path
