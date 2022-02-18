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

import os
import sys
import subprocess
from typing import Optional, Sequence, List


class ResourceCompiler:
    """ ToDo: Document
    """
    def __init__(self, resource_root: Optional[str] = None) -> None:
        if resource_root is None:
            resource_root = os.path.abspath('.')
        if not os.path.isdir(resource_root):
            raise NotADirectoryError(f'"resource_root" path is not a directory: {resource_root}')
        self.resource_root = resource_root
        self.icon_paths = list()
        self.stylesheet_paths = list()
        self.image_paths = list()

    def find_svg_icons(self, subdir: Optional[str] = None) -> None:
        resource_paths = self._find_resource_paths(file_endings=['svg', 'svgz'],
                                                   subdir=subdir,
                                                   recursive=True)
        self.icon_paths.extend(resource_paths)

    def find_qss_stylesheets(self, subdir: Optional[str] = None) -> None:
        resource_paths = self._find_resource_paths(file_endings=['qss'],
                                                   subdir=subdir,
                                                   recursive=True)
        self.stylesheet_paths.extend(resource_paths)

    def find_png_images(self, subdir: Optional[str] = None) -> None:
        resource_paths = self._find_resource_paths(file_endings=['png'],
                                                   subdir=subdir,
                                                   recursive=True)
        self.image_paths.extend(resource_paths)

    def _find_resource_paths(self,
                             file_endings: Sequence[str],
                             subdir: Optional[str] = None,
                             recursive: Optional[bool] = False) -> List[str]:
        search_path = os.path.join(self.resource_root, subdir) if subdir else self.resource_root
        resources = list()
        for root, dirs, files in os.walk(search_path):
            prefix = os.path.relpath(root, self.resource_root).strip('.').replace(os.path.sep, '/')
            if prefix:
                resources.extend(
                    f'{prefix}/{f}' for f in files if f.rsplit('.', 1)[-1] in file_endings
                )
            else:
                resources.extend(
                    f'{f.rsplit(".", 1)[0]}' for f in files if f.rsplit('.', 1)[-1] in file_endings
                )
            if not recursive:
                break
        return resources

    def create_binary_rcc(self, rcc_path: str):
        target_dir = os.path.dirname(rcc_path)
        if not os.path.isdir(target_dir):
            raise NotADirectoryError(f'target directory for .rcc file not found at "{target_dir}".')

        qrc_path = self._write_qrc_file()
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
        finally:
            os.remove(qrc_path)

    def _compile_qrc(self) -> str:
        qrc_lines = ['<!DOCTYPE RCC><RCC version="1.0">']
        # Add icons
        resource_paths = set(self.icon_paths)
        if resource_paths:
            qrc_lines.append(f'<qresource prefix="/icons">')
            qrc_lines.extend(
                f'\t<file alias="{p.rsplit(".", 1)[0].rsplit("/", 1)[-1]}">{p}</file>' for p in
                resource_paths
            )
            qrc_lines.append('</qresource>')
        # Add stylesheets
        resource_paths = set(self.stylesheet_paths)
        if resource_paths:
            qrc_lines.append(f'<qresource prefix="/stylesheets">')
            qrc_lines.extend(
                f'\t<file alias="{p.rsplit(".", 1)[0].rsplit("/", 1)[-1]}">{p}</file>' for p in
                resource_paths)
            qrc_lines.append('</qresource>')
        # Add images
        resource_paths = set(self.image_paths)
        if resource_paths:
            qrc_lines.append(f'<qresource prefix="/images">')
            qrc_lines.extend(
                f'\t<file alias="{p.rsplit(".", 1)[0].rsplit("/", 1)[-1]}">{p}</file>' for p in
                resource_paths)
            qrc_lines.append('</qresource>')
        qrc_lines.append('</RCC>')
        return '\n'.join(qrc_lines)

    def _write_qrc_file(self) -> str:
        compiled = self._compile_qrc()
        path = os.path.join(self.resource_root, 'tmp.qrc')
        try:
            with open(path, 'w') as file:
                file.write(compiled)
        except:
            try:
                os.remove(path)
            except OSError:
                pass
            raise
        return path
