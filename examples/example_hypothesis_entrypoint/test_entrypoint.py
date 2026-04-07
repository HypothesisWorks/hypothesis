# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from example_hypothesis_entrypoint import MyCustomType

from hypothesis import given, strategies as st


@given(st.from_type(MyCustomType))
def test_registered_from_entrypoint(x):
    # This demonstrates that we've registered the type, not just
    # worked out how to construct an instance.
    assert isinstance(x, MyCustomType)
    assert x.x >= 0
