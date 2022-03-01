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

__all__ = ['install', 'uninstall', 'main']

import os
import argparse
from shutil import copy2
from qudi.tools.build_resources import build_resources
from qudi.util.cleanup import clear_appdata, clear_user_data, clear_resources_appdata
from qudi.util.paths import get_appdata_dir
from qudi.core.qudikernel import install_kernel, uninstall_kernel


def install() -> None:
    # compile resources from all installed qudi addon packages and qudi-core.
    try:
        from qudi import __path__ as _qudi_ns_paths
    except ImportError:
        _qudi_ns_paths = list()
    __tmp = [p.lower() for p in _qudi_ns_paths]
    _qudi_ns_paths = [p for ii, p in enumerate(_qudi_ns_paths) if p.lower() not in __tmp[:ii]]

    core_qudi_path = os.path.abspath(os.path.dirname(__file__))
    qudi_paths = [p for p in _qudi_ns_paths if p.lower() != core_qudi_path.lower()]
    qudi_paths.append(core_qudi_path)
    clear_resources_appdata()
    for path in reversed(qudi_paths):
        resource_root = os.path.join(path, 'resources')
        if os.path.exists(resource_root):
            remainder, resource_name = os.path.split(os.path.dirname(path))
            # in case of development install, split the name even further
            if resource_name == 'src':
                resource_name = os.path.split(remainder)[-1]
            print(f'> Building resources "{resource_name}" for qudi from {resource_root} ...')
            build_resources(resource_name=resource_name, resource_root=resource_root)
            print(f'> Resources "{resource_name}" built successfully')

    # Move default.cfg to AppData directory
    print(f'> Copying default.cfg to AppData ...')
    copy2(src=os.path.join(core_qudi_path, 'resources', 'default.cfg'),
          dst=get_appdata_dir(create_missing=True),
          follow_symlinks=False)
    print(f'> Copied default.cfg to AppData.')

    # Install qudi IPython kernel
    install_kernel()


def uninstall() -> None:
    uninstall_kernel()
    print(f'> Deleting qudi AppData ...')
    clear_appdata()
    print(f'> qudi AppData deleted')


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
