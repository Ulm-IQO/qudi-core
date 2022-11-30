# -*- coding: utf-8 -*-

import sys
from setuptools import setup, find_namespace_packages


unix_dep = [
    'wheel',
    'cycler',
    'entrypoints',
    'fysom',
    'GitPython',
    'jupyter',
    'jupytext',
    'lmfit>=1.0.3',
    'matplotlib',
    'numpy',
    'pyqtgraph>=0.13.0',
    'PySide2==5.15.2',
    'rpyc>=5.0.1',
    'ruamel.yaml>=0.17.16',
    'scipy>=1.7.1',
    'jsonschema>=4.2.1',
]

windows_dep = [
    'wheel>=0.37.0',
    'cycler>=0.10.0',
    'entrypoints>=0.3',
    'fysom>=2.1.6',
    'GitPython>=3.1.24',
    'jupyter>=1.0.0',
    'jupytext>=1.13.0',
    'lmfit>=1.0.3',
    'matplotlib>=3.4.3',
    'numpy>=1.21.3',
    'pyqtgraph>=0.13.0',
    'PySide2==5.15.2',
    'rpyc>=5.0.1',
    'ruamel.yaml>=0.17.16',
    'scipy>=1.7.1',
    'jsonschema>=4.2.1',
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
                  },
    description='A modular measurement application framework',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Ulm-IQO/qudi-core',
    project_urls={'Documentation': 'https://ulm-iqo.github.io/qudi-core/',
                  'Source Code': 'https://github.com/Ulm-IQO/qudi-core/',
                  'Bug Tracker': 'https://github.com/Ulm-IQO/qudi-core/issues/',
                  },
    keywords=['qudi',
              'diamond',
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
    python_requires='>=3.8, <3.10',
    classifiers=['Development Status :: 5 - Production/Stable',

                 'Environment :: Win32 (MS Windows)',
                 'Environment :: X11 Applications',
                 'Environment :: MacOS X',

                 'Intended Audience :: Developers',
                 'Intended Audience :: Science/Research',
                 'Intended Audience :: End Users/Desktop',

                 'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',

                 'Natural Language :: English',

                 'Operating System :: Microsoft :: Windows :: Windows 8',
                 'Operating System :: Microsoft :: Windows :: Windows 8.1',
                 'Operating System :: Microsoft :: Windows :: Windows 10',
                 'Operating System :: MacOS :: MacOS X',
                 'Operating System :: Unix',
                 'Operating System :: POSIX :: Linux',

                 'Programming Language :: Python :: 3.8',
                 'Programming Language :: Python :: 3.9',

                 'Topic :: Scientific/Engineering',
                 'Topic :: Software Development :: Libraries :: Application Frameworks',
                 'Topic :: Software Development :: User Interfaces',
                 ],
    entry_points={
        'console_scripts': ['qudi=qudi.runnable:main',
                            'qudi-config-editor=qudi.tools.config_editor.config_editor:main',
                            'qudi-uninstall-kernel=qudi.core.qudikernel:uninstall_kernel',
                            'qudi-install-kernel=qudi.core.qudikernel:install_kernel'
                            ]
    },
    zip_safe=False
)
