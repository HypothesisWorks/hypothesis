# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

from itertools import islice

import pytest

from hypothesis import find, given
from hypothesis.errors import InvalidArgument
from hypothesis.strategies import text, lists, booleans, streaming
from hypothesis.searchstrategy.streams import Stream


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
    assert repr(next(iter(s))) in repr(s)


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


def test_streaming_errors_in_find():
    with pytest.raises(InvalidArgument):
        find(streaming(booleans()), lambda x: True)


def test_default_stream_is_empty():
    assert list(Stream()) == []


def test_can_slice_streams():
    assert list(Stream([1, 2, 3])[:2]) == [1, 2]
