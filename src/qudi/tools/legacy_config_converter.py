# -*- coding: utf-8 -*-
"""
This standalone script converts legacy qudi configuration files to the current valid format.

Copyright (c) 2022, the qudi developers. See the AUTHORS.md file at the top-level directory of this
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

import os
import shutil
import argparse
from typing import Optional, Any, Dict, Mapping, Sequence, List, Tuple
from tempfile import NamedTemporaryFile

from qudi.core.config.validator import validate_config, validate_local_module_config
from qudi.core.config.validator import ValidationError
from qudi.core.config.schema import local_module_config_schema
from qudi.util.yaml import DuplicateKeyError, YAMLError, YAMLStreamError, YAML


def read_file(config_file: str) -> str:
    with open(config_file, 'r') as file:
        return file.read()


def write_file(config_file: str, config_string: str) -> None:
    tmp = NamedTemporaryFile(delete=False)
    try:
        tmp.write(config_string)
        shutil.copy(tmp.name, config_file)
    finally:
        tmp.close()
        os.unlink(tmp.name)


def get_config_dict(config_string: str) -> Dict[str, Any]:
    return YAML().load(config_string)


def get_module_index_ranges(config_lines: Sequence[str]) -> List[slice]:
    slices = list()
    in_base = False
    in_module = False
    module_indent = 1
    start_index = 0
    for index, line in enumerate(config_lines):
        if not in_base and line.startswith(('gui:', 'logic:', 'hardware:')):
            in_base = True
            print(index, 'in base')
            continue
        elif in_base and line.startswith('global:'):
            in_base = False
            print(index, 'outside of base')
            continue

        # Continue if line is a comment, empty or not in any module base section
        if not in_base:
            continue
        stripped = line.strip()
        if (not stripped) or stripped.startswith('#'):
            continue

        if in_module and not line[module_indent:].startswith(' '):
            print(index, 'exited module')
            in_module = False
            slices.append(slice(start_index, index))

        if not in_module:
            module_indent = len(line) - len(line.lstrip(' '))
            if module_indent > 0:
                print(index, 'entered module')
                in_module = True
                start_index = index
    slices.append(slice(start_index, len(config_lines)))
    return slices


def group_module_config_options(config_lines: Sequence[str], )


# def test(config_string: str) -> str:
#     orig_lines = config_string.splitlines()
#     new_lines = orig_lines.copy()
#     new_index = 0
#     for orig_index, line in enumerate(orig_lines):
#         stripped = o
#
#     try:
#         while True:
#
#     except IndexError:
#         pass

# def group_module_config_options(config_dict: Mapping[str, Any]) -> Dict[str, Any]:
#     changed_module_configs = dict()
#     # iterate through each module config of each module base section
#     for base in ['gui', 'logic', 'hardware']:
#         for module_name, module_cfg in config_dict.get(base, dict()).items():
#             # Only treat local module configs
#             if 'module.Class' not in module_cfg:
#                 continue
#             # Do nothing if already a valid local module config
#             try:
#                 validate_local_module_config(module_cfg)
#             except ValidationError:
#                 pass
#             else:
#                 continue
#             preserve = [
#                 name for name in local_module_config_schema()['properties'] if name != 'options'
#             ]
#             legacy_option_names = [name for name in module_cfg if name not in preserve]
#             # Do nothing in case no legacy options are present
#             if legacy_option_names:
#                 new_module_config = module_cfg.copy()
#                 new_module_config['options'] = {
#                     key: new_module_config.pop(key) for key in legacy_option_names
#                 }
#                 changed_module_configs[module_name] = new_module_config
#     return changed_module_configs


def get_module_indent(config_string: str) -> str:
    for base in ['gui:', 'logic:', 'hardware:']:
        in_modules = False
        for line in config_string.splitlines():
            if not in_modules and line.startswith(base):
                in_modules = True
            elif in_modules and line.startswith('global:'):
                in_modules = False
            if in_modules:
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and stripped.endswith(':'):
                    indent_len = len(line.rstrip()) - len(stripped)
                    return line[:indent_len]
    # Use 4 spaces as default
    return ' ' * 4


def main(config_file: str, output_file: Optional[str] = None):
    if output_file is None:
        output_file = config_file
    # Read file to convert
    try:
        config_dict = get_config_dict(read_file(config_file))
    except (YAMLError, YAMLStreamError, DuplicateKeyError) as err:
        raise RuntimeError(
            f'Config file to convert ({config_file}) contains invalid YAML syntax.'
        ) from err
    # Group config options in their own JSON Schema property
    group_config_options(config_dict)
    # Validate resulting config and only write to file if validation passes
    try:
        validate_config(config_dict)
    except ValidationError as err:
        raise RuntimeError(
            f'Converted legacy config from "{config_file}" failed to validate. No output file '
            f'written.'
        ) from err
    write_file(config_file, output_file)


if __name__ == '__main__':
    # parse commandline parameters
    parser = argparse.ArgumentParser(prog='python legacy_config_converter.py')
    parser.add_argument(
        'file',
        help='The legacy config file to convert.'
    )
    parser.add_argument(
        '-o',
        '--out',
        action='store',
        default=None,
        help='Specify a custom output file. Default will overwrite the old config file.'
    )
    args = parser.parse_args()



