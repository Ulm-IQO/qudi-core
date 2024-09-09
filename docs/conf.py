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
# 'IPython.sphinxext.ipython_directive',
extensions = [
    'numpydoc',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx.ext.doctest', 
    'sphinx.ext.coverage'
]
intersphinx_mapping = {
    'PySide2': (
        'https://doc.qt.io/qtforpython-5',
        None,
    ),  # This is broken, some bug with PySide2 (and PySide6). See https://bugreports.qt.io/browse/PYSIDE-2215
}
# 'lmfit': ('https://lmfit.github.io/lmfit-py/', None),

templates_path = ['templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '**.ipynb_checkpoints']

autosummary_generate = True
autosummary_ignore_module_all = False
autosummary_imported_members = False
autodoc_mock_imports = ['lmfit']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'pydata_sphinx_theme'
html_logo = "../src/qudi/artwork/logo/logo_qudi.ico"
html_theme_options = {
    "logo": {
        "text": "Qudi-Core",
        "image_dark": "../src/qudi/artwork/logo/logo_qudi.ico",
    },
    'dark_mode': True,
    "navbar_start": ["navbar-logo"],
    "navbar_center": ["navbar-nav"],
    "navbar_end": ["navbar-icon-links"],
    "navbar_persistent": ["theme-switcher", "search-button"],
    "footer_start": ["copyright", "sphinx-version"],
    "footer_end": ["theme-version"],
    "show_toc_level": 1,
    "show_nav_level": 4,
    "collapse_navigation": True,
    "sidebar_hide_name": False,
    'navigation_with_keys': False,  # See https://github.com/pydata/pydata-sphinx-theme/issues/1492
}

html_sidebars = {
    "**": ["sidebar-nav-bs", "sidebar-ethical-ads"]
}
html_static_path = ['_static']
# html_css_files = [
#     'custom.css',
# ]




default_dark_mode = True  # For sphinx_rtd_dark_mode. Dark mode needs tweaking so not defaulting to it yet.

numpydoc_show_class_members = False
numpydoc_show_inherited_class_members = False
numpydoc_class_members_toctree = False

# Example autodoc settings
autodoc_default_options = {
    'members': True,    # Document all members (methods and attributes)
    'undoc-members': False,   # Include members without docstrings
    'show-inheritance': True,
    'inherited-members': False   # Show inheritance links
    # Other options as needed
}

# napoleon_numpy_docstring = True
# napoleon_google_docstring = False
# napoleon_include_init_with_doc = True
# napoleon_include_private_with_doc = False
# napoleon_include_special_with_doc = True
# napoleon_use_param = True
# napoleon_use_rtype = True


# This gives the full name of the inherited classes in the documentation. It would be better if we could
# just reference the documentation externally with intersphinx but it's not working correctly. Sphinx
# ends up documenting the entire inherited base class instead of just linking to it. It could be a problem
# caused by numpydoc, not sure yet.
def process_bases(app, name, obj, options, bases):
    for i, base in enumerate(bases):
        bases[i] = ':py:class:`' + base.__module__ + '.' + base.__name__ + '`'


def setup(app):
    app.connect('autodoc-process-bases', process_bases)
