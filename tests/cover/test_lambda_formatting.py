# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2016 David R. MacIver
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

from __future__ import division, print_function, absolute_import

from hypothesis.internal.reflection import get_pretty_function_description


def test_bracket_whitespace_is_striped():
    assert get_pretty_function_description(
        lambda x: (x + 1)
    ) == 'lambda x: (x + 1)'


def test_can_have_unicode_in_lambda_sources():
    t = lambda x: 'é' not in x
    assert get_pretty_function_description(t) == (
        "lambda x: 'é' not in x"
    )


ordered_pair = (
    lambda right: [].map(
        lambda length: ()))


def test_can_get_descriptions_of_nested_lambdas_with_different_names():
    assert get_pretty_function_description(ordered_pair) == \
        'lambda right: [].map(lambda length: ())'


def test_source_of_lambda_is_pretty():
    assert get_pretty_function_description(
        lambda x: True
    ) == 'lambda x: True'


def test_variable_names_are_not_pretty():
    t = lambda x: True
    assert get_pretty_function_description(t) == 'lambda x: True'


def test_does_not_error_on_dynamically_defined_functions():
    x = eval('lambda t: 1')
    get_pretty_function_description(x)


def test_collapses_whitespace_nicely():
    t = (
        lambda x,       y:           1
    )
    assert get_pretty_function_description(t) == 'lambda x, y: 1'


def test_is_not_confused_by_tuples():
    p = (lambda x: x > 1, 2)[0]

    assert get_pretty_function_description(p) == 'lambda x: x > 1'


def test_strips_comments_from_the_end():
    t = lambda x: 1
    assert get_pretty_function_description(t) == 'lambda x: 1'


def test_does_not_strip_hashes_within_a_string():
    t = lambda x: '#'
    assert get_pretty_function_description(t) == "lambda x: '#'"


def test_can_distinguish_between_two_lambdas_with_different_args():
    a, b = (lambda x: 1, lambda y: 2)
    assert get_pretty_function_description(a) == 'lambda x: 1'
    assert get_pretty_function_description(b) == 'lambda y: 2'


def test_does_not_error_if_it_cannot_distinguish_between_two_lambdas():
    a, b = (lambda x: 1, lambda x: 2)
    assert 'lambda x:' in get_pretty_function_description(a)
    assert 'lambda x:' in get_pretty_function_description(b)


def test_lambda_source_break_after_def_with_brackets():
    f = (lambda n:
         'aaa')

    source = get_pretty_function_description(f)
    assert source == "lambda n: 'aaa'"


def test_lambda_source_break_after_def_with_line_continuation():
    f = lambda n:\
        'aaa'

    source = get_pretty_function_description(f)
    assert source == "lambda n: 'aaa'"
