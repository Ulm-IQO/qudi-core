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

__all__ = ['AbstractConfigurationItem', 'ConfigurationItem', 'ScalarConfigurationItem',
           'SequenceConfigurationItem', 'MappingConfigurationItem', 'StrConfigurationItem',
           'BoolConfigurationItem', 'NumberConfigurationItem', 'RealConfigurationItem',
           'IntConfigurationItem', 'ListConfigurationItem', 'SetConfigurationItem',
           'StrListConfigurationItem']

import copy
from typing import Any
from abc import ABC, abstractmethod


class AbstractConfigurationItem(ABC):
    """
    """
    public_name = '<unbound>'

    def __set_name__(self, owner, name):
        if name.startswith('_'):
            raise ValueError(
                f'{self.__class__.__name__} "{name}" must not be a private/protected member.'
            )
        self.public_name = name
        self.private_name = f'_{name}'

    def __get__(self, instance, owner):
        return copy.deepcopy(getattr(instance, self.private_name))

    def __set__(self, instance, value):
        self.validate(value)
        setattr(instance, self.private_name, value)

    @abstractmethod
    def validate(self, value: Any) -> None:
        """ Checks value to set as ConfigurationItem. Raises TypeError if invalid.
        You must overwrite this method in specialized subclasses of AbstractConfigurationItem.
        """
        raise NotImplementedError


class ConfigurationItem(AbstractConfigurationItem):
    """
    """
    _leaf_types = (int, float, complex, str, bool, type(None))
    _sequence_types = (list, tuple, set, frozenset)
    _mapping_types = (dict,)

    def validate(self, value: Any) -> None:
        """ See: qudi.core.config.AbstractConfigurationItem

        Recursive validator that goes through all items of value and checks against types defined
        in class attributes _leaf_types, _sequence_types and _mapping_types.
        """
        if isinstance(value, self._leaf_types):
            return
        if isinstance(value, self._sequence_types):
            for val in value:
                ConfigurationItem.validate(self, val)
            return
        if isinstance(value, self._mapping_types):
            for key, val in value.items():
                if not isinstance(key, self._leaf_types):
                    allowed_types = '(' + ', '.join(typ.__name__ for typ in self._leaf_types) + ')'
                    raise TypeError(
                        f'{self.__class__.__name__} mapping "{self.public_name}" keys must be one '
                        f'of types {allowed_types}'
                    )
                ConfigurationItem.validate(self, val)
            return
        raise TypeError(f'{self.__class__.__name__} "{self.public_name}" encountered invalid type '
                        f'{type(value).__name__}.')


class ScalarConfigurationItem(ConfigurationItem):
    """
    """
    _sequence_types = tuple()
    _mapping_types = tuple()

    def __init__(self, validator=None) -> None:
        self._validator = validator

    def validate(self, value: Any) -> None:
        """ See: qudi.core.config.AbstractConfigurationItem
        """
        super().validate(value)
        if self._validator is not None:
            self._validator(value)


class SequenceConfigurationItem(ConfigurationItem):
    """
    """
    def __init__(self, item_validator=None) -> None:
        self._item_validator = super().validate if item_validator is None else item_validator

    def validate(self, value: Any) -> None:
        """ See: qudi.core.config.AbstractConfigurationItem
        """
        if value is None:
            return
        if not isinstance(value, self._sequence_types):
            allowed_types = '(' + ', '.join(typ.__name__ for typ in self._sequence_types) + ')'
            raise TypeError(f'{self.__class__.__name__} "{self.public_name}" must be one of types '
                            f'{allowed_types}')
        for it in value:
            self._item_validator(it)


class MappingConfigurationItem(ConfigurationItem):
    """
    """
    def __init__(self, item_validator=None) -> None:
        self._item_validator = item_validator

    def validate(self, value: Any) -> None:
        """ See: qudi.core.config.AbstractConfigurationItem
        """
        if value is None:
            return
        if not isinstance(value, self._mapping_types):
            allowed_types = '(' + ', '.join(typ.__name__ for typ in self._mapping_types) + ')'
            raise TypeError(f'{self.__class__.__name__} "{self.public_name}" must be one of types '
                            f'{allowed_types}')
        if self._item_validator is None:
            super().validate(value)
        else:
            for it in value.items():
                self._item_validator(it)


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
