# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

# -*- coding: utf-8 -*-

from __future__ import division, print_function, absolute_import

import os
import sys
import datetime

sys.path.append(
    os.path.join(os.path.dirname(__file__), '..', 'src')
)


autodoc_member_order = 'bysource'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.extlinks',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
]

templates_path = ['_templates']

source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Hypothesis'
copyright = u'2013-%s, David R. MacIver' % datetime.datetime.utcnow().year
author = u'David R. MacIver'

_d = {}
with open(os.path.join(os.path.dirname(__file__), '..', 'src',
                       'hypothesis', 'version.py')) as f:
    exec(f.read(), _d)
    version = _d['__version__']
    release = _d['__version__']

language = None

exclude_patterns = ['_build']

pygments_style = 'sphinx'

todo_include_todos = False

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'numpy': ('https://docs.scipy.org/doc/numpy/', None),
    'pandas': ('https://pandas.pydata.org/pandas-docs/stable/', None),
    'pytest': ('https://docs.pytest.org/en/stable/', None),
    'django': ('https://django.readthedocs.io/en/stable/', None),
    'attrs': ('http://www.attrs.org/en/stable/', None),
}

autodoc_mock_imports = ['pandas']

doctest_global_setup = '''
# Some standard imports
from hypothesis import *
from hypothesis.strategies import *
# Run deterministically, and don't save examples
import random
_random_state = random.getstate()
random.seed(0)
doctest_settings = settings(database=None, derandomize=True)
settings.register_profile('doctests', doctest_settings)
settings.load_profile('doctests')
# Never show deprecated behaviour in code examples
import warnings
warnings.filterwarnings('error', category=DeprecationWarning)
'''

doctest_global_cleanup = '''
random.setstate(_random_state)
'''

# This config value must be a dictionary of external sites, mapping unique
# short alias names to a base URL and a prefix.
# See http://sphinx-doc.org/ext/extlinks.html
_repo = 'https://github.com/HypothesisWorks/hypothesis/'
extlinks = {
    'commit': (_repo + 'commit/%s', 'commit '),
    'gh-file': (_repo + 'blob/master/%s', ''),
    'gh-link': (_repo + '%s', ''),
    'issue': (_repo + 'issues/%s', 'issue #'),
    'pull': (_repo + 'pull/%s', 'pull request #'),
    'pypi': ('https://pypi.org/project/%s', ''),
    'bpo': ('https://bugs.python.org/issue%s', 'bpo-'),
}

# -- Options for HTML output ----------------------------------------------

if os.environ.get('READTHEDOCS', None) != 'True':
    # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

html_static_path = ['_static']

htmlhelp_basename = 'Hypothesisdoc'

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
}

latex_documents = [
    (master_doc, 'Hypothesis.tex', u'Hypothesis Documentation',
     u'David R. MacIver', 'manual'),
]

man_pages = [
    (master_doc, 'hypothesis', u'Hypothesis Documentation',
     [author], 1)
]

texinfo_documents = [
    (master_doc, 'Hypothesis', u'Hypothesis Documentation',
     author, 'Hypothesis', 'Advanced property-based testing for Python.',
     'Miscellaneous'),
]
