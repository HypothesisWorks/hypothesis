# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest
import hypothesis.strategies as ds
from hypothesis.errors import InvalidArgument


def fn_test(*fnkwargs):
    fnkwargs = list(fnkwargs)
    return pytest.mark.parametrize(
        ('fn', 'args'), fnkwargs,
        ids=[
            '%s(%s)' % (fn.__name__, ', '.join(map(repr, args)))
            for fn, args in fnkwargs
        ]
    )


def fn_ktest(*fnkwargs):
    fnkwargs = list(fnkwargs)
    return pytest.mark.parametrize(
        ('fn', 'kwargs'), fnkwargs,
        ids=[
            '%s(%s)' % (fn.__name__, ', '.join(
                '%s=%r' % (k, v)
                for k, v in kwargs.items()
            ),)
            for fn, kwargs in fnkwargs
        ]
    )


@fn_ktest(
    (ds.integers, {'min_value': float('nan')}),
    (ds.integers, {'min_value': 2, 'max_value': 1}),
    (ds.sampled_from, {'elements': ()}),
    (ds.lists, {}),
    (ds.lists, {'average_size': float('nan')}),
    (ds.lists, {'min_size': 10, 'max_size': 9}),
    (ds.lists, {'min_size': -10, 'max_size': -9}),
    (ds.lists, {'max_size': -9}),
    (ds.lists, {'max_size': 10}),
    (ds.lists, {'min_size': -10}),
    (ds.lists, {'max_size': 10, 'average_size': 20}),
    (ds.lists, {'min_size': 1.0, 'average_size': 0.5}),
    (ds.lists, {'elements': 'hi'}),
    (ds.text, {'min_size': 10, 'max_size': 9}),
    (ds.text, {'max_size': 10, 'average_size': 20}),
    (ds.binary, {'min_size': 10, 'max_size': 9}),
    (ds.binary, {'max_size': 10, 'average_size': 20}),
    (ds.floats, {'min_value': float('nan')}),
    (ds.floats, {'max_value': 0.0, 'min_value': 1.0}),
    (ds.dictionaries, {'fixed': 'fish'}),
    (ds.dictionaries, {'variable': (ds.integers(),)}),
    (ds.dictionaries, {'variable': (ds.integers(), 1)}),
    (ds.dictionaries, {'variable': 1}),
)
def test_validates_keyword_arguments(fn, kwargs):
    with pytest.raises(InvalidArgument):
        fn(**kwargs)


@fn_ktest(
    (ds.integers, {'min_value': 0}),
    (ds.integers, {'min_value': 11}),
    (ds.integers, {'min_value': 11, 'max_value': 100}),
    (ds.integers, {'max_value': 0}),
    (ds.lists, {'max_size': 0}),
    (ds.lists, {'elements': ds.integers()}),
    (ds.lists, {'elements': ds.integers(), 'max_size': 5}),
    (ds.lists, {'elements': ds.booleans(), 'min_size': 5}),
    (ds.lists, {'elements': ds.booleans(), 'min_size': 5, 'max_size': 10}),
    (ds.booleans, {}),
    (ds.just, {'value': 'hi'}),
    (ds.integers, {'min_value': 12, 'max_value': 12}),
    (ds.floats, {}),
    (ds.floats, {'min_value': 1.0}),
    (ds.floats, {'max_value': 1.0}),
    (ds.floats, {'max_value': 1.0, 'min_value': -1.0}),
    (ds.sampled_from, {'elements': [1]}),
    (ds.sampled_from, {'elements': [1, 2, 3]}),
    (ds.dictionaries, {'fixed': {1: ds.integers()}}),
    (ds.dictionaries, {'variable': (ds.booleans(), ds.integers())}),
    (ds.dictionaries, {
        'fixed': {3: ds.text()},
        'variable': (ds.booleans(), ds.integers())}),
    (ds.dictionaries, {'variable': ds.lists(ds.tuples(
        ds.booleans(), ds.integers()))}),
    (ds.text, {'alphabet': 'abc'}),
    (ds.text, {'alphabet': ds.sampled_from('abc')}),
)
def test_produces_valid_examples_from_keyword(fn, kwargs):
    fn(**kwargs).example()


@fn_test(
    (ds.one_of, (1,))
)
def test_validates_args(fn, args):
    with pytest.raises(InvalidArgument):
        fn(*args)


@fn_test(
    (ds.one_of, (ds.booleans(), ds.tuples(ds.booleans()))),
    (ds.one_of, (ds.booleans(),)),
    (ds.dictionaries, (ds.dictionaries(),)),
    (ds.text, ()),
    (ds.binary, ()),
)
def test_produces_valid_examples_from_args(fn, args):
    fn(*args).example()


def test_tuples_raise_error_on_bad_kwargs():
    with pytest.raises(TypeError):
        ds.tuples(stuff='things')


def test_streaming_streams():
    for v in ds.streaming(ds.integers(max_value=1000)).example()[:10]:
        assert v <= 1000
