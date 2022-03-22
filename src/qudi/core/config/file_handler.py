# -*- coding: utf-8 -*-

"""
Static file handler and mixin for handling qudi configuration files.

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

__all__ = ['FileHandler', 'FileHandlerMixin']

import os
from typing import Any, Dict

from qudi.util.paths import get_default_config_dir, get_appdata_dir
from qudi.util.yaml import yaml_dump, yaml_load
from .validator import validate_config


class FileHandlerMixin:
    """ File handler mixin class providing static methods for handling raw qudi configuration files.
    Also applies qudi configuration validation and default value insertion upon loading/dumping
    configuration files.
    """

    @classmethod
    def _load_config_file(cls, path: str) -> Dict[str, Any]:
        config = yaml_load(cls.relative_to_absolute_path(path))
        validate_config(config)
        return config

    @classmethod
    def _dump_config_file(cls, path: str, config: Dict[str, Any]) -> None:
        if not path.endswith('.cfg'):
            raise ValueError('Configuration file must have ".cfg" file extension.')
        validate_config(config)
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


class FileHandler(FileHandlerMixin):
    """ Static standalone qudi configuration file handler. """

    @classmethod
    def load_config_file(cls, path: str) -> Dict[str, Any]:
        return cls._load_config_file(path)

    @classmethod
    def dump_config_file(cls, path: str, config: Dict[str, Any]) -> None:
        return cls._dump_config_file(path, config)
