# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

# -*- coding: utf-8 -*-

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']

source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Hypothesis'
copyright = u'2015, David R. MacIver'
author = u'David R. MacIver'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
version = '0.7'
release = '0.7'

language = None

exclude_patterns = ['_build']

pygments_style = 'sphinx'

todo_include_todos = False


# -- Options for HTML output ----------------------------------------------

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
