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

__all__ = ['ConfigurationSection']

import re
from typing import List, Any, Mapping, Optional

from .items import *


class ConfigurationSection:
    """
    """

    def __init__(self, config: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__()
        if config is not None:
            self.update()
            for key, value in config.items():
                try:
                    setattr(self, key, value)
                except AttributeError:
                    pass

    @classmethod
    def _is_config_item(cls, name) -> bool:
        return isinstance(cls.__dict__.get(name.lstrip('_'), None), AbstractConfigurationItem)

    @classmethod
    def _config_item_names(cls) -> List[str]:
        return [name for name, attr in cls.__dict__.items() if
                isinstance(attr, AbstractConfigurationItem)]

    def __setattr__(self, name, value):
        if self._is_config_item(name) or hasattr(self, name) or hasattr(self, name.lstrip('_')):
            super().__setattr__(name, value)
        else:
            raise AttributeError(f'No "{self.__class__.__name__}" member with name "{name}". '
                                 f'Can not set new "{self.__class__.__name__}" items')

    def __delattr__(self, name):
        raise AttributeError(f'Can not delete "{self.__class__.__name__}" members')

    def __getitem__(self, key):
        if not key.startswith('_') and self._is_config_item(key):
            return getattr(self, key)
        raise KeyError(f'No "{self.__class__.__name__}" item with name "{key}"')

    def __setitem__(self, key, value):
        if not key.startswith('_') and self._is_config_item(key):
            return setattr(self, key, value)
        raise KeyError(f'No "{self.__class__.__name__}" item with name "{key}". '
                       f'Can not set new "{self.__class__.__name__}" items.')

    def __delitem__(self, key):
        raise KeyError(f'Can not delete "{self.__class__.__name__}" items')

    def __len__(self):
        return len(self._config_item_names())

    def __iter__(self):
        return self.keys()

    def keys(self):
        for key in self._config_item_names():
            yield key

    def values(self):
        for key in self._config_item_names():
            yield getattr(self, key)

    def items(self):
        for key in self._config_item_names():
            yield key, getattr(self, key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def update(self, mapping=None, /, **kwargs) -> None:
        if mapping is None:
            if kwargs:
                mapping = kwargs
            else:
                return
        elif kwargs:
            mapping = mapping.copy()
            mapping.update(kwargs)
        allowed_keys = self._config_item_names()
        if not all(key in allowed_keys for key in mapping):
            raise KeyError(f'Invalid "{self.__class__.__name__}" item encountered.')
        for key, value in mapping.items():
            self[key] = value


class GlobalConfiguration(ConfigurationSection):
    """
    """

    startup_modules = StrListConfigurationItem()
    remote_modules_server = MappingConfigurationItem()
    namespace_server_port = IntConfigurationItem()
    force_remote_calls_by_value = BoolConfigurationItem()
    hide_manager_window = BoolConfigurationItem()
    stylesheet = StrConfigurationItem()
    daily_data_dirs = BoolConfigurationItem()
    default_data_dir = StrConfigurationItem()
    extension_paths = StrListConfigurationItem()

    def __init__(self, config: Optional[Mapping[str, Any]] = None) -> None:
        self.startup_modules = list()
        self.remote_modules_server = {'address': 'localhost',
                                      'port'   : 12345}
        self.namespace_server_port = 18861
        self.force_remote_calls_by_value = True
        self.hide_manager_window = False
        self.stylesheet = 'qdark.qss'
        self.daily_data_dirs = True
        self.default_data_dir = None
        self.extension_paths = None
        super().__init__(config=config)


class LocalModuleConfiguration(ConfigurationSection):
    """
    """
    module_class = StrConfigurationItem()
    allow_remote = BoolConfigurationItem()
    connect = MappingConfigurationItem()
    options = MappingConfigurationItem()

    def __init__(self, config: Optional[Mapping[str, Any]] = None) -> None:
        self.module_class = None
        self.allow_remote = False
        self.connect = None
        self.options = None
        super().__init__(config=config)


class RemoteModuleConfiguration(ConfigurationSection):
    """
    """
    remote_url = StrConfigurationItem()
    keyfile = StrConfigurationItem()
    certfile = StrConfigurationItem()

    def __init__(self, config: Optional[Mapping[str, Any]] = None) -> None:
        self.remote_url = None
        self.keyfile = None
        self.certfile = None
        super().__init__(config=config)


class ModulesConfiguration:
    """
    """
    _module_name_regex = re.compile(r'^\w+(\s\w+)*$')

    def __init__(self, module_base: str, config: Optional[Mapping[str, Mapping]] = None) -> None:
        if module_base not in ['gui', 'logic', 'hardware']:
            raise ValueError('"module_base" must be one of ["gui", "logic", "hardware"]')
        self._module_base = module_base
        self._modules = dict()
        if config is not None:
            for key, module_dict in config.items():
                if 'remote_url' in module_dict:
                    self[key] = RemoteModuleConfiguration(module_dict)
                else:
                    self[key] = LocalModuleConfiguration(module_dict)

    def add_local_module(self,
                         name: str,
                         module_class: str,
                         allow_remote: Optional[bool] = None,
                         connect: Optional[Mapping[str, str]] = None,
                         options: Optional[Mapping[str, Any]] = None) -> None:
        self.validate_name(name)

    @classmethod
    def validate_name(cls, name: str) -> None:
        if cls._module_name_regex.match(name) is None:
            raise ValueError('qudi module config name must be non-empty str containing only '
                             'unicode word characters and spaces.')

    @classmethod
    def validate_module_class(cls, module_class: str) -> None:
        if cls._module_name_regex.match(name) is None:
            raise ValueError('qudi module config name must be non-empty str containing only '
                             'unicode word characters and spaces.')
