# -*- coding: utf-8 -*-

"""
Run this module in order to compile and install the qudi resources (files in qudi/resources
namespace)

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

__all__ = ['main', 'build_resources']

import argparse
from qudi.util.resources import ResourceCompiler


def build_resources(resource_name: str, resource_root: str) -> None:
    rc = ResourceCompiler(resource_name=resource_name, resource_root=resource_root)
    rc.find_resource_paths(file_endings='', include_subdirs=True)  # include any files in root dir
    rc.write_rcc_file()


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Collect and compile resource files (icons, stylesheets etc.) for qudi.'
    )
    parser.add_argument('name', help='The name of the resource collection, e.g. "my-qudi-addon"')
    parser.add_argument('root_dir', help='The root directory path to search resource files in')
    args = parser.parse_args()
    build_resources(resource_name=args.name, resource_root=args.root_dir)


if __name__ == '__main__':
    main()
