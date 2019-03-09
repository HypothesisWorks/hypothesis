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

Note that as Lark is at version 0.x, this module *may* break API compatibility
in minor releases if supporting the latest version of Lark would otherwise be
infeasible.  We may also be quite aggressive in bumping the minimum version of
Lark, unless someone volunteers to either fund or do the maintainence.
"""

from __future__ import absolute_import, division, print_function

import attr
import lark
from lark.grammar import NonTerminal, Terminal

import hypothesis._strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.internal.conjecture.utils import calc_label_from_name
from hypothesis.internal.validation import check_type
from hypothesis.searchstrategy import SearchStrategy

if False:
    from typing import Text  # noqa

__all__ = ["from_lark"]


@attr.s()
class DrawState(object):
    """Tracks state of a single draw from a lark grammar.

    Currently just wraps a list of tokens that will be emitted at the
    end, but as we support more sophisticated parsers this will need
    to track more state for e.g. indentation level.
    """

    # The text output so far as a list of string tokens resulting from
    # each draw to a non-terminal.
    result = attr.ib(default=attr.Factory(list))


class LarkStrategy(SearchStrategy):
    """Low-level strategy implementation wrapping a Lark grammar.

    See ``from_lark`` for details.
    """

    def __init__(self, grammar, start=None):
        check_type(lark.lark.Lark, grammar, "grammar")
        if start is None:
            start = grammar.options.start
        self.grammar = grammar

        terminals, rules, ignore_names = grammar.grammar.compile()

        self.names_to_symbols = {}

        for r in rules:
            t = r.origin
            self.names_to_symbols[t.name] = t

        for t in terminals:
            self.names_to_symbols[t.name] = Terminal(t.name)

        self.start = self.names_to_symbols[start]

        self.ignored_symbols = (
            st.sampled_from([self.names_to_symbols[n] for n in ignore_names])
            if ignore_names
            else st.nothing()
        )

        self.terminal_strategies = {
            t.name: st.from_regex(t.pattern.to_regexp(), fullmatch=True)
            for t in terminals
        }

        nonterminals = {}

        for rule in rules:
            nonterminals.setdefault(rule.origin.name, []).append(tuple(rule.expansion))

        for v in nonterminals.values():
            v.sort(key=len)

        self.nonterminal_strategies = {
            k: st.sampled_from(v) for k, v in nonterminals.items()
        }

        self.__rule_labels = {}

    def do_draw(self, data):
        state = DrawState()
        self.draw_symbol(data, self.start, state)
        return u"".join(state.result)

    def rule_label(self, name):
        try:
            return self.__rule_labels[name]
        except KeyError:
            return self.__rule_labels.setdefault(
                name, calc_label_from_name("LARK:%s" % (name,))
            )

    def draw_symbol(self, data, symbol, draw_state):
        if isinstance(symbol, Terminal):
            try:
                strategy = self.terminal_strategies[symbol.name]
            except KeyError:
                raise InvalidArgument(
                    "Undefined terminal %r. Generation does not currently support use of %%declare."
                    % (symbol.name,)
                )
            draw_state.result.append(data.draw(strategy))
        else:
            assert isinstance(symbol, NonTerminal)
            data.start_example(self.rule_label(symbol.name))
            expansion = data.draw(self.nonterminal_strategies[symbol.name])
            for e in expansion:
                self.draw_symbol(data, e, draw_state)
                self.gen_ignore(data, draw_state)
            data.stop_example()

    def gen_ignore(self, data, draw_state):
        if self.ignored_symbols.is_empty:
            return
        if data.draw_bits(2) == 3:
            emit = data.draw(self.ignored_symbols)
            self.draw_symbol(data, emit, draw_state)

    def calc_has_reusable_values(self, recur):
        return True


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

    Currently ``from_lark`` does not support grammars that need custom lexing.
    Any lexers will be ignored, and any undefined terminals from the use of
    ``%declare`` will result in generation errors. We hope to support more of
    these features in future.
    """

    return LarkStrategy(grammar, start)
