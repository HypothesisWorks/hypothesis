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
    "hypothesis_redirects",
]

templates_path = ["_templates"]

redirects = {
    "details": "reference/index.html",
    "data": "reference/strategies.html",
    "database": "reference/api.html#database",
    # "stateful": "reference/api.html#stateful-tests",
    "reproducing": "reference/api.html",
    "ghostwriter": "reference/integrations.html#ghostwriter",
    "django": "reference/strategies.html#django",
    "numpy": "reference/strategies.html#numpy",
    "observability": "reference/integrations.html#observability",
    "settings": "reference/api.html#settings",
    "endorsements": "usage.html#testimonials",
    # TODO enable when we actually rename them
    # "extras": "extensions.html",
    "supported": "compatibility.html",
    "changes": "changelog.html",
    "strategies": "extensions.html",
    # these pages were removed without replacement
    "support": "index.html",
    "manifesto": "index.html",
    "examples": "index.html",
}
redirect_html_template_file = "redirect.html.template"

source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# General information about the project.
project = "Hypothesis"
author = "the Hypothesis team"
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
    "django": (
        "http://docs.djangoproject.com/en/stable/",
        "http://docs.djangoproject.com/en/stable/_objects/",
    ),
    "dateutil": ("https://dateutil.readthedocs.io/en/stable/", None),
    "redis": ("https://redis-py.readthedocs.io/en/stable/", None),
    "attrs": ("https://www.attrs.org/en/stable/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
    "IPython": ("https://ipython.readthedocs.io/en/stable/", None),
    "lark": ("https://lark-parser.readthedocs.io/en/stable/", None),
    "xarray": ("https://docs.xarray.dev/en/stable/", None),
}

autodoc_mock_imports = ["numpy", "pandas", "redis", "django", "pytz"]

rst_prolog = """
.. |given| replace:: :func:`~hypothesis.given`
.. |@given| replace:: :func:`@given <hypothesis.given>`
.. |@example| replace:: :func:`@example <hypothesis.example>`
.. |@example.xfail| replace:: :func:`@example(...).xfail() <hypothesis.example.xfail>`
.. |@settings| replace:: :func:`@settings <hypothesis.settings>`
.. |@composite| replace:: :func:`@composite <hypothesis.strategies.composite>`
.. |assume| replace:: :func:`~hypothesis.assume`
.. |target| replace:: :func:`~hypothesis.target`
.. |event| replace:: :func:`~hypothesis.event`
.. |note| replace:: :func:`~hypothesis.note`

.. |max_examples| replace:: :obj:`~hypothesis.settings.max_examples`
.. |settings.max_examples| replace:: :obj:`~hypothesis.settings.max_examples`
.. |settings.database| replace:: :obj:`~hypothesis.settings.database`
.. |settings.deadline| replace:: :obj:`~hypothesis.settings.deadline`
.. |settings.derandomize| replace:: :obj:`~hypothesis.settings.derandomize`
.. |settings.phases| replace:: :obj:`~hypothesis.settings.phases`
.. |settings.print_blob| replace:: :obj:`~hypothesis.settings.print_blob`
.. |settings.report_multiple_bugs| replace:: :obj:`~hypothesis.settings.report_multiple_bugs`
.. |settings.verbosity| replace:: :obj:`~hypothesis.settings.verbosity`
.. |settings.suppress_health_check| replace:: :obj:`~hypothesis.settings.suppress_health_check`

.. |HealthCheck.data_too_large| replace:: :obj:`HealthCheck.data_too_large <hypothesis.HealthCheck.data_too_large>`
.. |HealthCheck.filter_too_much| replace:: :obj:`HealthCheck.filter_too_much <hypothesis.HealthCheck.filter_too_much>`
.. |HealthCheck.too_slow| replace:: :obj:`HealthCheck.too_slow <hypothesis.HealthCheck.too_slow>`
.. |HealthCheck.function_scoped_fixture| replace:: :obj:`HealthCheck.function_scoped_fixture \
<hypothesis.HealthCheck.function_scoped_fixture>`
.. |HealthCheck.differing_executors| replace:: :obj:`HealthCheck.differing_executors \
<hypothesis.HealthCheck.differing_executors>`
.. |HealthCheck| replace:: :obj:`~hypothesis.HealthCheck`

.. |Phase| replace:: :obj:`Phase <hypothesis.Phase>`
.. |Phase.explicit| replace:: :obj:`Phase.explicit <hypothesis.Phase.explicit>`
.. |Phase.reuse| replace:: :obj:`Phase.reuse <hypothesis.Phase.reuse>`
.. |Phase.generate| replace:: :obj:`Phase.generate <hypothesis.Phase.generate>`
.. |Phase.target| replace:: :obj:`Phase.target <hypothesis.Phase.target>`
.. |Phase.shrink| replace:: :obj:`Phase.shrink <hypothesis.Phase.shrink>`
.. |Phase.explain| replace:: :obj:`Phase.explain <hypothesis.Phase.explain>`

.. |Verbosity| replace:: :obj:`~hypothesis.Verbosity`
.. |Verbosity.verbose| replace:: :obj:`Verbosity.verbose <hypothesis.Verbosity.verbose>`
.. |Verbosity.debug| replace:: :obj:`Verbosity.debug <hypothesis.Verbosity.debug>`
.. |Verbosity.normal| replace:: :obj:`Verbosity.normal <hypothesis.Verbosity.normal>`
.. |Verbosity.quiet| replace:: :obj:`Verbosity.quiet <hypothesis.Verbosity.quiet>`

.. |st.lists| replace:: :func:`~hypothesis.strategies.lists`
.. |st.integers| replace:: :func:`~hypothesis.strategies.integers`
.. |st.floats| replace:: :func:`~hypothesis.strategies.floats`
.. |st.booleans| replace:: :func:`~hypothesis.strategies.booleans`
.. |st.none| replace:: :func:`~hypothesis.strategies.none`
.. |st.composite| replace:: :func:`@composite <hypothesis.strategies.composite>`
.. |st.data| replace:: :func:`~hypothesis.strategies.data`
.. |st.one_of| replace:: :func:`~hypothesis.strategies.one_of`
.. |st.text| replace:: :func:`~hypothesis.strategies.text`
.. |st.characters| replace:: :func:`~hypothesis.strategies.characters`
.. |st.tuples| replace:: :func:`~hypothesis.strategies.tuples`
.. |st.sets| replace:: :func:`~hypothesis.strategies.sets`
.. |st.dictionaries| replace:: :func:`~hypothesis.strategies.dictionaries`
.. |st.fixed_dictionaries| replace:: :func:`~hypothesis.strategies.fixed_dictionaries`
.. |st.datetimes| replace:: :func:`~hypothesis.strategies.datetimes`
.. |st.builds| replace:: :func:`~hypothesis.strategies.builds`
.. |st.recursive| replace:: :func:`~hypothesis.strategies.recursive`
.. |st.deferred| replace:: :func:`~hypothesis.strategies.deferred`
.. |st.from_type| replace:: :func:`~hypothesis.strategies.from_type`
.. |st.sampled_from| replace:: :func:`~hypothesis.strategies.sampled_from`
.. |st.uuids| replace:: :func:`~hypothesis.strategies.uuids`
.. |st.ip_addresses| replace:: :func:`~hypothesis.strategies.ip_addresses`
.. |st.register_type_strategy| replace:: :func:`~hypothesis.strategies.register_type_strategy`
.. |st.just| replace:: :func:`~hypothesis.strategies.just`
.. |st.domains| replace:: :func:`~hypothesis.provisional.domains`
.. |st.urls| replace:: :func:`~hypothesis.provisional.urls`

.. |django.from_form| replace:: :func:`~hypothesis.extra.django.from_form`
.. |django.from_model| replace:: :func:`~hypothesis.extra.django.from_model`
.. |django.from_field| replace:: :func:`~hypothesis.extra.django.from_field`

.. |settings.register_profile| replace:: :func:`~hypothesis.settings.register_profile`
.. |settings.get_profile| replace:: :func:`~hypothesis.settings.get_profile`
.. |settings.load_profile| replace:: :func:`~hypothesis.settings.load_profile`

.. |SearchStrategy| replace:: :class:`~hypothesis.strategies.SearchStrategy`
.. |.filter| replace:: :func:`.filter() <hypothesis.strategies.SearchStrategy.filter>`
.. |.filter()| replace:: :func:`.filter() <hypothesis.strategies.SearchStrategy.filter>`
.. |.flatmap| replace:: :func:`.flatmap() <hypothesis.strategies.SearchStrategy.flatmap>`
.. |.flatmap()| replace:: :func:`.flatmap() <hypothesis.strategies.SearchStrategy.flatmap>`
.. |.map| replace:: :func:`.map() <hypothesis.strategies.SearchStrategy.map>`
.. |.map()| replace:: :func:`.map() <hypothesis.strategies.SearchStrategy.map>`
.. |.example()| replace:: :func:`.example() <hypothesis.strategies.SearchStrategy.example>`

.. |@rule| replace:: :func:`@rule <hypothesis.stateful.rule>`

.. |@reproduce_failure| replace:: :func:`@reproduce_failure <hypothesis.reproduce_failure>`

.. |ExampleDatabase| replace:: :class:`~hypothesis.database.ExampleDatabase`
.. |ExampleDatabase.save| replace:: :func:`~hypothesis.database.ExampleDatabase.save`
.. |ExampleDatabase.delete| replace:: :func:`~hypothesis.database.ExampleDatabase.delete`
.. |ExampleDatabase.fetch| replace:: :func:`~hypothesis.database.ExampleDatabase.fetch`
.. |ExampleDatabase.move| replace:: :func:`~hypothesis.database.ExampleDatabase.move`
.. |ExampleDatabase.add_listener| replace:: :func:`~hypothesis.database.ExampleDatabase.add_listener`
.. |ExampleDatabase.remove_listener| replace:: :func:`~hypothesis.database.ExampleDatabase.remove_listener`
.. |ExampleDatabase.clear_listeners| replace:: :func:`~hypothesis.database.ExampleDatabase.clear_listeners`
.. |ExampleDatabase._start_listening| replace:: :func:`~hypothesis.database.ExampleDatabase._start_listening`
.. |ExampleDatabase._stop_listening| replace:: :func:`~hypothesis.database.ExampleDatabase._stop_listening`
.. |ExampleDatabase._broadcast_change| replace:: :func:`~hypothesis.database.ExampleDatabase._broadcast_change`

.. |DirectoryBasedExampleDatabase| replace:: :class:`~hypothesis.database.DirectoryBasedExampleDatabase`
.. |InMemoryExampleDatabase| replace:: :class:`~hypothesis.database.InMemoryExampleDatabase`
.. |ReadOnlyDatabase| replace:: :class:`~hypothesis.database.ReadOnlyDatabase`
.. |MultiplexedDatabase| replace:: :class:`~hypothesis.database.MultiplexedDatabase`
.. |GitHubArtifactDatabase| replace:: :class:`~hypothesis.database.GitHubArtifactDatabase`
.. |BackgroundWriteDatabase| replace:: :class:`~hypothesis.database.BackgroundWriteDatabase`
.. |RedisExampleDatabase| replace:: :class:`~hypothesis.extra.redis.RedisExampleDatabase`

.. |is_hypothesis_test| replace:: :func:`~hypothesis.is_hypothesis_test`

.. |str| replace:: :obj:`python:str`
.. |int| replace:: :obj:`python:int`
.. |bool| replace:: :obj:`python:bool`
.. |bytes| replace:: :obj:`python:bytes`
.. |float| replace:: :obj:`python:float`
.. |assert| replace:: :keyword:`python:assert`
.. |dataclasses| replace:: :mod:`python:dataclasses`
"""

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

html_theme = "furo"
# remove "Hypothesis <version> documentation" from just below logo on the sidebar
html_theme_options = {"sidebar_hide_name": True}
html_static_path = ["_static"]
html_css_files = ["better-signatures.css", "wrap-in-tables.css", "no-scroll.css"]
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
