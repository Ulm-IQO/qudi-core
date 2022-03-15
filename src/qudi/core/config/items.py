# -*- coding: utf-8 -*-

"""
This file contains descriptor objects used for validating qudi configuration items.

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

__all__ = ['ConfigurationItem', 'ScalarConfigurationItem', 'SequenceConfigurationItem',
           'MappingConfigurationItem', 'StrConfigurationItem', 'BoolConfigurationItem',
           'NumberConfigurationItem', 'RealConfigurationItem', 'IntConfigurationItem',
           'ListConfigurationItem', 'SetConfigurationItem', 'StrListConfigurationItem']

import copy
from typing import Any
from qudi.util.helpers import is_string


class ConfigurationItem:
    """
    """
    _leaf_types = (int, float, complex, str, bool, type(None))
    _sequence_types = (list, tuple, set, frozenset)
    _mapping_types = (dict,)

    def __init__(self, name, default=None, validator=None):
        if not is_string(name):
            raise TypeError('Name of configuration item must be a string')
        self.validate = self.default_validator if validator is None else validator
        self.validate(default)
        self._name = str(name)
        self._default = default

    @property
    def name(self) -> str:
        return self._name

    @property
    def default(self) -> Any:
        return copy.deepcopy(self._default)

    @classmethod
    def default_validator(cls, value: Any) -> None:
        """ Checks value to set as ConfigurationItem. Raises TypeError if invalid.

        Default validator that goes recursively through all items of value and checks against
        types defined in class attributes _leaf_types, _sequence_types and _mapping_types.
        """
        if isinstance(value, cls._leaf_types):
            return
        if isinstance(value, cls._sequence_types):
            for val in value:
                ConfigurationItem.default_validator(val)
            return
        if isinstance(value, cls._mapping_types):
            for key, val in value.items():
                if not isinstance(key, cls._leaf_types):
                    allowed_types = ', '.join(typ.__name__ for typ in cls._leaf_types)
                    raise TypeError(
                        f'{cls.__name__} mapping keys must be one of the following types: '
                        f'[{allowed_types}]'
                    )
                ConfigurationItem.default_validator(val)
            return
        raise TypeError(f'{cls.__name__} encountered invalid type: {type(value).__name__}')


class ScalarConfigurationItem(ConfigurationItem):
    """
    """
    _sequence_types = ()
    _mapping_types = ()


class SequenceConfigurationItem(ConfigurationItem):
    """
    """

    @classmethod
    def default_validator(cls, value: Any) -> None:
        """ See: qudi.core.config.ConfigurationItem
        """
        if value is None:
            return
        if not isinstance(value, cls._sequence_types):
            allowed_types = ', '.join(typ.__name__ for typ in cls._sequence_types)
            raise TypeError(f'{cls.__name__} value must be one of the following types: '
                            f'[{allowed_types}]')
        for it in value:
            super().default_validator(it)


class MappingConfigurationItem(ConfigurationItem):
    """
    """

    @classmethod
    def default_validator(cls, value: Any) -> None:
        """ See: qudi.core.config.ConfigurationItem
        """
        if value is None:
            return
        if not isinstance(value, cls._mapping_types):
            allowed_types = ', '.join(typ.__name__ for typ in cls._mapping_types)
            raise TypeError(f'{cls.__name__} value must be one of the following types: '
                            f'[{allowed_types}]')
        super().default_validator(value)


class StrConfigurationItem(ScalarConfigurationItem):
    _leaf_types = (str, type(None))


class BoolConfigurationItem(ScalarConfigurationItem):
    _leaf_types = (bool, type(None))


class NumberConfigurationItem(ScalarConfigurationItem):
    _leaf_types = (int, float, complex, type(None))


class RealConfigurationItem(ScalarConfigurationItem):
    _leaf_types = (int, float, type(None))


class IntConfigurationItem(ScalarConfigurationItem):
    _leaf_types = (int, type(None))


class ListConfigurationItem(SequenceConfigurationItem):
    _sequence_types = (list, tuple)


class SetConfigurationItem(SequenceConfigurationItem):
    _sequence_types = (set, frozenset)


class StrListConfigurationItem(ListConfigurationItem):
    _leaf_types = (str, type(None))
