# -*- coding: utf-8 -*-

"""
JSON (draft v7) validator for qudi YAML configurations that also fills in default values.
The corresponding JSON schema is defined in ".__schema.py".

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

__all__ = ['ValidationError', 'validate_config', 'validate_local_module_config',
           'validate_remote_module_config', 'validate_module_name']

import re
from typing import Mapping, Any
from jsonschema import ValidationError
from jsonschema import validators as __validators
from jsonschema import Draft7Validator as __BaseValidator

from .schema import config_schema, remote_module_config_schema, local_module_config_schema


def __set_defaults(validator, properties, instance, schema):
    # Only insert default values of current schema into instance if validation passses
    try:
        __BaseValidator(schema).validate(instance)
    except ValidationError:
        pass
    else:
        for property, subschema in properties.items():
            if 'default' in subschema:
                try:
                    instance.setdefault(property, subschema['default'])
                except AttributeError:
                    pass

    for error in __BaseValidator.VALIDATORS['properties'](validator, properties, instance, schema):
        yield error


def __is_iterable(checker, instance):
    return (__BaseValidator.TYPE_CHECKER.is_type(instance, "array") or
            isinstance(instance, (set, frozenset, tuple)))


# Add custom JSON schema (draft v7) validator that accepts all Python builtin sequences as "array"
# type
DefaultInsertionValidator = __validators.extend(
    validator=__BaseValidator,
    validators={'properties': __set_defaults},
    type_checker=__BaseValidator.TYPE_CHECKER.redefine("array", __is_iterable)
)


def validate_config(config: Mapping[str, Any]) -> None:
    """ JSON schema (draft v7) validator for qudi configuration.
    Raises jsonschema.ValidationError if invalid.
    """
    DefaultInsertionValidator(config_schema()).validate(config)


def validate_local_module_config(config: Mapping[str, Any]) -> None:
    """ JSON schema (draft v7) validator for single qudi local module configuration.
    Raises jsonschema.ValidationError if invalid.
    """
    DefaultInsertionValidator(local_module_config_schema()).validate(config)


def validate_remote_module_config(config: Mapping[str, Any]) -> None:
    """ JSON schema (draft v7) validator for single qudi remote module configuration.
    Raises jsonschema.ValidationError if invalid.
    """
    DefaultInsertionValidator(remote_module_config_schema()).validate(config)


def validate_module_name(name: str) -> None:
    """ Regular expression validator for qudi module names.
    Raises jsonschema.ValidationError if invalid.

    WARNING: The jsonschema.ValidationError raised does not contain any JSON schema information.
    """
    if re.match(r'^[a-zA-Z_]+[a-zA-Z0-9_]*$', name) is None:
        raise ValidationError(
            'Module names must only contain word characters [a-zA-Z0-9_] and not start on a number.'
        )
