# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from itertools import islice

import pytest
from hypothesis import given, assume
from hypothesis.errors import InvalidArgument
from hypothesis.specifiers import streaming
from hypothesis.utils.show import show
from hypothesis.strategytests import strategy_test_suite
from hypothesis.internal.debug import minimal, via_database, some_template
from hypothesis.internal.compat import text_type, integer_types
from hypothesis.searchstrategy.streams import Stream, StreamTemplate

TestIntStreams = strategy_test_suite(streaming(int))
TestStreamLists = strategy_test_suite(streaming(int))
TestIntStreamStreams = strategy_test_suite(streaming(streaming(int)))


@given([bool])
def test_stream_give_lists(xs):
    s = Stream(iter(xs))
    assert list(s) == xs
    assert list(s) == xs


@given([bool])
def test_can_zip_streams_with_self(xs):
    s = Stream(iter(xs))
    assert list(zip(s, s)) == list(zip(xs, xs))


def loop(x):
    while True:
        yield x


def test_can_stream_infinite():
    s = Stream(loop(False))
    assert list(islice(s, 100)) == [False] * 100


@given(streaming(text_type))
def test_fetched_repr_is_in_stream_repr(s):
    assert repr(s) == 'Stream(...)'
    assert show(next(iter(s))) in show(s)


@given(streaming(int))
def test_streams_are_arbitrarily_long(ss):
    for i in islice(ss, 100):
        assert isinstance(i, integer_types)


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
        Stream([])['kittens']


def test_can_index_into_unindexed():
    x = Stream(loop(1))
    assert x[100] == 1


def test_can_replace_value():
    x = Stream(loop(11))
    y = x.with_value(1, 2)
    assert list(x[:3]) == [11] * 3
    assert list(y[:3]) == [11, 2, 11]


def test_can_minimize():
    x = minimal(streaming(int), lambda x: x[10] >= 1)
    ts = list(x[:11])
    assert ts == [0] * 10 + [1]


def test_default_stream_is_empty():
    assert list(Stream()) == []


def test_can_save_minimized_in_database():
    spec = streaming(bool)
    t = some_template(spec)
    assert isinstance(t.stream[10], bool)
    s = t.with_value(10, not t.stream[10])
    assert s != t
    sd = via_database(spec, s)
    assert s == sd


def test_template_equality():
    t = some_template(streaming(bool))
    t2 = StreamTemplate(t.seed, t.parameter_seed, Stream(t.stream))

    while True:
        t3 = some_template(streaming(bool))
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

    assert len({t, t2, t3, t4, t5}) == 4


@given(streaming(int))
def test_can_adaptively_assume_about_streams(xs):
    for i in islice(xs, 200):
        assume(i >= 0)
