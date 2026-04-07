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

from hypothesis import Phase, example, given, settings, strategies as st

OUTPUT_WITH_BREAK = """
Falsifying explicit example: test(
    x={0!r},
    y={0!r},
)
"""


@pytest.mark.parametrize("n", [10, 100])
def test_inserts_line_breaks_only_at_appropriate_lengths(n):
    @example("0" * n, "0" * n)
    @given(st.text(), st.text())
    def test(x, y):
        assert x < y

    with pytest.raises(AssertionError) as err:
        test()

    assert OUTPUT_WITH_BREAK.format("0" * n).strip() == "\n".join(err.value.__notes__)


@given(kw=st.none())
def generate_phase(*args, kw):
    assert args != (1, 2, 3)


@given(kw=st.none())
@example(kw=None)
@settings(phases=[Phase.explicit])
def explicit_phase(*args, kw):
    assert args != (1, 2, 3)


@pytest.mark.parametrize(
    "fn",
    [generate_phase, explicit_phase],
    ids=lambda fn: fn.__name__,
)
def test_vararg_output(fn):
    with pytest.raises(AssertionError) as err:
        fn(1, 2, 3)

    assert "1,\n    2,\n    3,\n" in "\n".join(err.value.__notes__)
