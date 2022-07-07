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

__all__ = ['FileHandler', 'FileHandlerBase', 'ParserError', 'ValidationError', 'YAMLError',
           'DuplicateKeyError']


import os
from typing import Any, Dict, Mapping

from qudi.util.paths import get_default_config_dir, get_appdata_dir
from qudi.util.yaml import yaml_dump, yaml_load, ParserError, YAMLError, DuplicateKeyError

from .validator import validate_config, ValidationError


class FileHandlerBase:
    """ File handler base class providing static methods for handling raw qudi configuration files.
    """

    @classmethod
    def _load(cls, path: str) -> Dict[str, Any]:
        return yaml_load(cls._relative_to_absolute_path(path))

    @classmethod
    def _dump(cls, path: str, config: Mapping[str, Any]) -> None:
        if not path.endswith('.cfg'):
            raise ValueError('Configuration file must have ".cfg" file extension.')
        path = cls._relative_to_absolute_path(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return yaml_dump(path, config)

    @classmethod
    def set_default_path(cls, path: str) -> None:
        """ Writes the given config file path to "<AppData>/qudi/load.cfg" to be used as default
        config at the next start of qudi. """
        # Write current config file path to load.cfg
        yaml_dump(
            os.path.join(get_appdata_dir(create_missing=True), 'load.cfg'),
            {'load_config_path': cls._relative_to_absolute_path(path)}
        )

    @staticmethod
    def get_saved_path() -> str:
        """ Tries to parse "<AppData>/qudi/load.cfg" and return the stored config file path.
        Raises FileNotFoundError if unsuccessful or if the recovered file path does not exist.
        """
        # Try loading config file path from last session
        load_cfg = yaml_load(os.path.join(get_appdata_dir(), 'load.cfg'), ignore_missing=True)
        file_path = load_cfg.get('load_config_path', '')
        if os.path.exists(file_path) and file_path.endswith('.cfg'):
            return file_path

        # Raise error if no last run config file could be found
        raise FileNotFoundError('No config file path saved from previous qudi sessions')

    @staticmethod
    def get_default_path() -> str:
        """ Tries to find config file named "default.cfg" in several locations with the following,
        non-recursive search directory priority:
            1. <UserHome>/qudi/config/
            2. <AppData>/qudi/

        Raises FileNotFoundError if no "default.cfg" file could be found in the above locations.
        """
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
    def _relative_to_absolute_path(path):
        """ Helper method converting given relative path to an existing absolute path.
        Prepends directories to given path with the following priority until an existing path has
        been created:
            1. <UserHome>/qudi/config/
            2. <AppData>/qudi/

        Raises FileNotFoundError if no existing path could be reconstructed by the above algorithm.
        """
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


class FileHandler(FileHandlerBase):
    """ File handler class providing static methods for handling raw qudi configuration files.
    Also applies qudi configuration validation and default value insertion upon loading/dumping
    configuration files.
    """

    @classmethod
    def load(cls, path: str) -> Dict[str, Any]:
        """ Load and validate a qudi configuration file from disk.
        Raises jsonschema.ValidationError if validation fails.
        """
        config = cls._load(path)
        validate_config(config)
        return config

    @classmethod
    def dump(cls, path: str, config: Dict[str, Any]) -> None:
        """ Validate and dump a qudi configuration file to disk.
        Raises jsonschema.ValidationError if validation fails.
        """
        validate_config(config)
        cls._dump(path, config)
