# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from random import Random

from hypothesis import Phase, find, settings, strategies as st


def test_find_uses_provided_random():
    prev = None

    for _ in range(3):
        seen = None

        def test(v):
            if len(v) > 5:
                nonlocal seen
                if seen is not None:
                    return v == seen
                else:
                    seen = v
                    return True

        result = find(
            st.text(),
            test,
            random=Random(13),
            settings=settings(phases=[Phase.generate], max_examples=1000),
        )
        if prev is None:
            prev = result
        else:
            assert prev == result
