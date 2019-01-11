# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

import hypothesis.extra.pandas as pdst
import hypothesis.strategies as st
from tests.common.arguments import argument_validation_test, e

BAD_ARGS = [
    e(pdst.data_frames),
    e(pdst.data_frames, pdst.columns(1, dtype="not a dtype")),
    e(pdst.data_frames, pdst.columns(1, elements="not a strategy")),
    e(pdst.data_frames, pdst.columns([[]])),
    e(pdst.data_frames, [], index=[]),
    e(pdst.data_frames, [], rows=st.fixed_dictionaries({"A": st.just(1)})),
    e(pdst.data_frames, pdst.columns(1)),
    e(pdst.data_frames, pdst.columns(1, dtype=float, fill=1)),
    e(pdst.data_frames, pdst.columns(1, dtype=float, elements=1)),
    e(pdst.data_frames, pdst.columns(1, fill=1, dtype=float)),
    e(pdst.data_frames, pdst.columns(["A", "A"], dtype=float)),
    e(pdst.data_frames, pdst.columns(1, elements=st.none(), dtype=int)),
    e(pdst.data_frames, 1),
    e(pdst.data_frames, [1]),
    e(pdst.data_frames, pdst.columns(1, dtype="category")),
    e(
        pdst.data_frames,
        pdst.columns(["A"], dtype=bool),
        rows=st.tuples(st.booleans(), st.booleans()),
    ),
    e(
        pdst.data_frames,
        pdst.columns(1, elements=st.booleans()),
        rows=st.tuples(st.booleans()),
    ),
    e(pdst.data_frames, rows=st.integers(), index=pdst.range_indexes(0, 0)),
    e(pdst.data_frames, rows=st.integers(), index=pdst.range_indexes(1, 1)),
    e(pdst.data_frames, pdst.columns(1, dtype=int), rows=st.integers()),
    e(pdst.indexes),
    e(pdst.indexes, dtype="category"),
    e(pdst.indexes, dtype="not a dtype"),
    e(pdst.indexes, elements="not a strategy"),
    e(pdst.indexes, elements=st.text(), dtype=float),
    e(pdst.indexes, elements=st.none(), dtype=int),
    e(pdst.indexes, dtype=int, max_size=0, min_size=1),
    e(pdst.indexes, dtype=int, unique="true"),
    e(pdst.indexes, dtype=int, min_size="0"),
    e(pdst.indexes, dtype=int, max_size="1"),
    e(pdst.range_indexes, 1, 0),
    e(pdst.range_indexes, min_size="0"),
    e(pdst.range_indexes, max_size="1"),
    e(pdst.series),
    e(pdst.series, dtype="not a dtype"),
    e(pdst.series, elements="not a strategy"),
    e(pdst.series, elements=st.none(), dtype=int),
    e(pdst.series, dtype="category"),
    e(pdst.series, index="not a strategy"),
]


test_raise_invalid_argument = argument_validation_test(BAD_ARGS)
