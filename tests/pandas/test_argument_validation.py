# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

import pytest

import hypothesis.strategies as st
import hypothesis.extra.pandas as pdst
from hypothesis import given
from hypothesis.errors import InvalidArgument


def e(a, *args, **kwargs):
    return (a, args, kwargs)


BAD_ARGS = [
    e(pdst.indexes, dtype="not a dtype"),
    e(pdst.indexes, elements="not a strategy"),
    e(pdst.indexes, elements=st.text(), dtype=float),
    e(pdst.indexes),
    e(pdst.series),
    e(pdst.data_frames),
    e(pdst.data_frames, pdst.columns([[]])),
    e(pdst.data_frames, pdst.columns(['A', 'A'], dtype=float)),
    e(pdst.data_frames, pdst.columns(['A'], dtype=float, fill=1)),
    e(pdst.data_frames, pdst.columns(['A'], dtype=float, elements=1)),
    e(pdst.data_frames, pdst.columns(1, fill=1, dtype=float)),
    e(pdst.data_frames, [], rows=st.fixed_dictionaries({'A': st.just(1)})),
    e(pdst.data_frames, [], index=[]),
    e(pdst.data_frames, 1),
    e(pdst.data_frames, [1]),
    e(pdst.range_indexes, 1, 0),
    e(pdst.indexes, dtype=int, max_size=0, min_size=1),
    e(pdst.indexes, dtype=int, unique="true"),
]


def e_to_str(elt):
    f, args, kwargs = elt
    bits = list(map(repr, args))
    bits.extend(sorted("%s=%r" % (k, v) for k, v in kwargs.items()))
    return "%s(%s)" % (f.__name__, ', '.join(bits))


@pytest.mark.parametrize(
    ('function', 'args', 'kwargs'), BAD_ARGS,
    ids=list(map(e_to_str, BAD_ARGS))
)
def test_raise_invalid_argument(function, args, kwargs):
    @given(function(*args, **kwargs))
    def test(x):
        pass

    with pytest.raises(InvalidArgument):
        test()
