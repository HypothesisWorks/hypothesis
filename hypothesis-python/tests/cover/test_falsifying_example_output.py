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

from hypothesis import example, given, strategies as st
from tests.common.utils import capture_out

OUTPUT_NO_LINE_BREAK = """
Falsifying explicit example: test(
    x=%(input)s, y=%(input)s,
)
"""


OUTPUT_WITH_LINE_BREAK = """
Falsifying explicit example: test(
    x=%(input)s,
    y=%(input)s,
)
"""


@pytest.mark.parametrize("line_break,input", [(False, "0" * 10), (True, "0" * 100)])
def test_inserts_line_breaks_only_at_appropriate_lengths(line_break, input):
    @example(input, input)
    @given(st.text(), st.text())
    def test(x, y):
        assert x < y

    with capture_out() as cap:
        with pytest.raises(AssertionError):
            test()

    template = OUTPUT_WITH_LINE_BREAK if line_break else OUTPUT_NO_LINE_BREAK

    desired_output = template % {"input": repr(input)}

    actual_output = cap.getvalue()

    assert desired_output.strip() == actual_output.strip()


def test_vararg_output():
    @given(foo=st.text())
    def test(*args, foo):
        assert False

    with capture_out() as cap:
        with pytest.raises(AssertionError):
            test(1, 2, 3)

    assert "1, 2, 3" in cap.getvalue()
