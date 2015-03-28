# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import re
from random import Random

import pytest
import hypothesis.settings as hs
from hypothesis import assume
from tests.common import timeout
from hypothesis.core import given
from hypothesis.types import RandomWithSeed
from hypothesis.errors import Unfalsifiable
from hypothesis.specifiers import Just, OneOf, SampledFrom, just
from hypothesis.utils.show import show
from tests.common.specifiers import Descriptor, DescriptorWithValue, \
    primitive_types
from hypothesis.strategytests import TemplatesFor
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.internal.verifier import Verifier
from hypothesis.searchstrategy.strategies import BuildContext, strategy

# Placate flake8
[OneOf, just, Just, RandomWithSeed, SampledFrom]

NoneType = type(None)


def size(specifier):
    if specifier in primitive_types:
        return 1
    elif isinstance(specifier, dict):
        children = specifier.values()
    elif isinstance(specifier, (Just, SampledFrom)):
        return 1
    else:
        try:
            children = list(specifier)
        except TypeError:
            return 1
    return 1 + sum(map(size, children))


MAX_SIZE = 15
settings = hs.Settings(
    max_examples=100, timeout=4,
    average_list_length=2.0,
    database=None,
)

verifier = Verifier(
    settings=settings,
)


@timeout(5)
@given(Descriptor, Random, verifier=verifier)
def test_can_falsify_false_things(desc, random):
    assume(size(desc) <= MAX_SIZE)
    verifier.random = random
    x = verifier.falsify(lambda x: False, desc)[0]
    assert not list(strategy(desc, settings).full_simplify(x))


@timeout(5)
@given(Descriptor, verifier=verifier)
def test_can_not_falsify_true_things(desc):
    assume(size(desc) <= MAX_SIZE)
    with pytest.raises(Unfalsifiable):
        verifier.falsify(lambda x: True, desc)

UNDESIRABLE_STRINGS = re.compile('at 0x')


@timeout(5)
@given(Descriptor, verifier=verifier)
def test_does_not_use_nasty_type_reprs_in_show(desc):
    strat = strategy(desc)
    s = repr(strat)
    assert not UNDESIRABLE_STRINGS.findall(s)
    assert type(strat).__name__ in s


@timeout(5)
@given(Descriptor, verifier=verifier)
def test_show_evals_as_specifier(desc):
    s = show(desc)
    read_desc = eval(s)
    assert show(read_desc) == s


def tree_contains_match(t, f):
    if f(t):
        return True
    if isinstance(t, (text_type, binary_type)):
        # Workaround for stupid one element string behaviour
        return False
    try:
        t = list(t)
    except TypeError:
        return False
    return any(tree_contains_match(s, f) for s in t)


@timeout(10)
@given(Descriptor, Random, verifier=verifier)
def test_copies_all_its_values_correctly(desc, random):
    strat = strategy(desc, settings)
    value = strat.produce_template(
        BuildContext(random), strat.draw_parameter(random))
    assert show(strat.reify(value)) == show(strat.reify(value))


@given(
    TemplatesFor(DescriptorWithValue),
    verifier=verifier,
)
def test_can_minimize_specifier_with_value(dav):
    s = strategy(DescriptorWithValue, settings)
    last(s.simplify_such_that(dav, lambda x: True))


@given(Descriptor, Random, verifier=verifier)
def test_template_is_hashable(specifier, random):
    strat = strategy(specifier, settings)
    parameter = strat.draw_parameter(random)
    template = strat.produce_template(BuildContext(random), parameter)
    hash(template)


def last(it):
    for i in it:
        pass
    return i


@given(Descriptor, Random, verifier=verifier)
def test_can_perform_all_basic_operations(specifier, random):
    strat = strategy(specifier, settings)
    parameter = strat.draw_parameter(random)
    template = strat.produce_template(BuildContext(random), parameter)
    assert (
        strat.to_basic(template) ==
        strat.to_basic(strat.from_basic(strat.to_basic(template)))
    )
    minimal_template = last(strat.simplify_such_that(
        template,
        lambda x: True
    ))
    strat.reify(minimal_template)
    assert (
        strat.to_basic(minimal_template) ==
        strat.to_basic(strat.from_basic(strat.to_basic(minimal_template)))
    )


@given(DescriptorWithValue, verifier=verifier)
def test_integrity_check_dav(dav):
    strat = strategy(dav.specifier, settings)
    assert show(dav.value) == show(strat.reify(dav.template))
