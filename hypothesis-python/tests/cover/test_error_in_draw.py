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
from tests.common.utils import capture_out


def test_error_is_in_finally():
    @given(st.data())
    def test(d):
        try:
            d.draw(st.lists(st.integers(), min_size=3, unique=True))
        finally:
            raise ValueError()

    with capture_out() as o:
        with pytest.raises(ValueError):
            test()

    assert "[0, 1, -1]" in o.getvalue()
