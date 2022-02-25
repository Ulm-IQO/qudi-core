# -*- coding: utf-8 -*-

"""
Run this module in order to compile and install the qudi-core resources (most stuff in qudi/artwork)

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

import argparse
from qudi.util.resources import ResourceCompiler


def main(resource_name: str, resource_root: str) -> None:
    print(f'> Building resources "{resource_name}" for qudi from {resource_root} ...')
    rc = ResourceCompiler(resource_name=resource_name, resource_root=resource_root)
    rc.find_png_paths()
    rc.find_svg_paths()
    rc.find_qss_paths()
    rc.write_qrc_file()
    rc.write_rcc_file()
    print(f'> Resources "{resource_name}" built successfully')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Collect and compile resource files (icons, stylesheets etc.) for qudi.'
    )
    parser.add_argument('name', help='The name of the resource collection, e.g. "my-qudi-addon"')
    parser.add_argument('root_dir', help='The root directory path to search resource files in')
    args = parser.parse_args()

    main(resource_name=args.name, resource_root=args.root_dir)
