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

import operator

import numpy as np

import hypothesis.strategies as st
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.internal.compat import hrange, reduce, text_type, \
    binary_type


def from_dtype(dtype):
    if dtype.kind == u'b':
        result = st.booleans()
    elif dtype.kind == u'f':
        result = st.floats()
    elif dtype.kind == u'c':
        result = st.complex_numbers()
    elif dtype.kind in (u'S', u'a', u'V'):
        result = st.binary()
    elif dtype.kind == u'u':
        result = st.integers(
            min_value=0, max_value=1 << (4 * dtype.itemsize) - 1)
    elif dtype.kind == u'i':
        min_integer = -1 << (4 * dtype.itemsize - 1)
        result = st.integers(min_value=min_integer, max_value=-min_integer - 1)
    elif dtype.kind == u'U':
        result = st.text()
    else:
        raise NotImplementedError(
            u'No strategy implementation for %r' % (dtype,)
        )
    return result.map(dtype.type)


class ArrayStrategy(SearchStrategy):

    def __init__(self, element_strategy, shape, dtype):
        self.shape = tuple(shape)
        assert shape
        self.array_size = reduce(operator.mul, shape)
        self.dtype = dtype
        self.element_strategy = element_strategy

    def do_draw(self, data):
        result = np.zeros(dtype=self.dtype, shape=self.array_size)
        for i in hrange(self.array_size):
            result[i] = self.element_strategy.do_draw(data)
        return result.reshape(self.shape)


def is_scalar(spec):
    return spec in (
        int, bool, text_type, binary_type, float, complex
    )


def arrays(dtype, shape, elements=None):
    if not isinstance(dtype, np.dtype):
        dtype = np.dtype(dtype)
    if elements is None:
        elements = from_dtype(dtype)
    if isinstance(shape, int):
        shape = (shape,)
    shape = tuple(shape)
    if not shape:
        if dtype.kind != u'O':
            return elements
    else:
        return ArrayStrategy(
            shape=shape,
            dtype=dtype,
            element_strategy=elements
        )
