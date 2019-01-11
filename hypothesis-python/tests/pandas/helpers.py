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

import numpy as np

PANDAS_TIME_DTYPES = tuple(map(np.dtype, ["<M8[ns]", "<m8[ns]", ">M8[ns]", ">m8[ns]"]))


def supported_by_pandas(dtype):
    """Checks whether the dtype is one that can be correctly handled by
    Pandas."""
    # Pandas does not support non-native byte orders and things go amusingly
    # wrong in weird places if you try to use them. See
    # https://pandas.pydata.org/pandas-docs/stable/gotchas.html#byte-ordering-issues
    if dtype.byteorder not in ("|", "="):
        return False

    # Pandas only supports a limited range of timedelta and datetime dtypes
    # compared to the full range that numpy supports and will convert
    # everything to those types (possibly increasing precision in the course of
    # doing so, which can cause problems if this results in something which
    # does not fit into the desired word type. As a result we want to filter
    # out any timedelta or datetime dtypes that are not of the desired types.
    if dtype.kind in ("m", "M"):
        return dtype in PANDAS_TIME_DTYPES
    return True
