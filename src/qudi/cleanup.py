# -*- coding: utf-8 -*-

"""
Runnable performing the cleanup of qudi-core, i.e. deleting created AppData and uninstalling the
qudi IPython kernelspec.
Should be run just before uninstalling qudi-core in order to leave no orphaned data behind.

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

__all__ = ['main']

import os
import re
from qudi.util.paths import get_resources_dir, get_appdata_dir
from qudi.core.qudikernel import uninstall_kernel


def clear_module_appdata():
    print('> Clearing qudi modules AppData...')
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
    print('> qudi modules AppData cleared')


def clear_resources_appdata():
    print('> Clearing qudi resources AppData...')
    resources_dir = get_resources_dir()
    if os.path.exists(resources_dir):
        # Remove resources files
        resources_regex = re.compile(r'\A(.+)_rcc.py\Z')
        for root, dirs, files in os.walk(resources_dir):
            for file in files:
                if resources_regex.match(file):
                    try:
                        os.remove(os.path.join(root, file))
                    except OSError:
                        pass
            break
        # Remove __pycache__
        pycache_dir = os.path.join(resources_dir, '__pycache__')
        if os.path.exists(pycache_dir):
            for file in os.listdir(pycache_dir):
                try:
                    os.remove(os.path.join(pycache_dir, file))
                except OSError:
                    pass
            try:
                os.rmdir(pycache_dir)
            except OSError:
                pass
        # Remove resources directory if empty
        try:
            os.rmdir(resources_dir)
        except OSError:
            pass
    print('> qudi resources AppData cleared')


def clear_load_config():
    print('> Clearing qudi load config...')
    load_config_path = os.path.join(get_appdata_dir(), 'load.cfg')
    try:
        os.remove(load_config_path)
    except OSError:
        pass
    print('> qudi load config cleared')


def clear_appdata():
    clear_resources_appdata()
    clear_module_appdata()
    clear_load_config()
    # remove appdata directory if empty
    try:
        os.rmdir(get_appdata_dir())
    except OSError:
        pass


def main():
    print('> Cleaning up qudi...')
    # uninstall qudi kernel
    uninstall_kernel()
    # clear AppData
    clear_appdata()
    print('> qudi cleanup complete')


if __name__ == '__main__':
    main()
