# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import datetime
import re
import sys
import types
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.append(str(root / "src"))
sys.path.append(str(Path(__file__).parent / "_ext"))

needs_sphinx = re.search(
    r"sphinx==([0-9\.]+)", root.joinpath("../requirements/tools.txt").read_text()
).group(1)
default_role = "py:obj"
nitpicky = True

autodoc_member_order = "bysource"
autodoc_typehints = "none"
maximum_signature_line_length = 60  # either one line, or one param per line

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "hoverxref.extension",
    "sphinx_codeautolink",
    "sphinx_selective_exclude.eager_only",
    "sphinx-jsonschema",
    # loading this extension overrides the default -b linkcheck behavior with
    # custom url ignore logic. see hypothesis_linkcheck.py for details.
    "hypothesis_linkcheck",
]

templates_path = ["_templates"]

source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# General information about the project.
project = "Hypothesis"
author = "David R. MacIver"
copyright = f"2013-{datetime.date.today().year}, {author}"

_d = {}
_version_file = root.joinpath("src", "hypothesis", "version.py")
exec(_version_file.read_text(encoding="utf-8"), _d)
version = _d["__version__"]
release = _d["__version__"]


def setup(app):
    if root.joinpath("RELEASE.rst").is_file():
        app.tags.add("has_release_file")

    # Workaround for partial-initialization problem when autodoc imports libcst
    import libcst

    import hypothesis.extra.codemods

    assert libcst
    assert hypothesis.extra.codemods

    # patch in mock array_api namespace so we can autodoc it
    from hypothesis.extra.array_api import (
        RELEASED_VERSIONS,
        make_strategies_namespace,
        mock_xp,
    )

    mod = types.ModuleType("xps")
    mod.__dict__.update(
        make_strategies_namespace(mock_xp, api_version=RELEASED_VERSIONS[-1]).__dict__
    )
    assert "xps" not in sys.modules
    sys.modules["xps"] = mod


language = "en"
exclude_patterns = ["_build"]
pygments_style = "sphinx"
todo_include_todos = False

# To run linkcheck (last argument is the output dir)
#   sphinx-build --builder linkcheck hypothesis-python/docs linkcheck
linkcheck_ignore = [
    # we'll assume that python isn't going to break peps, and github isn't going
    # to break issues/pulls. (and if they did, we'd hopefully notice quickly).
    r"https://peps.python.org/pep-.*",
    r"https://github.com/HypothesisWorks/hypothesis/issues/\d+",
    r"https://github.com/HypothesisWorks/hypothesis/pull/\d+",
]

# See https://sphinx-hoverxref.readthedocs.io/en/latest/configuration.html
hoverxref_auto_ref = True
hoverxref_domains = ["py"]
hoverxref_role_types = {
    "attr": "tooltip",
    "class": "tooltip",
    "const": "tooltip",
    "exc": "tooltip",
    "func": "tooltip",
    "meth": "tooltip",
    "mod": "tooltip",
    "obj": "tooltip",
    "ref": "tooltip",
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable/", None),
    "pytest": ("https://docs.pytest.org/en/stable/", None),
    "django": ("https://django.readthedocs.io/en/stable/", None),
    "dateutil": ("https://dateutil.readthedocs.io/en/stable/", None),
    "redis": ("https://redis-py.readthedocs.io/en/stable/", None),
    "attrs": ("https://www.attrs.org/en/stable/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
    "IPython": ("https://ipython.readthedocs.io/en/stable/", None),
    "lark": ("https://lark-parser.readthedocs.io/en/stable/", None),
}

autodoc_mock_imports = ["numpy", "pandas", "redis", "django", "pytz"]

codeautolink_autodoc_inject = False
codeautolink_global_preface = """
from hypothesis import *
import hypothesis.strategies as st
from hypothesis.strategies import *
"""

# This config value must be a dictionary of external sites, mapping unique
# short alias names to a base URL and a prefix.
# See http://sphinx-doc.org/ext/extlinks.html
_repo = "https://github.com/HypothesisWorks/hypothesis/"
extlinks = {
    "commit": (_repo + "commit/%s", "commit %s"),
    "gh-file": (_repo + "blob/master/%s", "%s"),
    "gh-link": (_repo + "%s", "%s"),
    "issue": (_repo + "issues/%s", "issue #%s"),
    "pull": (_repo + "pull/%s", "pull request #%s"),
    "pypi": ("https://pypi.org/project/%s/", "%s"),
    "bpo": ("https://bugs.python.org/issue%s", "bpo-%s"),
    "xp-ref": ("https://data-apis.org/array-api/latest/API_specification/%s", "%s"),
    "wikipedia": ("https://en.wikipedia.org/wiki/%s", "%s"),
}

# -- Options for HTML output ----------------------------------------------

html_theme = "sphinx_rtd_theme"

html_static_path = ["_static"]

html_css_files = ["better-signatures.css", "wrap-in-tables.css"]

htmlhelp_basename = "Hypothesisdoc"

html_favicon = "../../brand/favicon.ico"

html_logo = "../../brand/dragonfly-rainbow-150w.svg"

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {}

latex_documents = [
    (master_doc, "Hypothesis.tex", "Hypothesis Documentation", author, "manual")
]

man_pages = [(master_doc, "hypothesis", "Hypothesis Documentation", [author], 1)]

texinfo_documents = [
    (
        master_doc,
        "Hypothesis",
        "Hypothesis Documentation",
        author,
        "Hypothesis",
        "Advanced property-based testing for Python.",
        "Miscellaneous",
    )
]
