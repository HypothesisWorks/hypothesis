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
import time
import signal
from random import Random
from functools import wraps

import pytest
import hypothesis.settings as hs
from hypothesis import Verifier, Unfalsifiable, assume
from tests.common import small_table
from hypothesis.descriptors import Just, OneOf, SampledFrom, just
from hypothesis.strategytable import StrategyTable
from tests.common.descriptors import Descriptor, DescriptorWithValue, \
    primitive_types
from hypothesis.searchstrategy import RandomWithSeed, nice_string
from hypothesis.testdecorators import given
from hypothesis.descriptortests import TemplatesFor
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.internal.utils.fixers import actually_equal

# Placate flake8
[OneOf, just, Just, RandomWithSeed, SampledFrom]

NoneType = type(None)


class Timeout(BaseException):
    pass


try:
    signal.SIGALRM
    # The tests here have a tendency to run away with themselves a it if
    # something goes wrong, so we use a relatively hard kill timeout.

    def timeout(seconds=1):
        def decorate(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                start = time.time()

                def handler(signum, frame):
                    raise Timeout(
                        'Timed out after %.2fs' % (time.time() - start))

                old_handler = signal.signal(signal.SIGALRM, handler)
                signal.alarm(seconds)
                try:
                    return f(*args, **kwargs)
                finally:
                    signal.signal(signal.SIGALRM, old_handler)
                    signal.alarm(0)
            return wrapped
        return decorate
except AttributeError:
    # We're on an OS with no SIGALRM. Fall back to no timeout.
    def timeout(seconds=1):
        def decorate(f):
            return f
        return decorate


def size(descriptor):
    if descriptor in primitive_types:
        return 1
    elif isinstance(descriptor, dict):
        children = descriptor.values()
    elif isinstance(descriptor, (Just, SampledFrom)):
        return 1
    else:
        try:
            children = list(descriptor)
        except TypeError:
            return 1
    return 1 + sum(map(size, children))


MAX_SIZE = 15
settings = hs.Settings(max_examples=100, timeout=4)

verifier = Verifier(
    settings=settings,
    strategy_table=small_table,
)


@timeout(5)
@given(Descriptor, Random, verifier=verifier)
def test_can_falsify_false_things(desc, random):
    assume(size(desc) <= MAX_SIZE)
    verifier.random = random
    x = verifier.falsify(lambda x: False, desc)[0]
    strategy = small_table.strategy(desc)
    assert not list(strategy.simplify(x))


@timeout(5)
@given([Descriptor], Random, verifier=verifier)
def test_can_falsify_false_things_with_many_args(descs, random):
    assume(len(descs) > 0)
    assume(size(descs) <= MAX_SIZE)
    descs = tuple(descs)
    verifier.random = random
    x = verifier.falsify(lambda *args: False, *descs)
    strategy = small_table.strategy(descs)
    assert not list(strategy.simplify(x))


@timeout(5)
@given(Descriptor, verifier=verifier)
def test_can_not_falsify_true_things(desc):
    assume(size(desc) <= MAX_SIZE)
    with pytest.raises(Unfalsifiable):
        verifier.falsify(lambda x: True, desc)

UNDESIRABLE_STRINGS = re.compile('|'.join(
    re.escape(repr(t)) for t in primitive_types
))


@timeout(5)
@given(Descriptor, verifier=verifier)
def test_does_not_use_nasty_type_reprs_in_nice_string(desc):
    s = nice_string(desc)
    assert not UNDESIRABLE_STRINGS.findall(s)


@timeout(5)
@given(Descriptor, verifier=verifier)
def test_nice_string_evals_as_descriptor(desc):
    s = nice_string(desc)
    read_desc = eval(s)
    assert actually_equal(desc, read_desc, fuzzy=True)


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


@timeout(5)
@given(Descriptor, Random, verifier=verifier)
def test_copies_all_its_values_correctly(desc, random):
    strategy = small_table.strategy(desc)
    value = strategy.produce_template(random, strategy.parameter.draw(random))
    assert actually_equal(strategy.reify(value), strategy.reify(value))


@given(
    TemplatesFor(DescriptorWithValue),
    verifier=verifier,
)
def test_can_minimize_descriptor_with_value(dav):
    s = small_table.strategy(DescriptorWithValue)
    list(s.simplify_such_that(dav, lambda x: True))


@given(Descriptor, Random, verifier=verifier)
def test_template_is_hashable(descriptor, random):
    strategy = StrategyTable.default().strategy(descriptor)
    parameter = strategy.parameter.draw(random)
    template = strategy.produce_template(random, parameter)
    hash(template)


@given(Descriptor, Random, verifier=verifier)
def test_can_perform_all_basic_operations(descriptor, random):
    strategy = StrategyTable.default().strategy(descriptor)
    parameter = strategy.parameter.draw(random)
    template = strategy.produce_template(random, parameter)
    assert actually_equal(
        template,
        strategy.from_basic(strategy.to_basic(template))
    )
    minimal_template = list(strategy.simplify_such_that(
        template,
        lambda x: True
    ))[-1]
    strategy.reify(minimal_template)
    assert actually_equal(
        minimal_template,
        strategy.from_basic(strategy.to_basic(minimal_template))
    )


@given(DescriptorWithValue, verifier=verifier)
def test_integrity_check_dav(dav):
    strategy = StrategyTable.default().strategy(dav.descriptor)
    assert actually_equal(dav.value, strategy.reify(dav.template))
