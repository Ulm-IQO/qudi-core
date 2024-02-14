# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

sys.path.insert(0, os.path.abspath('../src/qudi/'))

project = 'qudi-core'
copyright = '2024, Ulm IQO'
author = 'Ulm IQO'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

    # 'IPython.sphinxext.ipython_console_highlighting',
    # 'nbsphinx',
extensions = [
    'IPython.sphinxext.ipython_directive',
    'IPython.sphinxext.ipython_directive',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.viewcode',
    'numpydoc',
    'sphinx_rtd_dark_mode',
]

templates_path = ['templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '**.ipynb_checkpoints']

autosummary_generate = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = 'pydata_sphinx_theme'
# html_theme = 'sphinx_book_theme'
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    "navigation_with_keys": False,  # See https://github.com/pydata/pydata-sphinx-theme/issues/1492
}
default_dark_mode = False  # For sphinx_rtd_dark_mode. Dark mode needs tweaking so not defaulting to it yet.
html_static_path = []  # Normally defaults to '_static' but we don't have any static files.

numpydoc_show_class_members = False
numpydoc_show_inherited_class_members = False
numpydoc_class_members_toctree = False
