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
from collections.abc import MutableMapping as AbstractMutableMapping

from .proxy import MappingProxy
from .validator import validate_config
from .file_handler import FileHandlerMixin
from ._modules import ModuleConfigMixin


class Configuration(FileHandlerMixin, ModuleConfigMixin, AbstractMutableMapping):  #QtCore.QObject):
    """
    """

    # sigConfigChanged = QtCore.Signal(object)

    def __init__(self,
                 configuration: Optional[MutableMapping[str, Any]] = None,
                 parent: Optional[QtCore.QObject] = None):
        # super().__init__(parent=parent)
        super().__init__()

        self._file_path = None

        # initialize config dict if given
        if configuration is None:
            self._config = dict()
        else:
            self._config = copy.deepcopy(configuration)

        # Validate config dict and fill in missing default values from schema
        self._validate()

    def _validate(self) -> None:
        """ Performs JSON schema validation on the current configuration mapping.
        Raises qudi.core.config.validator.ValidationError if the validation fails.
        """
        validate_config(self._config)
        # self.sigConfigChanged.emit(self)

    @property
    def config(self) -> MappingProxy:
        return MappingProxy(self._config, self._validate)

    @property
    def file_path(self):
        return self._file_path

    def __getitem__(self, key: str) -> Any:
        try:
            return self.config['global'][key]
        except KeyError:
            return self.config[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if key in self._config:
            self.config[key] = value
        else:
            self.config['global'][key] = value

    def __delitem__(self, key: str) -> None:
        try:
            del self.config['global'][key]
        except KeyError:
            del self.config[key]

    def __iter__(self):
        for key, sub_cfg in self._config.items():
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

        # Load YAML file from disk
        config = self._load_config_file(file_path)

        # Write current config file path to load.cfg in AppData if requested
        if set_default:
            self.set_default_config_path(file_path)

        self._file_path = file_path
        self._config = config
        # self.sigConfigChanged.emit(self)

    def dump_config(self, file_path=None):
        file_path = self._file_path if file_path is None else file_path
        if file_path is None:
            raise ValueError('No file path defined for qudi configuration to dump into')
        self._dump_config_file(file_path, self._config)
        self._file_path = file_path
