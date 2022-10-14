# -*- coding: utf-8 -*-

"""
ToDo: Document

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

__all__ = ['init_resources', 'print_resource_tree', 'ResourceCompiler']

import os
import sys
import importlib
import subprocess
from PySide2.QtCore import QDirIterator
from typing import Optional, Sequence, List, Union


from qudi.util.paths import get_resources_dir


def init_resources():
    resource_root = get_resources_dir(create_missing=True)
    resource_modules = [
        f.rsplit('.', 1)[0] for f in os.listdir(resource_root) if f.endswith('_rc.py')
    ]
    if resource_modules:
        if resource_root not in sys.path:
            sys.path.append(resource_root)
        for mod in resource_modules:
            importlib.import_module(mod)


def print_resource_tree(root=':/', level=0):
    ident = '  ' * level
    it = QDirIterator(root)
    while it.hasNext():
        item = it.next()
        print(f'{ident}{item}')
        print_resource_tree(item, level=level+1)


class ResourceCompiler:
    """ ToDo: Document
    """
    def __init__(self, resource_name: str, resource_root: Optional[str] = None) -> None:
        if resource_root is None:
            resource_root = '.'
        resource_root = os.path.normpath(os.path.abspath(resource_root))
        if not os.path.isdir(resource_root):
            raise NotADirectoryError(f'"resource_root" path is not a directory: {resource_root}')
        self.resource_root = resource_root
        self.resource_name = '_'.join(resource_name.replace('-', '_').split())
        self.qrc_filename = f'{self.resource_name}.qrc'
        self.rcc_filename = f'{self.resource_name}_rc.py'
        self.resource_paths = list()
        self._qrc_written = os.path.exists(os.path.join(self.resource_root, self.qrc_filename))

    def find_svg_paths(self, include_subdirs: Optional[bool] = True) -> List[str]:
        return self.find_resource_paths(file_endings=['.svg', '.svgz'],
                                        include_subdirs=include_subdirs)

    def find_qss_paths(self, include_subdirs: Optional[bool] = True) -> List[str]:
        return self.find_resource_paths(file_endings=['.qss'], include_subdirs=include_subdirs)

    def find_png_paths(self, include_subdirs: Optional[bool] = True) -> List[str]:
        return self.find_resource_paths(file_endings=['.png'], include_subdirs=include_subdirs)

    def find_cfg_paths(self, include_subdirs: Optional[bool] = True) -> List[str]:
        return self.find_resource_paths(file_endings=['.cfg'], include_subdirs=include_subdirs)

    def find_resource_paths(self,
                            file_endings: Union[str, Sequence[str]],
                            include_subdirs: Optional[bool] = True) -> List[str]:
        if not isinstance(file_endings, str):
            file_endings = tuple(file_endings)
        resources = list()
        for root, dirs, files in os.walk(self.resource_root):
            prefix = os.path.relpath(root, self.resource_root).strip('.')
            resources.extend(
                os.path.join(prefix, f).replace('\\', '/') for f in files if
                f.endswith(file_endings) and f != self.qrc_filename
            )
            if not include_subdirs:
                break
        self.resource_paths.extend(resources)
        if resources:
            self._qrc_written = False
        return resources

    def write_qrc_file(self) -> str:
        path = os.path.join(self.resource_root, self.qrc_filename)
        compiled = self._compile_qrc()
        try:
            with open(path, 'w') as file:
                file.write(compiled)
            self._qrc_written = True
        except:
            try:
                os.remove(path)
            except OSError:
                pass
            raise
        return path

    def write_rcc_file(self) -> str:
        rcc_path = os.path.join(get_resources_dir(create_missing=True), self.rcc_filename)
        qrc_path = os.path.join(self.resource_root, f'{self.resource_name}.qrc')
        if not self._qrc_written:
            qrc_path = self.write_qrc_file()
        try:
            subprocess.run(['pyside2-rcc', '-g', 'python', qrc_path, '-o', rcc_path],
                           text=True,
                           check=True)
        except subprocess.CalledProcessError:
            try:
                os.remove(rcc_path)
            except OSError:
                pass
            raise
        return rcc_path

    def _compile_qrc(self) -> str:
        qrc_lines = ['<!DOCTYPE RCC><RCC version="1.0">']
        resource_paths = set(self.resource_paths)
        if resource_paths:
            qrc_lines.append(f'<qresource>')
            qrc_lines.extend(f'\t<file>{p}</file>' for p in resource_paths)
            qrc_lines.append('</qresource>')
        qrc_lines.append('</RCC>')
        return '\n'.join(qrc_lines)
