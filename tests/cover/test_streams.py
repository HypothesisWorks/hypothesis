# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

from copy import copy, deepcopy
from random import Random
from itertools import islice

import pytest

from hypothesis import find, given, strategy
from hypothesis.errors import InvalidArgument
from hypothesis.strategies import text, lists, floats, booleans, \
    integers, streaming
from hypothesis.utils.show import show
from hypothesis.internal.debug import minimal, some_template
from hypothesis.searchstrategy.streams import Stream, StreamTemplate


@given(lists(booleans()))
def test_stream_give_lists(xs):
    s = Stream(iter(xs))
    assert list(s) == xs
    assert list(s) == xs


@given(lists(booleans()))
def test_can_zip_streams_with_self(xs):
    s = Stream(iter(xs))
    assert list(zip(s, s)) == list(zip(xs, xs))


def loop(x):
    while True:
        yield x


def test_can_stream_infinite():
    s = Stream(loop(False))
    assert list(islice(s, 100)) == [False] * 100


@given(streaming(text()))
def test_fetched_repr_is_in_stream_repr(s):
    assert repr(s) == u'Stream(...)'
    assert show(next(iter(s))) in show(s)


def test_cannot_thunk_past_end_of_list():
    with pytest.raises(IndexError):
        Stream([1])._thunk_to(5)


def test_thunking_evaluates_initial_list():
    x = Stream([1, 2, 3])
    x._thunk_to(1)
    assert len(x.fetched) == 1


def test_thunking_map_evaluates_source():
    x = Stream(loop(False))
    y = x.map(lambda t: True)
    y[100]
    assert y._thunked() == 101
    assert x._thunked() == 101


def test_wrong_index_raises_type_error():
    with pytest.raises(InvalidArgument):
        Stream([])[u'kittens']


def test_can_index_into_unindexed():
    x = Stream(loop(1))
    assert x[100] == 1


def test_can_map():
    x = Stream([1, 2, 3]).map(lambda i: i * 2)
    assert isinstance(x, Stream)
    assert list(x) == [2, 4, 6]


def test_can_replace_value():
    x = Stream(loop(11))
    y = x.with_value(1, 2)
    assert list(x[:3]) == [11] * 3
    assert list(y[:3]) == [11, 2, 11]


def test_can_minimize():
    x = minimal(streaming(integers()), lambda x: x[10] >= 1)
    ts = list(x[:11])
    assert ts == [0] * 10 + [1]


def test_default_stream_is_empty():
    assert list(Stream()) == []


def test_template_equality():
    t = some_template(streaming(booleans()))
    t2 = StreamTemplate(t.seed, t.parameter_seed, Stream(t.stream))

    while True:
        t3 = some_template(streaming(booleans()))
        if t3.seed != t.seed:
            break
    assert t == t2
    assert t != t3
    assert t != 1

    v = t.stream[11]
    t4 = t2.with_value(11, not v)
    assert t4 != t

    t5 = StreamTemplate(t.seed, t.parameter_seed + 1, Stream(t.stream))
    assert t2 != t5

    assert len(set((t, t2, t3, t4, t5))) == 4


def test_streams_copy_as_self():
    x = streaming(booleans()).example()
    assert copy(x) is x
    assert deepcopy(x) is x

    y = x.map(lambda x: not x)
    assert copy(y) is y
    assert deepcopy(y) is y


def test_check_serialization_preserves_changed_marker():
    strat = strategy(
        streaming(floats(min_value=0.0, max_value=2.2250738585072014e-308)))
    template = strat.draw_template(
        Random(0), strat.draw_parameter(Random(0)))
    strat.reify(template)[0]
    simpler = next(strat.full_simplify(
        Random(0), template
    ))

    as_basic = strat.to_basic(simpler)
    assert as_basic == strat.to_basic(strat.from_basic(as_basic))


def test_lists_of_streams():
    x = find(
        lists(streaming(integers()), min_size=10),
        lambda x: all(t[3] for t in x))
    assert [list(t[:4]) for t in x] == [[0] * 3 + [1]] * 10


def test_streams_with_distinct_values():
    x = find(streaming(integers()), lambda x: len(set(x[:10])) >= 10)
    elts = sorted(set(x[:10]))
    assert len(elts) == 10
    assert elts == list(range(min(elts), max(elts) + 1))


def test_decreasing_streams():
    n = 10
    x = find(
        streaming(integers()), lambda x: all(
            x[i] >= n - i for i in range(n + 1)))
    assert list(x[:(n + 1)]) == list(range(n, -1, -1))
