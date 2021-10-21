# -*- coding: utf-8 -*-

import os
import sys
from setuptools import setup, find_namespace_packages
from setuptools.command.develop import develop
from setuptools.command.install import install


class PrePostDevelopCommands(develop):
    """ Pre- and Post-installation script for development mode.
    """

    def run(self):
        # PUT YOUR PRE-INSTALL SCRIPT HERE
        develop.run(self)
        # PUT YOUR POST-INSTALL SCRIPT HERE
        try:
            from qudi.core.qudikernel import install_kernel
            install_kernel()
        except:
            pass


class PrePostInstallCommands(install):
    """ Pre- and Post-installation for installation mode.
    """

    def run(self):
        # PUT YOUR PRE-INSTALL SCRIPT HERE
        install.run(self)
        # PUT YOUR POST-INSTALL SCRIPT HERE
        try:
            from qudi.core.qudikernel import install_kernel
            install_kernel()
        except:
            pass


unix_dep = [
    'wheel',
    'cycler',
    'entrypoints',
    'fysom',
    'GitPython',
    'jupyter',
    'jupytext',
    'lmfit',
    'matplotlib',
    'numpy',
    'pyqtgraph',
    'PySide2',
    'rpyc',
    'ruamel.yaml',
    'scipy',
]

windows_dep = [
    'wheel',
    'cycler',
    'entrypoints',
    'fysom',
    'GitPython',
    'jupyter',
    'jupytext',
    'lmfit',
    'matplotlib',
    'numpy',
    'pyqtgraph',
    'PySide2',
    'rpyc',
    'ruamel.yaml',
    'scipy',
]

with open('VERSION', 'r') as file:
    version = file.read().strip()

with open('README.md', 'r') as file:
    long_description = file.read()

setup(
    name='qudi-core',
    version=version,
    packages=find_namespace_packages(where='src', exclude=['qudi.artwork']),
    package_dir={'': 'src'},
    package_data={'': ['LICENSE', 'LICENSE.LESSER', 'AUTHORS.md', 'README.md', 'VERSION'],
                  'qudi': ['artwork/icons/*',
                           'artwork/icons/**/*',
                           'artwork/icons/**/**/*',
                           'artwork/styles/*',
                           'artwork/styles/**/*',
                           'artwork/styles/**/**/*',
                           'artwork/logo/*',
                           ],
                  'qudi.core': ['default.cfg']
                  },
    description='A modular measurement application framework',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Ulm-IQO/qudi-core',
    keywords=['diamond',
              'quantum',
              'confocal',
              'experiment',
              'measurement',
              'framework',
              'lab',
              'laboratory',
              'instrumentation',
              'instrument',
              'modular'
              ],
    license='LGPLv3',
    install_requires=windows_dep if sys.platform == 'win32' else unix_dep,
    python_requires='~=3.8',
    cmdclass={'develop': PrePostDevelopCommands,
              'install': PrePostInstallCommands},
    entry_points={
        'console_scripts': ['qudi=qudi.runnable:main',
                            'qudi-config-editor=qudi.tools.config_editor.config_editor:main',
                            'qudi-uninstall-kernel=qudi.core.qudikernel:uninstall_kernel',
                            'qudi-install-kernel=qudi.core.qudikernel:install_kernel'
                            ]
    },
    zip_safe=False
)
