# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis import given, strategies as st


def test_error_is_in_finally():
    @given(st.data())
    def test(d):
        try:
            d.draw(st.lists(st.integers(), min_size=3, unique=True))
        finally:
            raise ValueError()

    with pytest.raises(ValueError) as err:
        test()

    assert "[0, 1, -1]" in "\n".join(err.value.__notes__)
