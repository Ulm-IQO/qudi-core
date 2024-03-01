# -*- coding: utf-8 -*-
"""
Check if something is a rpyc remotemodules object and transfer it

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

__all__ = ['netobtain', 'connect_to_remote_module_server']

import rpyc
import rpyc.core.netref as _netref
import rpyc.utils.classic as _classic
from typing import Optional


def netobtain(obj):
    """
    """
    if isinstance(obj, _netref.BaseNetref):
        return _classic.obtain(obj)
    return obj


def connect_to_remote_module_server(host: str,
                                    port: int,
                                    certfile: Optional[str] = None,
                                    keyfile: Optional[str] = None,
                                    protocol_config: Optional[dict] = None) -> rpyc.Connection:
    """ Helper method to connect to a qudi RemoteModulesServer via rpyc. Returns rpyc connection
    root object.
    """
    if protocol_config is None:
        protocol_config = {'allow_all_attrs'     : True,
                           'allow_setattr'       : True,
                           'allow_delattr'       : True,
                           'allow_pickle'        : True,
                           'sync_request_timeout': 3600}
    if certfile and keyfile:
        connection = rpyc.ssl_connect(host=host,
                                      port=port,
                                      config=protocol_config,
                                      certfile=certfile,
                                      keyfile=keyfile)
    else:
        connection = rpyc.connect(host=host,
                                  port=port,
                                  config=protocol_config)
    return connection
