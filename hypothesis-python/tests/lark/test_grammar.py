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

from __future__ import absolute_import, division, print_function

import json

import pytest
from lark.lark import Lark

from hypothesis import given
from hypothesis.errors import InvalidArgument
from hypothesis.extra.lark import from_lark
from hypothesis.internal.compat import integer_types, text_type
from hypothesis.strategies import data, just
from tests.common.debug import find_any

# Adapted from the official Lark tutorial, with modifications to ensure
# that the generated JSON is valid.  i.e. no numbers starting with ".",
# \f is not ignorable whitespace, and restricted strings only.  Source:
# https://github.com/lark-parser/lark/blob/master/docs/json_tutorial.md
EBNF_GRAMMAR = r"""
    value: dict
         | list
         | STRING
         | NUMBER
         | "true"  -> true
         | "false" -> false
         | "null"  -> null
    list : "[" [value ("," value)*] "]"
    dict : "{" [STRING ":" value ("," STRING ":" value)*] "}"

    STRING : /"[a-z]*"/
    NUMBER : /-?[1-9][0-9]*(\.[0-9]+)?([eE][+-]?[0-9]+)?/

    WS : /[ \t\r\n]+/
    %ignore WS
"""

LIST_GRAMMAR = r"""
list : "[" [NUMBER ("," NUMBER)*] "]"
NUMBER: /[0-9]+/
"""


@given(from_lark(Lark(EBNF_GRAMMAR, start="value")))
def test_generates_valid_json(string):
    json.loads(string)


@pytest.mark.parametrize(
    "start, type_",
    [
        ("dict", dict),
        ("list", list),
        ("STRING", text_type),
        ("NUMBER", integer_types + (float,)),
        ("TRUE", bool),
        ("FALSE", bool),
        ("NULL", type(None)),
    ],
)
@given(data=data())
def test_can_specify_start_rule(data, start, type_):
    string = data.draw(from_lark(Lark(EBNF_GRAMMAR, start="value"), start=start))
    value = json.loads(string)
    assert isinstance(value, type_)


def test_can_generate_ignored_tokens():
    list_grammar = r"""
    list : "[" [STRING ("," STRING)*] "]"
    STRING : /"[a-z]*"/
    WS : /[ \t\r\n]+/
    %ignore WS
    """
    strategy = from_lark(Lark(list_grammar, start="list"))
    # A JSON list of strings in canoncial form which does not round-trip,
    # must contain ignorable whitespace in the initial string.
    find_any(strategy, lambda s: "\t" in s)


def test_generation_without_whitespace():
    find_any(from_lark(Lark(LIST_GRAMMAR, start="list")), lambda g: " " not in g)


def test_cannot_convert_EBNF_to_strategy_directly():
    with pytest.raises(InvalidArgument):
        # Not a Lark object
        from_lark(EBNF_GRAMMAR).example()
    with pytest.raises(TypeError):
        # Not even the right number of arguments
        from_lark(EBNF_GRAMMAR, start="value").example()
    with pytest.raises(InvalidArgument):
        # Wrong type for explicit_strategies
        from_lark(Lark(LIST_GRAMMAR, start="list"), explicit=[]).example()


def test_undefined_terminals_require_explicit_strategies():
    elem_grammar = r"""
    list : "[" [ELEMENT ("," ELEMENT)*] "]"
    %declare ELEMENT
    """
    with pytest.raises(InvalidArgument):
        from_lark(Lark(elem_grammar, start="list")).example()
    strategy = {"ELEMENT": just("200")}
    from_lark(Lark(elem_grammar, start="list"), explicit=strategy).example()


def test_cannot_use_explicit_strategies_for_unknown_terminals():
    with pytest.raises(InvalidArgument):
        from_lark(
            Lark(LIST_GRAMMAR, start="list"), explicit={"unused_name": just("")}
        ).example()


def test_non_string_explicit_strategies_are_invalid():
    with pytest.raises(InvalidArgument):
        from_lark(
            Lark(LIST_GRAMMAR, start="list"), explicit={"NUMBER": just(0)}
        ).example()


@given(
    string=from_lark(Lark(LIST_GRAMMAR, start="list"), explicit={"NUMBER": just("0")})
)
def test_can_override_defined_terminal(string):
    assert sum(json.loads(string)) == 0
