# -*- coding: utf-8 -*-
"""
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

ToDo: Throw errors around for non-existent directories
"""

__all__ = ['get_user_appdata_dir', 'get_global_appdata_dir', 'get_default_config_dir',
           'get_default_log_dir', 'get_default_data_dir', 'get_daily_directory', 'get_home_dir',
           'get_qudi_core_dir', 'get_userdata_dir', 'get_resources_dir', 'get_module_app_data_path',
           'get_qudi_package_dirs']

import datetime
import os
import sys
from typing import Optional, List


def get_qudi_core_dir() -> str:
    """ Returns the absolute path to the source directory of the qudi-core package.

    @return str: path to qudi-core root dir
    """
    import qudi.core as core
    return os.path.abspath(os.path.join(os.path.dirname(core.__file__), '..'))


def get_resources_dir(create_missing: Optional[bool] = False) -> str:
    """ Returns the absolute path to the qudi resources directory. Usually a subdirectory of the
    appdata directory (see: get_global_appdata_dir)

    @return string: path to the resources directory of qudi
    """
    path = os.path.join(get_global_appdata_dir(create_missing=create_missing), 'resources')
    if create_missing and not os.path.exists(path):
        os.mkdir(path)
    return path


def get_home_dir() -> str:
    """ Returns the path to the home directory, which should definitely exist.

    @return str: absolute path to the home directory
    """
    return os.path.abspath(os.path.expanduser('~'))


def get_userdata_dir(create_missing: Optional[bool] = False) -> str:
    """ Returns the path to the qudi subfolder in the user home directory. This path should be used
     for exposed user data like config files etc.

    @return str: absolute path to the home directory
    """
    path = os.path.join(get_home_dir(), 'qudi')
    # Create directory if desired. Will throw an exception if path returned by get_home_dir() is
    # non-existent (which should never happen).
    if create_missing and not os.path.exists(path):
        os.mkdir(path)
    return path


def get_user_appdata_dir(create_missing: Optional[bool] = False) -> str:
    """ Get the user specific application data directory """
    if sys.platform == 'win32':
        # resolves to "C:\Users\<UserName>\AppData\Local" on win7 and newer
        path = os.path.join(os.environ['LOCALAPPDATA'], 'qudi')
    elif sys.platform == 'darwin':
        path = os.path.abspath(os.path.expanduser('~/Library/Preferences/qudi'))
    else:
        path = os.path.abspath(os.path.expanduser('~/.local/qudi'))

    # Create path if desired.
    if create_missing and not os.path.exists(path):
        os.makedirs(path)
    return path


def get_global_appdata_dir(create_missing: Optional[bool] = False) -> str:
    """ Get the user specific application data directory """
    if sys.platform == 'win32':
        # resolves to "C:\Users\<UserName>\AppData\Roaming" on win7 and newer
        path = os.path.join(os.environ['APPDATA'], 'qudi')
    elif sys.platform == 'darwin':
        path = os.path.abspath(os.path.expanduser('~/Library/Preferences/qudi'))
    else:
        path = os.path.abspath(os.path.expanduser('~/.local/qudi'))

    # Create path if desired.
    if create_missing and not os.path.exists(path):
        os.makedirs(path)
    return path


def get_default_config_dir(create_missing: Optional[bool] = False) -> str:
    """ Get the system specific application data directory.

    @return str: path to appdata directory
    """
    path = os.path.join(get_userdata_dir(create_missing), 'config')
    # Create path if desired.
    if create_missing and not os.path.exists(path):
        os.mkdir(path)
    return path


def get_default_log_dir(create_missing: Optional[bool] = False) -> str:
    """ Get the system specific application log directory.

    @return str: path to default logging directory
    """
    # FIXME: This needs to be properly done for linux systems
    path = os.path.join(get_userdata_dir(create_missing), 'log')
    # Create path if desired.
    if create_missing and not os.path.exists(path):
        os.mkdir(path)
    return path


def get_default_data_dir(create_missing: Optional[bool] = False) -> str:
    """ Get the system specific application fallback data root directory.
    Does NOT consider qudi configuration.

    @return str: path to default data root directory
    """
    # FIXME: This needs to be properly done for linux systems
    path = os.path.join(get_userdata_dir(create_missing), 'Data')
    # Create path if desired.
    if create_missing and not os.path.exists(path):
        os.mkdir(path)
    return path


def get_daily_directory(timestamp: Optional[datetime.datetime] = None,
                        root: Optional[str] = None,
                        create_missing: Optional[bool] = False
                        ) -> str:
    """ Returns a path tree according to the timestamp given.

    The directory structure will have the form: root/<YYYY>/<MM>/<YYYY-MM-DD>
    If not root directory is given, this method will return just the relative path stub:
    <YYYY>/<MM>/<YYYY-MM-DD>

    @param datetime.datetime timestamp: optional, Timestamp for which to create daily directory
                                        (default: now)
    @param str root: optional, root path for daily directory structure
    @param bool create_missing: optional, indicate if the directory should be created (True) or not
                                (False). Is only considered if root is given as well.
    """
    if timestamp is None:
        timestamp = datetime.datetime.now()

    day_dir = timestamp.strftime('%Y-%m-%d')
    year_dir, month_dir = day_dir.split('-')[:2]
    daily_path = os.path.join(year_dir, month_dir, day_dir)
    if root is not None:
        daily_path = os.path.join(root, daily_path)
        if create_missing:
            os.makedirs(daily_path, exist_ok=True)
    return daily_path


def get_module_app_data_path(cls_name: str, module_base: str, module_name: str) -> str:
    """ Constructs the appData file path for the given qudi module
    """
    file_name = f'status-{cls_name}_{module_base}_{module_name}.cfg'
    return os.path.join(get_user_appdata_dir(), file_name)


def get_qudi_package_dirs() -> List[str]:
    try:
        from qudi import __path__ as _qudi_ns_paths
    except ImportError:
        _qudi_ns_paths = list()
    tmp = [p.lower() for p in _qudi_ns_paths]
    directories = [p for ii, p in enumerate(_qudi_ns_paths) if p.lower() not in tmp[:ii]]
    try:
        core_dir = get_qudi_core_dir()
        directories.remove(core_dir)
        directories = [core_dir, *directories]
    except ValueError:
        pass
    return directories
