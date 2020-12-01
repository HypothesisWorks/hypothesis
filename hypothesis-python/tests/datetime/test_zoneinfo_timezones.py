# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.strategies._internal.datetime import zoneinfo
from tests.common.debug import assert_no_examples, find_any, minimal


def test_utc_is_minimal():
    assert minimal(st.timezones()) is zoneinfo.ZoneInfo("UTC")


def test_can_generate_non_utc():
    find_any(
        st.datetimes(timezones=st.timezones()).filter(lambda d: d.tzinfo.key != "UTC")
    )


@given(st.data(), st.datetimes(), st.datetimes())
def test_datetimes_stay_within_naive_bounds(data, lo, hi):
    if lo > hi:
        lo, hi = hi, lo
    out = data.draw(st.datetimes(lo, hi, timezones=st.timezones()))
    assert lo <= out.replace(tzinfo=None) <= hi


@pytest.mark.parametrize("kwargs", [{"no_cache": 1}])
def test_timezones_argument_validation(kwargs):
    with pytest.raises(InvalidArgument):
        st.timezones(**kwargs).validate()


@pytest.mark.parametrize(
    "kwargs",
    [
        # {"allow_alias": 1},
        # {"allow_deprecated": 1},
        {"allow_prefix": 1},
    ],
)
def test_timezone_keys_argument_validation(kwargs):
    with pytest.raises(InvalidArgument):
        st.timezone_keys(**kwargs).validate()


def test_can_disallow_prefixes():
    assert_no_examples(
        st.timezone_keys(allow_prefix=False),
        lambda s: s.startswith(("posix/", "right/")),
    )
