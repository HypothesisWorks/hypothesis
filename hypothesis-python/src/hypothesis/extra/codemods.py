# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

"""
.. _codemods:

--------------------
hypothesis[codemods]
--------------------

This module provides codemods based on the :pypi:`LibCST` library, which can
both detect *and automatically fix* issues with code that uses Hypothesis,
including upgrading from deprecated features to our recommended style.

You can run the codemods via our CLI::

    $ hypothesis codemod --help
    Usage: hypothesis codemod [OPTIONS] PATH...

      `hypothesis codemod` refactors deprecated or inefficent code.

      It adapts `python -m libcst.tool`, removing many features and config
      options which are rarely relevant for this purpose.  If you need more
      control, we encourage you to use the libcst CLI directly; if not this one
      is easier.

      PATH is the file(s) or directories of files to format in place, or "-" to
      read from stdin and write to stdout.

    Options:
      -h, --help  Show this message and exit.

Alternatively you can use ``python -m libcst.tool``, which offers more control
at the cost of additional configuration (adding ``'hypothesis.extra'`` to the
``modules`` list in ``.libcst.codemod.yaml``) and `some issues on Windows
<https://github.com/Instagram/LibCST/issues/435>`__.

.. autofunction:: refactor
"""

from typing import List

import libcst as cst
import libcst.matchers as m
from libcst.codemod import VisitorBasedCodemodCommand


def refactor(code: str) -> str:
    """Update a source code string from deprecated to modern Hypothesis APIs.

    This may not fix *all* the deprecation warnings in your code, but we're
    confident that it will be easier than doing it all by hand.

    We recommend using the CLI, but if you want a Python function here it is.
    """
    context = cst.codemod.CodemodContext()
    mod = cst.parse_module(code)
    transforms: List[VisitorBasedCodemodCommand] = [
        HypothesisFixPositionalKeywonlyArgs(context),
        HypothesisFixComplexMinMagnitude(context),
    ]
    for transform in transforms:
        mod = transform.transform_module(mod)
    return mod.code


def match_qualname(name):
    # We use the metadata to get qualname instead of matching directly on function
    # name, because this handles some scope and "from x import y as z" issues.
    return m.MatchMetadataIfTrue(
        cst.metadata.QualifiedNameProvider,
        # If there are multiple possible qualnames, e.g. due to conditional imports,
        # be conservative.  Better to leave the user to fix a few things by hand than
        # to break their code while attempting to refactor it!
        lambda qualnames: all(n.name == name for n in qualnames),
    )


class HypothesisFixComplexMinMagnitude(VisitorBasedCodemodCommand):
    """Fix a deprecated min_magnitude=None argument for complex numbers::

        st.complex_numbers(min_magnitude=None) -> st.complex_numbers(min_magnitude=0)

    Note that this should be run *after* ``HypothesisFixPositionalKeywonlyArgs``,
    in order to handle ``st.complex_numbers(None)``.
    """

    DESCRIPTION = "Fix a deprecated min_magnitude=None argument for complex numbers."
    METADATA_DEPENDENCIES = (cst.metadata.QualifiedNameProvider,)

    @m.call_if_inside(
        m.Call(metadata=match_qualname("hypothesis.strategies.complex_numbers"))
    )
    def leave_Arg(self, original_node, updated_node):
        if m.matches(
            updated_node, m.Arg(keyword=m.Name("min_magnitude"), value=m.Name("None"))
        ):
            return updated_node.with_changes(value=cst.Integer("0"))
        return updated_node
