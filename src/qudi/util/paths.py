# -*- coding: utf-8 -*-
"""
.. Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
.. distribution and on <https://github.com/Ulm-IQO/qudi-core/>
..
.. This file is part of qudi.
..
.. Qudi is free software: you can redistribute it and/or modify it under the terms of
.. the GNU Lesser General Public License as published by the Free Software Foundation,
.. either version 3 of the License, or (at your option) any later version.
..
.. Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
.. without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
.. See the GNU Lesser General Public License for more details.
..
.. You should have received a copy of the GNU Lesser General Public License along with qudi.
.. If not, see <https://www.gnu.org/licenses/>.

ToDo: Throw errors around for non-existent directories
"""

__all__ = [
    "get_appdata_dir",
    "get_default_config_dir",
    "get_default_log_dir",
    "get_default_data_dir",
    "get_daily_directory",
    "get_home_dir",
    "get_main_dir",
    "get_userdata_dir",
    "get_artwork_dir",
    "get_module_app_data_path",
]

import datetime
import os
import sys
from typing import Optional


def get_main_dir() -> str:
    """
    Returns the absolute path to the directory of the main software.

    Returns
    -------
    str
        Path to the main tree of the software.
    """
    import qudi.core as core

    return os.path.abspath(os.path.join(os.path.dirname(core.__file__), ".."))


def get_artwork_dir() -> str:
    """
    Returns the absolute path to the Qudi artwork directory.

    Returns
    -------
    str
        Path to the artwork directory of Qudi.

    """
    return os.path.join(get_main_dir(), "artwork")


def get_home_dir() -> str:
    """
    Returns the absolute path to the home directory.

    Returns
    -------
    str
        Absolute path to the home directory.

    """
    return os.path.abspath(os.path.expanduser("~"))


def get_userdata_dir(create_missing: Optional[bool] = False) -> str:
    """
    Returns the absolute path to the Qudi subfolder in the user home directory.
    This path should be used for exposed user data like config files, etc.

    Returns
    -------
    str
        Absolute path to the Qudi subfolder in the user home directory.

    """
    path = os.path.join(get_home_dir(), "qudi")
    # Create directory if desired. Will throw an exception if path returned by get_home_dir() is
    # non-existent (which should never happen).
    if create_missing and not os.path.exists(path):
        os.mkdir(path)
    return path


def get_appdata_dir(create_missing: Optional[bool] = False) -> str:
    """
    Get the system-specific application data directory.

    Returns
    -------
    str
        Path to the application data directory specific to the system.

    """
    if sys.platform == "win32":
        # resolves to "C:\Documents and Settings\<UserName>\Application Data" on XP and
        # "C:\Users\<UserName>\AppData\Roaming" on win7 and newer
        path = os.path.join(os.environ["APPDATA"], "qudi")
    elif sys.platform == "darwin":
        path = os.path.abspath(os.path.expanduser("~/Library/Preferences/qudi"))
    else:
        path = os.path.abspath(os.path.expanduser("~/.local/qudi"))

    # Create path if desired.
    if create_missing and not os.path.exists(path):
        os.makedirs(path)
    return path


def get_default_config_dir(create_missing: Optional[bool] = False) -> str:
    """
    Get the system-specific application data directory.

    Returns
    -------
    str
        Path to the application data directory specific to the system.

    """
    path = os.path.join(get_userdata_dir(create_missing), "config")
    # Create path if desired.
    if create_missing and not os.path.exists(path):
        os.mkdir(path)
    return path


def get_default_log_dir(create_missing: Optional[bool] = False) -> str:
    """
    Get the system-specific application log directory.

    Returns
    -------
    str
        Path to the default logging directory specific to the system.

    """
    # FIXME: This needs to be properly done for linux systems
    path = os.path.join(get_userdata_dir(create_missing), "log")
    # Create path if desired.
    if create_missing and not os.path.exists(path):
        os.mkdir(path)
    return path


def get_default_data_dir(create_missing: Optional[bool] = False) -> str:
    """
    Get the system-specific application fallback data root directory.
    This function does NOT consider Qudi configuration.

    Returns
    -------
    str
        Path to the default data root directory specific to the system.

    """
    # FIXME: This needs to be properly done for linux systems
    path = os.path.join(get_userdata_dir(create_missing), "Data")
    # Create path if desired.
    if create_missing and not os.path.exists(path):
        os.mkdir(path)
    return path


def get_daily_directory(
    timestamp: Optional[datetime.datetime] = None,
    root: Optional[str] = None,
    create_missing: Optional[bool] = False,
) -> str:
    """
    Returns a path tree according to the timestamp given.

    The directory structure will have the form: root/<YYYY>/<MM>/<YYYY-MM-DD>
    If no root directory is given, this method will return just the relative path stub:
    <YYYY>/<MM>/<YYYY-MM-DD>

    Parameters
    ----------
    timestamp : datetime.datetime, optional
        Timestamp for which to create the daily directory. Defaults to current timestamp if not provided.
    root : str, optional
        Root path for the daily directory structure. If not provided, only the relative path stub is returned.
    create_missing : bool, optional
        Indicates if the directory should be created (True) or not (False). Only considered if root is given.

    Returns
    -------
    str
        Path representing the directory structure based on the timestamp.

    """
    if timestamp is None:
        timestamp = datetime.datetime.now()

    day_dir = timestamp.strftime("%Y-%m-%d")
    year_dir, month_dir = day_dir.split("-")[:2]
    daily_path = os.path.join(year_dir, month_dir, day_dir)
    if root is not None:
        daily_path = os.path.join(root, daily_path)
        if create_missing:
            os.makedirs(daily_path, exist_ok=True)
    return daily_path


def get_module_app_data_path(cls_name: str, module_base: str, module_name: str) -> str:
    """Constructs the appData file path for the given qudi module"""
    file_name = f"status-{cls_name}_{module_base}_{module_name}.cfg"
    return os.path.join(get_appdata_dir(), file_name)
