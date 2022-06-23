# -*- coding: utf-8 -*-

"""
This file contains a mixin class to provide a convenient interface for adding/removing qudi
modules to/from the configuration.

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

__all__ = ['ModuleConfigMixin', 'FileHandlerMixin']

import os
import copy
from numbers import Number
from typing import Mapping, Optional, Union, Sequence, Set, List, MutableMapping, Any, Dict

from qudi.util.paths import get_default_config_dir, get_appdata_dir
from qudi.util.yaml import yaml_dump, yaml_load

from .validator import validate_local_module_config, validate_remote_module_config


class ModuleConfigMixin:
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
        validate_local_module_config(module_config)
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
        validate_remote_module_config(module_config)
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


class FileHandlerMixin:
    """ File handler mixin class providing static methods for handling raw qudi configuration files.
    Also applies qudi configuration validation and default value insertion upon loading/dumping
    configuration files.
    """

    @classmethod
    def _load_config_file(cls, path: str) -> Dict[str, Any]:
        return yaml_load(cls.relative_to_absolute_path(path))

    @classmethod
    def _dump_config_file(cls, path: str, config: Dict[str, Any]) -> None:
        if not path.endswith('.cfg'):
            raise ValueError('Configuration file must have ".cfg" file extension.')
        path = cls.relative_to_absolute_path(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return yaml_dump(path, config)

    @classmethod
    def set_default_config_path(cls, path: str):
        # Write current config file path to load.cfg
        yaml_dump(
            os.path.join(get_appdata_dir(create_missing=True), 'load.cfg'),
            {'load_config_path': cls.relative_to_absolute_path(path)}
        )

    @staticmethod
    def get_saved_config_path() -> str:
        # Try loading config file path from last session
        load_cfg = yaml_load(os.path.join(get_appdata_dir(), 'load.cfg'), ignore_missing=True)
        file_path = load_cfg.get('load_config_path', '')
        if os.path.exists(file_path) and file_path.endswith('.cfg'):
            return file_path

        # Raise error if no last run config file could be found
        raise FileNotFoundError('No config file path saved from previous qudi sessions')

    @staticmethod
    def get_default_config_path() -> str:
        # Try default.cfg in user home directory
        file_path = os.path.join(get_default_config_dir(create_missing=False), 'default.cfg')
        if os.path.exists(file_path):
            return file_path

        # Fall back to default.cfg in qudi AppData directory if possible
        file_path = os.path.join(get_appdata_dir(create_missing=False), 'default.cfg')
        if os.path.exists(file_path):
            return file_path

        # Raise error if no config file could be found
        raise FileNotFoundError('No config file could be found in default directories')

    @staticmethod
    def relative_to_absolute_path(path):
        # absolute or relative path? Existing?
        if os.path.isabs(path) and os.path.exists(path):
            return path

        # relative path? Try relative to userdata dir, user home dir and relative to main dir
        for search_dir in [get_default_config_dir(), get_appdata_dir()]:
            new_path = os.path.abspath(os.path.join(search_dir, path))
            if os.path.exists(new_path):
                return new_path

        # Raise exception if no existing path can be determined
        raise FileNotFoundError(
            f'Qudi relative path "{path}" can not be resolved or does not exist.'
        )
