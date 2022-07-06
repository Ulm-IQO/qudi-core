# -*- coding: utf-8 -*-

"""
JSON schema to be used by jsonschema.validate on YAML qudi configuration files.

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

__all__ = ['config_schema', 'local_module_config_schema', 'remote_module_config_schema']

from typing import Dict, Any


__module_name_pattern = r'[a-zA-Z_]+[a-zA-Z0-9_]*'


def config_schema() -> Dict[str, Any]:
    """ Creates and returns the JSON schema for a qudi configuration """
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'global': {
                'type': 'object',
                'additionalProperties': True,
                'default': dict(),
                'properties': {
                    'startup_modules': {
                        'type': 'array',
                        'uniqueItems': True,
                        'items': {
                            'type': 'string',
                            'pattern': f'^{__module_name_pattern}$'
                        },
                        'default': list()
                    },
                    'remote_modules_server': {
                        'type': ['null', 'object'],
                        'required': ['address', 'port'],
                        'default': None,
                        'additionalProperties': False,
                        'properties': {
                            'address': {
                                'type': 'string',
                            },
                            'port': {
                                'type': 'integer',
                                'minimum': 0,
                                'maximum': 65535
                            },
                            'certfile': {
                                'type': ['null', 'string'],
                                'default': None
                            },
                            'keyfile': {
                                'type': ['null', 'string'],
                                'default': None
                            }
                        }
                    },
                    'namespace_server_port': {
                        'type': 'integer',
                        'minimum': 0,
                        'maximum': 65535,
                        'default': 18861
                    },
                    'force_remote_calls_by_value': {
                        'type': 'boolean',
                        'default': True
                    },
                    'hide_manager_window': {
                        'type': 'boolean',
                        'default': False
                    },
                    'stylesheet': {
                        'type': 'string',
                        'pattern': r'^[^.]+\.qss$',
                        'default': 'qdark.qss'
                    },
                    'daily_data_dirs': {
                        'type': 'boolean',
                        'default': True
                    },
                    'default_data_dir': {
                        'type': ['null', 'string'],
                        'default': None
                    },
                    'extension_paths': {
                        'type': 'array',
                        'uniqueItems': True,
                        'items': {
                            'type': 'string'
                        },
                        'default': list()
                    }
                }
            },
            'gui': {
                'type': 'object',
                'propertyNames': {
                    'pattern': f'^{__module_name_pattern}$'
                },
                'additionalProperties': {
                    '$ref': '#/$defs/local_module'
                },
                'default': dict()
            },
            'logic': {
                'type': 'object',
                'propertyNames': {
                    'pattern': f'^{__module_name_pattern}$'
                },
                'additionalProperties': {
                    'oneOf': [
                        {'$ref': '#/$defs/local_module'},
                        {'$ref': '#/$defs/remote_module'}
                    ]
                },
                'default': dict()
            },
            'hardware': {
                'type': 'object',
                'propertyNames': {
                    'pattern': f'^{__module_name_pattern}$'
                },
                'additionalProperties': {
                    'oneOf': [
                        {'$ref': '#/$defs/local_module'},
                        {'$ref': '#/$defs/remote_module'}
                    ]
                },
                'default': dict()
            }
        },

        '$defs': {
            'local_module': local_module_config_schema(),
            'remote_module': remote_module_config_schema()
        }
    }


def local_module_config_schema() -> Dict[str, Any]:
    """ Creates and returns the JSON schema for a single qudi local module configuration """
    return {
        'type': 'object',
        'required': ['module.Class'],
        'additionalProperties': False,
        'properties': {
            'module.Class': {
                'type': 'string',
                'pattern': f'^{__module_name_pattern}(\\.{__module_name_pattern})*$',
            },
            'allow_remote': {
                'type': 'boolean',
                'default': False
            },
            'connect': {
                'type': 'object',
                'additionalProperties': {
                    'type': 'string',
                    'pattern': f'^{__module_name_pattern}$'
                },
                'default': dict()
            },
            'options': {
                'type': 'object',
                'additionalProperties': True,
                'default': dict()
            }
        }
    }


def remote_module_config_schema() -> Dict[str, Any]:
    """ Creates and returns the JSON schema for a single qudi remote module configuration """
    return {
        'type': 'object',
        'required': ['native_module_name', 'address', 'port'],
        'additionalProperties': False,
        'properties': {
            'native_module_name': {
                'type': 'string',
                'pattern': f'^{__module_name_pattern}$'
            },
            'address': {
                'type': 'string',
            },
            'port': {
                'type': 'integer',
                'minimum': 0,
                'maximum': 65535
            },
            'certfile': {
                'type': ['null', 'string'],
                'default': None
            },
            'keyfile': {
                'type': ['null', 'string'],
                'default': None
            }
        }
    }
