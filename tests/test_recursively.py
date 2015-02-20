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
from hypothesis import Verifier, Unfalsifiable, Unsatisfiable, assume
from tests.common import small_table
from hypothesis.descriptors import Just, OneOf, SampledFrom, just
from tests.common.descriptors import Descriptor, DescriptorWithValue, \
    primitive_types
from hypothesis.searchstrategy import RandomWithSeed, nice_string
from hypothesis.testdecorators import given
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.internal.utils.fixers import actually_equal

# Placate flake8
[OneOf, just, Just, RandomWithSeed, SampledFrom]


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


def is_immutable_data(t):
    return not tree_contains_match(
        t, lambda x: isinstance(x, (list, set, dict)))


def test_basic_tree_matching():
    """Just an integrity check to make sure we're testing the right thing
    here."""

    assert not is_immutable_data([1])
    assert not is_immutable_data(([1],))
    assert not is_immutable_data({'foo': 1})
    assert is_immutable_data((1, 1))
    assert is_immutable_data('foo')


@timeout(5)
@given(Descriptor, verifier=verifier)
def test_cannot_generate_mutable_data_from_an_immutable_strategy(d):
    strategy = small_table.strategy(d)
    assume(strategy.has_immutable_data)
    really_small_verifier = Verifier(
        settings=hs.Settings(max_examples=50, timeout=5)
    )

    with pytest.raises((Unfalsifiable, Unsatisfiable)):
        print(
            nice_string(d),
            really_small_verifier.falsify(is_immutable_data, d))


@timeout(5)
@given(Descriptor, Random, verifier=verifier)
def test_copies_all_its_values_correctly(desc, random):
    strategy = small_table.strategy(desc)
    value = strategy.produce(random, strategy.parameter.draw(random))
    assert actually_equal(value, strategy.copy(value))


@given(Descriptor, verifier=verifier)
def test_can_produce_what_it_produces(desc):
    strategy = small_table.strategy(desc)
    with pytest.raises(Unfalsifiable):
        verifier.falsify(strategy.could_have_produced, desc)


@given(DescriptorWithValue, verifier=verifier)
def test_decomposing_produces_things_that_can_be_produced(dav):
    for d, v in small_table.strategy(dav.descriptor).decompose(dav.value):
        assert small_table.strategy(d).could_have_produced(v)


@given(
    DescriptorWithValue,
    verifier=verifier,
)
def test_can_minimize_descriptor_with_value(dav):
    s = small_table.strategy(DescriptorWithValue)
    list(s.simplify_such_that(dav, lambda x: True))
