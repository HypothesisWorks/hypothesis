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
from hypothesis.internal.compat import text_type
from hypothesis.strategies import data
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


@given(from_lark(Lark(EBNF_GRAMMAR, start="value")))
def test_generates_valid_json(string):
    json.loads(string)


@pytest.mark.parametrize(
    "start, type_",
    [
        ("dict", dict),
        ("list", list),
        ("STRING", text_type),
        ("NUMBER", (int, float)),
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
    find_any(strategy, lambda s: s != json.dumps(json.loads(s)))


def test_cannot_convert_EBNF_to_strategy_directly():
    with pytest.raises(InvalidArgument):
        # Not a Lark object
        from_lark(EBNF_GRAMMAR).example()
    with pytest.raises(TypeError):
        # Not even the right number of arguments
        from_lark(EBNF_GRAMMAR, start="value").example()
