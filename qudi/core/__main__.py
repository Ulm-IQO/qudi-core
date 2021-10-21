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
"""

import argparse
from qudi.core.application import Qudi

# parse commandline parameters
parser = argparse.ArgumentParser(prog='python -m qudi.core')
parser.add_argument(
    '-g',
    '--no-gui',
    action='store_true',
    help='Run qudi "headless", i.e. without GUI. User interaction only possible via IPython kernel.'
)
parser.add_argument(
    '-d',
    '--debug',
    action='store_true',
    help='Run qudi in debug mode to log all debug messages. Can affect performance.'
)
parser.add_argument(
    '-c',
    '--config',
    default=None,
    help='Path to the configuration file to use for for this qudi session.'
)
parser.add_argument(
    '-l',
    '--logdir',
    default='',
    help='Absolute path to log directory to use instead of the default one "<user_home>/qudi/log/"'
)
args = parser.parse_args()

app = Qudi(no_gui=args.no_gui, debug=args.debug, log_dir=args.logdir, config_file=args.config)
app.run()
