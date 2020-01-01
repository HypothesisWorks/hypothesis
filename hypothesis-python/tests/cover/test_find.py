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

from random import Random

from hypothesis import Phase, find, settings, strategies as st


def test_find_uses_provided_random():
    prev = None

    for _ in range(3):
        seen = []

        def test(v):
            if len(v) > 5:
                if seen:
                    return v == seen[0]
                else:
                    seen.append(v)
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
