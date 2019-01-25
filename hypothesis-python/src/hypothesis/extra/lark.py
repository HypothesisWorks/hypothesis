# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
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
----------------
hypothesis[lark]
----------------

This extra can be used to generate strings matching any context-free grammar,
using the `Lark parser library <https://github.com/lark-parser/lark>`_.

It currently only supports Lark's native EBNF syntax, but we plan to extend
this to support other common syntaxes such as ANTLR and :rfc:`5234` ABNF.
Lark already `supports loading grammars
<https://github.com/lark-parser/lark#how-to-use-nearley-grammars-in-lark>`_
from `nearley.js <https://nearley.js.org/>`_, so you may not have to write
your own at all.
"""

from __future__ import absolute_import, division, print_function

import lark

import hypothesis._strategies as st
from hypothesis.internal.validation import check_type

if False:
    from typing import Text  # noqa

__all__ = ["from_lark"]


@st.cacheable
@st.defines_strategy_with_reusable_values
def from_lark(grammar, start=None):
    # type: (lark.lark.Lark, Text) -> st.SearchStrategy[Text]
    """A strategy for strings accepted by the given context-free grammar.

    ``grammar`` must be a ``Lark`` object, which wraps an EBNF specification.
    The Lark EBNF grammar reference can be found
    `here <https://lark-parser.readthedocs.io/en/latest/grammar/>`_.

    ``from_lark`` will automatically generate strings matching the
    nonterminal ``start`` symbol in the grammar, which was supplied as an
    argument to the Lark class.  To generate strings matching a different
    symbol, including terminals, you can override this by passing the
    ``start`` argument to ``from_lark``.
    """
    check_type(lark.lark.Lark, grammar, "grammar")
    if start is None:
        start = grammar.options.start

    # Compiling the EBNF grammar to a sanitised and canonicalised BNF
    # format makes further transformations much easier.
    terminals, rules, ignore_names = grammar.grammar.compile()

    # Map all terminals to the corresponging regular expression, and
    # thence to a strategy for producing matching strings.
    # We'll add strategies for non-terminals to this mapping later.
    strategies = {
        t.name: st.from_regex(t.pattern.to_regexp(), fullmatch=True) for t in terminals
    }
    if start in strategies:
        return strategies[start]

    # Reshape our flat list of rules into a dict of rulename to list of
    # possible productions for that rule.  We sort productions by increasing
    # number of parts as a heuristic for shrinking order.
    nonterminals = {
        origin.name: sorted(
            [rule.expansion for rule in rules if rule.origin == origin], key=len
        )
        for origin in set(rule.origin for rule in rules)
    }

    @st.cacheable
    @st.defines_strategy_with_reusable_values
    def convert(expansion):
        parts = []
        for p in expansion:
            if parts and ignore_names:
                # Chance to insert ignored substrings between meaningful
                # tokens, e.g. whitespace between values in JSON.
                parts.append(
                    st.just(u"")
                    | st.one_of([strategies[name] for name in ignore_names])
                )
            if p.name in strategies:
                # This might be a Terminal, or it might be a NonTerminal
                # that we've previously handled.
                parts.append(strategies[p.name])
            else:
                # It must be the first time we've encountered this NonTerminal.
                # Recurse to handle it, relying on lazy strategy instantiation
                # to allow forward references, then add it to the strategies
                # cache to avoid infinite loops.
                assert isinstance(p, lark.grammar.NonTerminal)
                s = st.one_of([convert(ex) for ex in nonterminals[p.name]])
                parts.append(s)
                strategies[p.name] = s
        # Special-case rules with only one expansion; it's worthwhile being
        # efficient when this includes terminals!  Otherwise, join the parts.
        if len(parts) == 1:
            return parts[0]
        return st.tuples(*parts).map(u"".join)

    # Most grammars describe several production rules, so we check the start
    # option passed to Lark to see which nonterminal we're going to produce.
    return st.one_of([convert(ex) for ex in nonterminals[start]])
