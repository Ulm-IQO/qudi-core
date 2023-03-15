# -*- coding: utf-8 -*-
"""
This file contains the Qudi tools for remote module sharing via rpyc server.

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

__all__ = ('connect_to_remote_module_server', 'BaseServer', 'RemoteModulesServer', 'QudiNamespaceServer')

import ssl
import rpyc
import weakref
from PySide2 import QtCore
from rpyc.utils.authenticators import SSLAuthenticator
from typing import Optional

from qudi.util.mutex import Mutex
from qudi.core.logger import get_logger
from qudi.core.services import RemoteModulesService, QudiNamespaceService

logger = get_logger(__name__)


def connect_to_remote_module_server(host: str,
                                    port: int,
                                    certfile: Optional[str] = None,
                                    keyfile: Optional[str] = None,
                                    protocol_config: Optional[dict] = None):
    """ Helper method to connect to a qudi RemoteModuleServer via rpyc. Returns an rpyc connection
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
    logger.debug(f'Connected to RemoteModulesServer on {host}:{port:d}')
    return connection


class _ServerRunnable(QtCore.QObject):
    """ QObject containing the actual long-running code to execute in a separate thread for qudi
    RPyC servers.
    """

    def __init__(self, service, host, port, certfile=None, keyfile=None, protocol_config=None,
                 ssl_version=None, cert_reqs=None, ciphers=None):
        super().__init__()

        self.service = service
        self.server = None

        self.host = host
        self.port = port
        self.certfile = certfile
        self.keyfile = keyfile
        if protocol_config is None:
            self.protocol_config = {'allow_all_attrs'     : True,
                                    'allow_setattr'       : True,
                                    'allow_delattr'       : True,
                                    'allow_pickle'        : True,
                                    'sync_request_timeout': 3600}
        else:
            self.protocol_config = protocol_config
        self.ssl_version = ssl.PROTOCOL_TLSv1_2 if ssl_version is None else ssl_version
        self.cert_reqs = ssl.CERT_REQUIRED if cert_reqs is None else cert_reqs
        self.ciphers = 'EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH' if ciphers is None else ciphers

    @QtCore.Slot()
    def run(self):
        """ Start the RPyC server """
        if self.certfile is not None and self.keyfile is not None:
            authenticator = SSLAuthenticator(certfile=self.certfile,
                                             keyfile=self.keyfile,
                                             cert_reqs=self.cert_reqs,
                                             ssl_version=self.ssl_version,
                                             ciphers=self.ciphers)
        else:
            authenticator = None

        try:
            self.server = rpyc.ThreadedServer(self.service,
                                              hostname=self.host,
                                              port=self.port,
                                              protocol_config=self.protocol_config,
                                              authenticator=authenticator)
            logger.info(f'Starting RPyC server "{self.thread().objectName()}" on '
                        f'[{self.host}]:{self.port:d}')
            logger.debug(f'{self.thread().objectName()}: '
                         f'protocol_config is {self.protocol_config}, '
                         f'authenticator is {authenticator}')
            self.server.start()
        except:
            logger.exception(f'Error during start of RPyC Server "{self.thread().objectName()}":')
            self.server = None

    @QtCore.Slot()
    def stop(self):
        """ Stop the RPyC server """
        if self.server is not None:
            try:
                self.server.close()
                logger.info(f'Stopped RPyC server on [{self.host}]:{self.port:d}')
            except:
                logger.exception(
                    f'Exception while trying to stop RPyC server on [{self.host}]:{self.port:d}'
                )
            finally:
                self.server = None


class BaseServer(QtCore.QObject):
    """ Contains a threaded RPyC server providing given service.
    USE SSL AUTHENTICATION WHEN LISTENING ON ANYTHING ELSE THAN "localhost"/127.0.0.1.
    Actual RPyC server runs in a QThread.
    """

    def __init__(self, qudi, service_instance, name, host, port, certfile=None,
                 keyfile=None, protocol_config=None, ssl_version=None, cert_reqs=None,
                 ciphers=None, parent=None):
        """
        @param int port: port the RPyC server should listen to
        """
        super().__init__(parent=parent)

        self.__qudi_ref = weakref.ref(qudi)
        self._thread_lock = Mutex()

        self.service = service_instance
        self._name = name
        self._server = _ServerRunnable(service=service_instance,
                                       host=host,
                                       port=port,
                                       certfile=certfile,
                                       keyfile=keyfile,
                                       protocol_config=protocol_config,
                                       ssl_version=ssl_version,
                                       cert_reqs=cert_reqs,
                                       ciphers=ciphers)

    @property
    def server(self):
        return self._server.server

    @property
    def is_running(self):
        with self._thread_lock:
            return self._server.server is not None

    @property
    def _qudi(self):
        qudi = self.__qudi_ref()
        if qudi is None:
            raise RuntimeError('Dead qudi application reference encountered')
        return qudi

    @property
    def _thread_manager(self):
        manager = self._qudi.thread_manager
        if manager is None:
            raise RuntimeError('No thread manager initialized in qudi application')
        return manager

    @property
    def _module_manager(self):
        manager = self._qudi.module_manager
        if manager is None:
            raise RuntimeError('No module manager initialized in qudi application')
        return manager

    @QtCore.Slot()
    def start(self):
        """ Start the RPyC server
        """
        with self._thread_lock:
            if self.server is None:
                thread = self._thread_manager.get_new_thread(self._name)
                self._server.moveToThread(thread)
                thread.started.connect(self._server.run)
                thread.start()
            else:
                logger.warning(f'RPyC server "{self._name}" is already running.')

    @QtCore.Slot()
    def stop(self):
        """ Stop the RPyC server
        """
        with self._thread_lock:
            if self.server is not None:
                try:
                    self._server.stop()
                finally:
                    thread_manager = self._thread_manager
                    thread_manager.quit_thread(self._name)
                    thread_manager.join_thread(self._name, time=5)


class RemoteModulesServer(BaseServer):
    """
    """

    def __init__(self, **kwargs):
        kwargs['service_instance'] = RemoteModulesService(
            module_manager=kwargs['qudi'].module_manager
        )
        super().__init__(**kwargs)

    def share_module(self, module_name: str):
        self.service.share_module(module_name)

    def remove_shared_module(self, module_name: str):
        self.service.remove_shared_module(module_name)


class QudiNamespaceServer(BaseServer):
    """ Contains a RPyC server that serves all activated qudi modules as well as a reference to the
    running qudi instance locally without encryption.
    You can specify the port but the host will always be "localhost"/127.0.0.1
    See qudi.core.remotemodules.RemoteModuleServer if you want to expose qudi modules to non-local
    clients.
    Actual rpyc server runs in a QThread.
    """

    def __init__(self, qudi, name, port, force_remote_calls_by_value=False, parent=None):
        """
        @param qudi.Qudi qudi: The governing qudi main application instance
        @param str name: Server name (used as name for the associated QThread)
        @param int port: port the RPyC server should listen to
        @param PySide2.QtCore.QObject parent: optional, parent Qt QObject
        """
        service_instance = QudiNamespaceService(
            qudi=qudi,
            force_remote_calls_by_value=force_remote_calls_by_value
        )
        super().__init__(parent=parent,
                         qudi=qudi,
                         service_instance=service_instance,
                         name=name,
                         host='localhost',
                         port=port)
