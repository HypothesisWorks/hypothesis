# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

# on_rtd is whether we are on readthedocs.org
import os
import sys
import datetime

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

sys.path.append(
    os.path.join(os.path.dirname(__file__), '..', 'src')
)

from hypothesis import __version__


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

version = __version__
release = __version__

language = None

exclude_patterns = ['_build']

pygments_style = 'sphinx'

todo_include_todos = False

intersphinx_mapping = {
    'python': ('http://docs.python.org/3/', None),
}

autodoc_mock_imports = ['numpy']

doctest_global_setup = '''
# Some standard imports
from hypothesis import *
from hypothesis.strategies import *
# Ensure that output (including from strategies) is deterministic
import random
random.seed(0)
# don't save examples
settings.register_profile('doctests', settings(database=None, strict=True))
settings.load_profile('doctests')
'''

# This config value must be a dictionary of external sites, mapping unique
# short alias names to a base URL and a prefix.
# See http://sphinx-doc.org/ext/extlinks.html
extlinks = {
    'commit': ('https://github.com/HypothesisWorks/hypothesis-python/commit/%s', 'commit '),
    'gh-file': ('https://github.com/HypothesisWorks/hypothesis-python/blob/master/%s', ''),
    'gh-link': ('https://github.com/HypothesisWorks/hypothesis-python/%s', ''),
    'issue': ('https://github.com/HypothesisWorks/hypothesis-python/issues/%s', 'issue #'),
    'pull': ('https://github.com/HypothesisWorks/hypothesis-python/pulls/%s', 'pull request #'),
}

# -- Options for HTML output ----------------------------------------------

if not on_rtd:  # only import and set the theme if we're building docs locally
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
     author, 'Hypothesis', 'One line description of project.',
     'Miscellaneous'),
]
