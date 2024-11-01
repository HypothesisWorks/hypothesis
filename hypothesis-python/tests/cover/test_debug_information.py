# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import re

import pytest

from hypothesis import Verbosity, given, settings, strategies as st
from hypothesis.database import InMemoryExampleDatabase

from tests.common.utils import capture_out


def test_reports_passes():
    @given(st.integers())
    @settings(
        verbosity=Verbosity.debug, max_examples=1000, database=InMemoryExampleDatabase()
    )
    def test(i):
        assert i < 10

    with capture_out() as out:
        with pytest.raises(AssertionError):
            test()

    value = out.getvalue()

    assert "minimize_individual_nodes" in value
    assert "calls" in value
    assert "shrinks" in value

    shrinks_info = re.compile(r"call(s?) of which ([0-9]+) shrank")

    for l in value.splitlines():
        m = shrinks_info.search(l)
        if m is not None and int(m.group(2)) != 0:
            break
    else:
        pytest.xfail(reason="Sometimes the first failure is 10, and cannot shrink.")
