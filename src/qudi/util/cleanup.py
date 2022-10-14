# -*- coding: utf-8 -*-

"""
Utility functions to clean up qudi appdata.

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

__all__ = ['clear_appdata', 'clear_modules_appdata', 'clear_resources_appdata', 'clear_load_config',
           'clear_default_config', 'clear_user_data', 'clear_config_files', 'clear_log_files']

import os
import re
from shutil import rmtree
from qudi.util.paths import get_resources_dir, get_appdata_dir, get_userdata_dir
from qudi.util.paths import get_default_config_dir, get_default_log_dir


def clear_modules_appdata():
    appdata_dir = get_appdata_dir()
    if os.path.exists(appdata_dir):
        # delete qudi modules appdata, i.e. StatusVars
        status_regex = re.compile(
            r'status-(.+?)_(hardware|gui|logic)_(.+?)[.]{1}(cfg|npy|npz)'
        )
        for root, dirs, files in os.walk(appdata_dir):
            for file in files:
                if status_regex.match(file):
                    try:
                        os.remove(os.path.join(root, file))
                    except OSError:
                        pass
            break


def clear_resources_appdata():
    resources_dir = get_resources_dir()
    if os.path.exists(resources_dir):
        # Remove resources files
        resources_regex = re.compile(r'\A(.+)_rc.py\Z')
        for root, dirs, files in os.walk(resources_dir):
            for file in files:
                if resources_regex.match(file):
                    try:
                        os.remove(os.path.join(root, file))
                    except OSError:
                        pass
            break
        # Remove .checksum
        try:
            os.remove(os.path.join(resources_dir, '.checksum'))
        except OSError:
            pass
        # Remove __pycache__
        try:
            rmtree(os.path.join(resources_dir, '__pycache__'))
        except OSError:
            pass
        # Remove resources directory if empty
        try:
            os.rmdir(resources_dir)
        except OSError:
            pass


def clear_load_config():
    load_config_path = os.path.join(get_appdata_dir(), 'load.cfg')
    try:
        os.remove(load_config_path)
    except OSError:
        pass


def clear_default_config():
    default_config_path = os.path.join(get_appdata_dir(), 'default.cfg')
    try:
        os.remove(default_config_path)
    except OSError:
        pass


def clear_log_files():
    log_dir = get_default_log_dir()
    if os.path.isdir(log_dir):
        log_regex = re.compile(r'\Aqudi\.log(\.\d)?\Z')
        for path in [os.path.join(log_dir, f) for f in os.listdir(log_dir) if log_regex.match(f)]:
            try:
                os.remove(path)
            except OSError:
                pass
        try:
            os.rmdir(log_dir)
        except OSError:
            pass


def clear_config_files():
    config_dir = get_default_config_dir()
    if os.path.isdir(config_dir):
        for file in [f for f in os.listdir(config_dir) if f.endswith('.cfg')]:
            try:
                os.remove(os.path.join(config_dir, file))
            except OSError:
                pass
        try:
            os.rmdir(config_dir)
        except OSError:
            pass


def clear_user_data():
    clear_log_files()
    clear_config_files()
    # Delete qudi userdata directory in home if it is empty
    try:
        os.rmdir(get_userdata_dir())
    except OSError:
        pass


def clear_appdata():
    clear_resources_appdata()
    clear_modules_appdata()
    clear_load_config()
    clear_default_config()
    # remove appdata directory if empty
    try:
        os.rmdir(get_appdata_dir())
    except OSError:
        pass
