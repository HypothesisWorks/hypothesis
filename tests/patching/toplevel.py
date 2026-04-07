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

import hypothesis
import hypothesis.strategies as st

WHERE_TOP = Path(__file__).relative_to(Path.cwd())


@hypothesis.given(st.integers())
def fn_top(x):
    """A trivial test function."""
