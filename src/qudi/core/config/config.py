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

__all__ = ['Configuration', 'ValidationError', 'ParserError']

import copy
from numbers import Number
from PySide2 import QtCore
from typing import Mapping, Optional, Union, Sequence, Set, List, MutableMapping, Any
from collections.abc import MutableMapping as _MutableMapping
from qudi.core.meta import ABCQObjectMeta as _ABCQObjectMeta

from .validator import ValidationError
from .validator import validate_config as _validate_config
from .validator import validate_local_module_config as _validate_local_module_config
from .validator import validate_remote_module_config as _validate_remote_module_config
from .file_handler import ParserError
from .file_handler import FileHandlerBase as _FileHandlerBase


class _ModuleConfigInterface:
    """ Mixin for adding and removing qudi modules from the qudi configuration.
    """
    _OptionType = Union[Sequence, Mapping, Set, Number, str]

    def add_local_module(self,
                         base: str,
                         name: str,
                         module_class: str,
                         allow_remote: Optional[bool] = None,
                         connect: Optional[Mapping[str, str]] = None,
                         options: Optional[Mapping[str, _OptionType]] = None) -> None:
        if self.module_configured(name):
            raise KeyError(f'Module with name "{name}" already configured')
        self.validate_module_base(base)
        module_config = {'module.Class': module_class}
        if allow_remote is not None:
            module_config['allow_remote'] = allow_remote
        if connect is not None:
            module_config['connect'] = copy.copy(connect)
        if options is not None:
            module_config['options'] = copy.deepcopy(options)
        _validate_local_module_config(module_config)
        new_config = self.config_map
        new_config[base][name] = module_config
        self.set_config(new_config)

    def add_remote_module(self,
                          base: str,
                          name: str,
                          remote_url: str,
                          certfile: Optional[str] = None,
                          keyfile: Optional[str] = None) -> None:
        if self.module_configured(name):
            raise KeyError(f'Module with name "{name}" already configured')
        self.validate_module_base(base)
        module_config = {'remote_url': remote_url}
        if certfile is not None:
            module_config['certfile'] = certfile
        if keyfile is not None:
            module_config['keyfile'] = keyfile
        _validate_remote_module_config(module_config)
        new_config = self.config_map
        new_config[base][name] = module_config
        self.set_config(new_config)

    def rename_module(self, old_name: str, new_name: str) -> None:
        if old_name == new_name:
            return
        if not self.module_configured(old_name):
            raise KeyError(f'No module with name "{old_name}" configured')
        if self.module_configured(new_name):
            raise KeyError(f'Module with name "{new_name}" already configured')

        new_config = self.config_map
        for base in ['gui', 'logic', 'hardware']:
            try:
                module_config = new_config[base].pop(old_name)
            except KeyError:
                continue
            else:
                new_config[base][new_name] = module_config
                self.set_config(new_config)
                return

    def remove_module(self, name: str) -> None:
        new_config = self.config_map
        for base in ['gui', 'logic', 'hardware']:
            try:
                del new_config[base][name]
            except KeyError:
                continue
            else:
                self.set_config(new_config)
                return
        raise KeyError(f'No module with name "{name}" configured')

    def module_configured(self, name: str) -> bool:
        """ Checks if a module with given name is present in current configuration """
        return name in self._config['gui'] or name in self._config['logic'] or name in self._config[
            'hardware']

    def module_config(self, name: str) -> MutableMapping[str, Any]:
        for base in ['gui', 'logic', 'hardware']:
            try:
                return copy.deepcopy(self._config[base][name])
            except KeyError:
                pass
        raise KeyError(f'No module with name "{name}" configured')

    def is_remote_module(self, name):
        return 'remote_url' in self.get_module_config(name)

    def is_local_module(self, name):
        return 'module.Class' in self.get_module_config(name)

    @property
    def module_names(self) -> List[str]:
        """ List of the currently configured module names. """
        return [*self._config['gui'], *self._config['logic'], *self._config['hardware']]

    @staticmethod
    def validate_module_base(base: str) -> None:
        if base not in ['gui', 'logic', 'hardware']:
            raise ValueError('qudi module base must be one of ["gui", "logic", "hardware"]')


class Configuration(_FileHandlerBase,
                    _ModuleConfigInterface,
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
        return max(0, len(self._config) + len(self._config['global']) - 1)

    def load(self, file_path=None, set_default=False):
        file_path = self._file_path if file_path is None else file_path
        # Try to restore last loaded config file path if possible
        if file_path is None:
            try:
                file_path = self.get_saved_path()
            except FileNotFoundError:
                try:
                    file_path = self.get_default_path()
                except FileNotFoundError:
                    pass
        if file_path is None:
            raise ValueError('No file path defined for configuration to load')

        # Load YAML file from disk.
        config = self._load(file_path)
        # validate config, add missing default values and set as current config.
        old_path = self._file_path
        try:
            self._file_path = file_path
            self.set_config(config)
        except ValidationError:
            self._file_path = old_path
            raise

        # Write current config file path to load.cfg in AppData if requested
        if set_default:
            self.set_default_path(file_path)

    def dump(self, file_path=None):
        file_path = self._file_path if file_path is None else file_path
        if file_path is None:
            raise ValueError('No file path defined for qudi configuration to dump into')
        config = self.config_map
        _validate_config(config)
        self._dump(file_path, config)
        self._file_path = file_path
