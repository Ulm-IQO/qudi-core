# -*- coding: utf-8 -*-

"""
This file contains an object representing a qudi configuration.
Qudi configurations are stored in YAML file format.

Copyright (c) 2022, the qudi developers. See the AUTHORS.md file at the top-level directory of this
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

__all__ = ['Configuration', 'ValidationError', 'ParserError', 'YAMLError', 'DuplicateKeyError']

import copy
from numbers import Number
from PySide6 import QtCore
from typing import Mapping, Optional, Union, Sequence, Set, List, MutableMapping, Any
from collections.abc import MutableMapping as _MutableMapping
from qudi.core.meta import ABCQObjectMeta as _ABCQObjectMeta

from .validator import ValidationError
from .validator import validate_config as _validate_config
from .validator import validate_local_module_config as _validate_local_module_config
from .validator import validate_remote_module_config as _validate_remote_module_config
from .file_handler import ParserError, YAMLError, DuplicateKeyError
from .file_handler import FileHandlerBase as _FileHandlerBase


_OptionType = Union[Sequence, Mapping, Set, Number, str]


class Configuration(_FileHandlerBase,
                    _MutableMapping,
                    QtCore.QObject,
                    metaclass=_ABCQObjectMeta):
    """QObject subclass representing a valid qudi configuration.
    Handles config file loading/dumping as well as writing qudi load config to AppData.
    Performs JSON schema validation upon file loading/dumping and mutation.
    Includes interface methods to add/remove module configurations as well as getting/setting
    various config items.
    """
    sigConfigChanged = QtCore.Signal(object)  # self

    def __init__(self,
                 config: Optional[MutableMapping[str, Any]] = None,
                 parent: Optional[QtCore.QObject] = None
                 ) -> None:
        super().__init__(parent=parent)

        self._file_path = None  # File path for corresponding .cfg file
        self._config = None     # The raw configuration as dict

        # initialize and validate config dict
        self.set_config(config)

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

    @property
    def config_map(self) -> MutableMapping[str, Any]:
        """Deepcopy of the raw config dict."""
        return copy.deepcopy(self._config)

    @property
    def file_path(self) -> Union[None, str]:
        """File path of the associated .cfg file.
        Will be None if no file has been associated, i.e. no load/dump has been performed on this
        config.
        """
        return self._file_path

    def set_config(self, config: Union[None, MutableMapping[str, Any]]) -> None:
        """Validate and reset this Configuration with the given raw config dict.
        """
        new_config = dict() if config is None else copy.deepcopy(config)
        _validate_config(new_config)
        self._config = new_config
        self.sigConfigChanged.emit(self)

    def load(self, file_path: Optional[str] = None, set_default: Optional[bool] = False) -> None:
        """Load a config from file (.cfg), validate it (JSON schema) and reset this Configuration
        instance.

        If no "file_path" argument is given, try to determine the file path by the following
        priority and raise ValueError if no path could be found:
            1. Use "file_path" property if it is not None
            2. Use file path saved in AppData from previous qudi session
            3. Use existing "default.cfg" file in "<UserHome>/qudi/config/"
            4. Use existing "default.cfg" file in "<AppData>/qudi/"
        This instance is only reset on successful JSON schema validation of the loaded config.
        Will set the "file_path" property accordingly on success.

        If optional "set_default" flag is set, write the new file_path to "<AppData>/qudi/load.cfg"
        to be the new default config at the next start of qudi.
        """
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

    def dump(self, file_path: Optional[str] = None) -> None:
        """Dumps this Configuration instance to file (.cfg) after successful JSON schema
        validation.

        If no "file_path" argument is given, try to use the "file_path" property and raise
        ValueError if no path could be found.
        Will set the "file_path" property accordingly on success.
        """
        file_path = self._file_path if file_path is None else file_path
        if file_path is None:
            raise ValueError('No file path defined for qudi configuration to dump into')
        config = self.config_map
        _validate_config(config)
        self._dump(file_path, config)
        self._file_path = file_path

    def add_local_module(self,
                         base: str,
                         name: str,
                         module_class: str,
                         allow_remote: Optional[bool] = None,
                         connect: Optional[Mapping[str, str]] = None,
                         options: Optional[Mapping[str, _OptionType]] = None) -> None:
        """Mutates the current configuration by validating and adding a new local qudi module
        config with base "gui", "logic" or "hardware" of the form:
            <name>:
                module.Class: <module.Class>
                allow_remote: <allow_remote>
                options:
                    <options_key1>: <options_value1>
                    <options_key2>: <options_value2>
                    ...
                connect:
                    <connect_key1>: <connect_value1>
                    <connect_key2>: <connect_value1>
                    ...

        Raises KeyError if a module with the same name is already configured.
        """
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
                          native_module_name: str,
                          address: str,
                          port: int,
                          certfile: Optional[str] = None,
                          keyfile: Optional[str] = None) -> None:
        """Mutates the current configuration by validating and adding a new remote qudi module
        config with base "gui", "logic" or "hardware" of the form:
            <name>:
                native_module_name: <native_module_name>
                address: <address>
                port: <port>
                certfile: <certfile>
                keyfile: <keyfile>

        Raises KeyError if a module with the same name is already configured.
        """
        if self.module_configured(name):
            raise KeyError(f'Module with name "{name}" already configured')
        self.validate_module_base(base)
        module_config = {'native_module_name': native_module_name,
                         'address'           : address,
                         'port'              : port}
        if certfile is not None:
            module_config['certfile'] = certfile
        if keyfile is not None:
            module_config['keyfile'] = keyfile
        _validate_remote_module_config(module_config)
        new_config = self.config_map
        new_config[base][name] = module_config
        self.set_config(new_config)

    def rename_module(self, old_name: str, new_name: str) -> None:
        """Mutates the current configuration by validating and renaming an already configured
        module.

        Raises KeyError if a module with <new_name> is already configured or if <old_name> can not
        be found in the current config.
        """
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
        """Mutates the current configuration by deleting a configured module.

        Raises KeyError if no module is configured by given <name>.
        """
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
        """Checks if a module with given name is present in current configuration."""
        return name in self._config['gui'] or name in self._config['logic'] or name in self._config[
            'hardware']

    def module_config(self, name: str) -> MutableMapping[str, Any]:
        """Returns module configuration for given module <name>.

        Raises KeyError if no module is configured by given <name>.
        """
        for base in ['gui', 'logic', 'hardware']:
            try:
                return copy.deepcopy(self._config[base][name])
            except KeyError:
                pass
        raise KeyError(f'No module with name "{name}" configured')

    def is_remote_module(self, name: str) -> bool:
        """Checks whether a configured module is a remote module and returns answer flag.

        Raises KeyError if no module is configured by given <name>.
        """
        return 'native_module_name' in self.get_module_config(name)

    def is_local_module(self, name):
        """Checks whether a configured module is a local module and returns answer flag.

        Raises KeyError if no module is configured by given <name>.
        """
        return 'module.Class' in self.get_module_config(name)

    @property
    def module_names(self) -> List[str]:
        """List of the currently configured module names."""
        return [*self._config['gui'], *self._config['logic'], *self._config['hardware']]

    @staticmethod
    def validate_module_base(base: str) -> None:
        """Raises ValueError if the given string is no valid qudi module base."""
        if base not in ['gui', 'logic', 'hardware']:
            raise ValueError('qudi module base must be one of ["gui", "logic", "hardware"]')
