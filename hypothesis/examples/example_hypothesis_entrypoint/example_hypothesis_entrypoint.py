# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""This example demonstrates a setuptools entry point.

See https://hypothesis.readthedocs.io/en/latest/strategies.html#registering-strategies-via-setuptools-entry-points
for details and documentation.
"""


class MyCustomType:
    def __init__(self, x: int):
        assert x >= 0, f"got {x}, but only positive numbers are allowed"
        self.x = x


def _hypothesis_setup_hook():
    import hypothesis.strategies as st

    st.register_type_strategy(MyCustomType, st.integers(min_value=0).map(MyCustomType))
