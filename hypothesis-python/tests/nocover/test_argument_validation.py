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

import hypothesis.strategies as st
from tests.common.arguments import argument_validation_test, e

BAD_ARGS = []


def adjust(ex, **kwargs):
    f, a, b = ex
    b = dict(b)
    b.update(kwargs)
    BAD_ARGS.append((f, a, b))


for ex in [
    e(st.lists, st.integers()),
    e(st.sets, st.integers()),
    e(st.frozensets, st.integers()),
    e(st.dictionaries, st.integers(), st.integers()),
    e(st.text),
    e(st.binary),
]:
    adjust(ex, min_size=-1)
    adjust(ex, max_size=-1)
    adjust(ex, min_size="no")
    adjust(ex, max_size="no")


BAD_ARGS.extend([e(st.lists, st.nothing(), unique=True, min_size=1)])

test_raise_invalid_argument = argument_validation_test(BAD_ARGS)
