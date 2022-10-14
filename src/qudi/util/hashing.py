# -*- coding: utf-8 -*-

"""
Utility functions for hashing.

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

__all__ = ['hash_directories', 'hash_files']

import os
import hashlib
from typing import Optional, Iterable


def hash_directories(root_dirs: Iterable[str], buffer_size: Optional[int] = -1) -> str:
    checksum = hashlib.md5()
    for path in root_dirs:
        for root, dirs, files in os.walk(path):
            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'rb') as fd:
                        while chunk := fd.read(buffer_size):
                            checksum.update(chunk)
                    checksum.update(filepath.encode('utf-8'))
                except OSError:
                    pass
    return checksum.hexdigest()


def hash_files(files: Iterable[str],
               buffer_size: Optional[int] = -1,
               root_dir: Optional[str] = None
               ) -> str:
    checksum = hashlib.md5()
    for path in files:
        if root_dir:
            path = os.path.join(root_dir, path)
        try:
            with open(path, 'rb') as fd:
                while chunk := fd.read(buffer_size):
                    checksum.update(chunk)
            checksum.update(path.encode('utf-8'))
        except OSError:
            pass
    return checksum.hexdigest()
