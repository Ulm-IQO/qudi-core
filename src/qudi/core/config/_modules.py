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

__all__ = ['ModuleConfigMixin']

import copy
from numbers import Number
from typing import Mapping, Optional, Union, Sequence, Set, List
from .proxy import MappingProxy


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
        self.validate_module_base(base)
        module_config = {'module.Class': module_class}
        if allow_remote is not None:
            module_config['allow_remote'] = allow_remote
        if connect is not None:
            module_config['connect'] = copy.copy(connect)
        if options is not None:
            module_config['options'] = copy.deepcopy(options)
        self.config[base][name] = module_config

    def add_remote_module(self,
                          base: str,
                          name: str,
                          remote_url: str,
                          certfile: Optional[str] = None,
                          keyfile: Optional[str] = None) -> None:
        self.validate_module_base(base)
        module_config = {'remote_url': remote_url}
        if certfile is not None:
            module_config['certfile'] = certfile
        if keyfile is not None:
            module_config['keyfile'] = keyfile
        self.config[base][name] = module_config

    def rename_module(self, old_name: str, new_name: str) -> None:
        if old_name == new_name:
            return
        if not self.module_configured(old_name):
            raise KeyError(f'No module with name "{old_name}" configured')
        if self.module_configured(new_name):
            raise KeyError(f'Module with name "{new_name}" already configured')

        for base in ['gui', 'logic', 'hardware']:
            try:
                module_config = self._config[base].pop(old_name)
            except KeyError:
                continue
            self.config[base][new_name] = module_config
            return

    def remove_module(self, name: str) -> None:
        config_proxy = self.config
        for base in ['gui', 'logic', 'hardware']:
            try:
                del config_proxy[base][name]
            except KeyError:
                continue
            return
        raise KeyError(f'No module with name "{name}" configured')

    def module_configured(self, name: str) -> bool:
        """ Checks if a module with given name is present in current configuration """
        return name in self._config['gui'] or name in self._config['logic'] or name in self._config[
            'hardware']

    def get_module_config(self, name: str) -> MappingProxy:
        config_proxy = self.config
        for base in ['gui', 'logic', 'hardware']:
            try:
                return config_proxy[base][name]
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
