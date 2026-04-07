# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""A stable file for which we can write patches.  Don't move stuff around!"""

from pathlib import Path

import numpy as np

from hypothesis import example, given, strategies as st
from hypothesis.extra import numpy as npst

WHERE = Path(__file__).relative_to(Path.cwd())


@given(st.integers())
def fn(x):
    """A trivial test function."""


class Cases:
    @example(n=0, label="whatever")
    @given(st.integers(), st.text())
    def mth(self, n, label):
        """Indented method with existing example decorator."""


@given(st.integers())
@example(x=2).via("not a literal when repeated " * 2)
@example(x=1).via("covering example")
def covered(x):
    """A test function with a removable explicit example."""


@given(npst.arrays(np.int8, 1))
def undef_name(array):
    assert sum(array) < 100


# TODO: test function for insertion-order logic, once I get that set up.
