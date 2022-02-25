# -*- coding: utf-8 -*-

"""
Runnable performing the setup of qudi-core, i.e. setting up AppData, compiling resources
(icons, stylesheets, ...) and other stuff.
Needs to run once in order to set up qudi after installing the qudi-core package.

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
from qudi.tools.build_resources import main as build_resources
from qudi.core.qudikernel import install_kernel


def main():
    print('> Setting up qudi-core...')
    # Set up qudi-core resources
    resource_root = os.path.abspath(os.path.join(os.path.dirname(__file__), 'artwork'))
    build_resources(resource_name='qudi-core', resource_root=resource_root)
    # install qudi IPython kernelspec
    install_kernel()
    print(f'> qudi-core setup complete')


if __name__ == '__main__':
    main()
