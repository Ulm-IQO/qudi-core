# -*- coding: utf-8 -*-

"""
Runnable performing the setup of qudi-core, i.e. setting up AppData, compiling resources
(icons, stylesheets, ...) and other stuff.
Needs to run once in order to set up qudi after installing the qudi-core package.
Calling it with the uninstall flag set, will undo everything again, i.e. delete appdata, uninstall
qudi kernel etc.

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

__all__ = ['install', 'uninstall', 'main', 'is_configured', 'hash_resources',
           'hash_compiled_resources']

import os
import argparse
from typing import Optional

from qudi.tools.build_resources import build_resources
from qudi.util.cleanup import clear_appdata, clear_user_data, clear_resources_appdata
from qudi.util.paths import get_qudi_core_dir, get_qudi_package_dirs, get_resources_dir
from qudi.core.qudikernel import install_kernel, uninstall_kernel
from qudi.util.yaml import yaml_dump, yaml_load
from qudi.util.hashing import hash_directories, hash_files


def is_configured() -> bool:
    try:
        resource_hashes = yaml_load(os.path.join(get_resources_dir(), '.checksum'))
    except OSError:
        return False
    buf_size = 16 * 1024 * 1024
    if resource_hashes.get('source', None) != hash_resources(buf_size):
        return False
    if resource_hashes.get('compiled', None) != hash_compiled_resources(buf_size):
        return False
    return True


def hash_resources(buffer_size: Optional[int] = -1) -> str:
    resource_dirs = [
        os.path.join(path, 'resources') for path in get_qudi_package_dirs() if
        os.path.isdir(os.path.join(path, 'resources'))
    ]
    return hash_directories(resource_dirs, buffer_size)


def hash_compiled_resources(buffer_size: Optional[int] = -1) -> str:
    return hash_files((f for f in os.listdir(get_resources_dir()) if f.endswith('_rc.py')),
                      buffer_size,
                      get_resources_dir())


def install() -> None:
    # compile resources from all installed qudi addon packages and qudi-core.
    qudi_paths = [get_qudi_core_dir()]
    tmp = qudi_paths[0].lower()
    qudi_paths.extend(path for path in get_qudi_package_dirs() if path.lower() != tmp)
    clear_resources_appdata()
    for ii, path in enumerate(qudi_paths):
        resource_root = os.path.join(path, 'resources')
        if os.path.exists(resource_root) and os.path.isdir(resource_root):
            remainder, resource_name = os.path.split(os.path.dirname(path))
            # in case of development install, split the name even further
            if resource_name == 'src':
                resource_name = os.path.split(remainder)[-1]
            print(f'> Building resources for "{resource_name}" for qudi from {resource_root} ...')
            build_resources(resource_name=f'{ii:d}_{resource_name}', resource_root=resource_root)
            print(f'> Resources for "{resource_name}" built successfully')

    # resource setup complete
    # calculate hashes for resources to detect future changes
    resource_hashes = {'source': hash_resources(16 * 1024 * 1024),
                       'compiled': hash_compiled_resources(16 * 1024 * 1024)}
    yaml_dump(os.path.join(get_resources_dir(create_missing=True), '.checksum'), resource_hashes)

    # Install qudi IPython kernel
    install_kernel()


def uninstall() -> None:
    uninstall_kernel()
    print(f'> Deleting qudi AppData ...')
    clear_appdata()
    print(f'> qudi AppData deleted')
    try:
        os.remove(os.path.join(get_resources_dir(), '.checksum'))
    except OSError:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description='(Un-)Configure qudi.')
    parser.add_argument(
        '-u',
        '--uninstall',
        action='store_true',
        help='Flag to undo all setup steps performed during configuration/installation.'
    )
    parser.add_argument(
        '-d',
        '--userdata',
        action='store_true',
        help='Flag to also delete all user data from home directory upon uninstall.'
    )
    args = parser.parse_args()
    if args.uninstall:
        print('> Cleaning up qudi...')
        uninstall()
        if args.userdata:
            print(f'> Deleting qudi user data...')
            clear_user_data()
            print(f'> qudi user data deleted')
        print('> qudi cleanup complete')
    else:
        print('> Setting up qudi...')
        install()
        print(f'> qudi setup complete')


if __name__ == '__main__':
    main()
