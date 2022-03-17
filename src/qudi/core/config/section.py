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

__all__ = ['ConfigurationSection', 'GlobalConfiguration', 'LocalModuleConfiguration',
           'RemoteModuleConfiguration']

import copy
import re
from typing import List, Any, Mapping, Optional, Union

from .items import *


class ConfigurationSectionMeta(type):
    """ Metaclass for ConfigurationSection types.
    Joins all parent and current class "_config_items" member dicts.
    """
    def __new__(mcs, name, bases, attributes):
        config_items = dict()
        for base in reversed(bases):
            config_items.update(base.__dict__.get('_config_items', dict()))
        config_items.update(attributes.get('_config_items', dict()))
        attributes['_config_items'] = config_items
        return super().__new__(mcs, name, bases, attributes)


class ConfigurationSection(metaclass=ConfigurationSectionMeta):
    """
    """
    _config_items_editable = False  # ADDITIONAL items can be added and deleted again dynamically
    _config_items = dict()  # All _config_items from parent classes will be automatically included

    def __init__(self, configuration: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__()
        self._config = {name: cfg_item.default for name, cfg_item in self._config_items.items()}
        # Create a shallow copy of the _config_items class dict in this instance if it should be
        # editable
        if self._config_items_editable:
            self._config_items = self._config_items.copy()
        if configuration is not None:
            self.update(configuration)

    def __getitem__(self, key):
        return self._config[key]

    def __setitem__(self, key, value):
        try:
            validate = self._config_items[key].validate
        except KeyError:
            if self._config_items_editable:
                new_item = ConfigurationItem()
                self._config_items[key] = new_item
                self._config[key] = new_item.default
                validate = new_item.validate
            else:
                raise
        validate(value)
        self._config[key] = value

    def __delitem__(self, key):
        if self._config_items_editable and key not in self.__class__._config_items:
            del self._config_items[key]
            self._config.pop(key, None)
            return
        raise TypeError(f'Can not delete "{self.__class__.__name__}" config items')

    def __len__(self):
        return len(self._config)

    def __iter__(self):
        return self._config.__iter__()

    def keys(self):
        return self._config.keys()

    def values(self):
        return self._config.values()

    def items(self):
        return self._config.items()

    def get(self, key, default=None):
        return self._config.get(key, default)

    def update(self, mapping=None, /, **kwargs) -> None:
        if mapping is None:
            if kwargs:
                mapping = kwargs
            else:
                return
        elif kwargs:
            mapping = mapping.copy()
            mapping.update(kwargs)
        for key, value in mapping.items():
            self[key] = value

    def pop(self, key, /, *args):
        if self._config_items_editable and key not in self.__class__._config_items:
            self._config_items.pop(key, *args)
            return self._config.pop(key, *args)
        raise TypeError(f'Can not delete "{self.__class__.__name__}" config items')

    def copy(self):
        return ConfigurationSection(copy.deepcopy(self._config))


class GlobalConfiguration(ConfigurationSection):
    """ The global configuration section of qudi
    """
    _config_items_editable = True
    _config_items = {
        'startup_modules'            : StrListConfigurationItem(default=list()),
        'remote_modules_server'      : MappingConfigurationItem(default={'address': 'localhost',
                                                                         'port'   : 12345}),
        'namespace_server_port'      : IntConfigurationItem(default=18861),
        'force_remote_calls_by_value': BoolConfigurationItem(default=False),
        'hide_manager_window'        : BoolConfigurationItem(default=False),
        'stylesheet'                 : StrConfigurationItem(default='qdark.qss'),
        'daily_data_dirs'            : BoolConfigurationItem(default=True),
        'default_data_dir'           : StrConfigurationItem(),
        'extension_paths'            : StrListConfigurationItem()
    }


class LocalModuleConfiguration(ConfigurationSection):
    """ Configuration section of a local qudi module
    """

    @staticmethod
    def validate_module_class(module_class: str) -> None:
        if re.match(r'^\w+(\.\w+)*$', module_class) is None:
            raise ValueError('qudi module config "module.Class" must be non-empty str containing a '
                             'valid Python "module.Class"-like path, e.g. '
                             '"my_module.my_submodule.MyClass"')

    _config_items = {
        'module.Class': StrConfigurationItem(validator=validate_module_class),
        'allow_remote': BoolConfigurationItem(default=False),
        'connect'     : MappingConfigurationItem(),
        'options'     : MappingConfigurationItem()
    }


class RemoteModuleConfiguration(ConfigurationSection):
    """ Configuration section of a remote qudi module
    """

    _config_items = {
        'remote_url': StrConfigurationItem(),
        'keyfile'   : StrConfigurationItem(),
        'certfile'  : StrConfigurationItem(),
    }


class ModulesConfiguration:
    """
    """

    def __init__(self, configuration: Optional[Mapping[str, Mapping[str, Any]]] = None) -> None:
        self._local_modules = dict()
        self._remote_modules = dict()
        if configuration is not None:
            for name, module_cfg in configuration.items():
                if 'remote_url' in module_cfg:
                    self.add_remote_module(name, module_cfg)
                else:
                    self.add_local_module(name, module_cfg)

    def add_local_module(self,
                         name: str,
                         module_config: Optional[Mapping[str, Any]] = None) -> None:
        self.validate_new_module_name(name)
        self._local_modules[name] = LocalModuleConfiguration(configuration=module_config)

    def add_remote_module(self,
                          name: str,
                          module_config: Optional[Mapping[str, Any]] = None) -> None:
        self.validate_new_module_name(name)
        self._remote_modules[name] = RemoteModuleConfiguration(configuration=module_config)

    def remove_module(self, name: str) -> None:
        del self[name]

    def validate_new_module_name(self, name: str) -> None:
        if re.match(r'^\w+(\s\w+)*$', name) is None:
            raise ValueError('qudi module config name must be non-empty str containing only '
                             'unicode word characters and spaces.')
        if name in self._local_modules:
            raise ValueError(f'Local qudi module with name "{name}" already configured in this '
                             f'{self.__class__.__name__} group')
        if name in self._remote_modules:
            raise ValueError(f'Remote qudi module with name "{name}" already configured in this '
                             f'{self.__class__.__name__} group')

    def __getitem__(self, key: str) -> Union[LocalModuleConfiguration, RemoteModuleConfiguration]:
        try:
            return self._local_modules[key]
        except KeyError:
            try:
                return self._remote_modules[key]
            except KeyError:
                pass
        raise KeyError(
            f'No qudi module with name "{key}" configured in this {self.__class__.__name__} group'
        )

    def __setitem__(self, key, value) -> None:
        try:
            module_config = self[key]
        except KeyError:
            pass
        else:
            module_config.update(value)
            return
        raise KeyError(f'No qudi module with name "{key}" configured in this '
                       f'{self.__class__.__name__} group.\n'
                       f'Use add_local_module/add_remote_module to add new modules to this group.')

    def __delitem__(self, key) -> None:
        try:
            del self._local_modules[key]
            return
        except KeyError:
            try:
                del self._remote_modules[key]
                return
            except KeyError:
                pass
        raise KeyError(f'No qudi module with name "{key}" configured in this '
                       f'{self.__class__.__name__} group')

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key, /, *args):
        if self._config_items_editable and key not in self.__class__._config_items:
            self._config_items.pop(key, *args)
            return self._config.pop(key, *args)
        raise TypeError(f'Can not delete "{self.__class__.__name__}" config items')
