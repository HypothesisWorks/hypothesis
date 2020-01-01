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

from hypothesis.internal.conjecture.shrinking import Integer
from tests.common.utils import capture_out


def test_debug_output():
    with capture_out() as o:
        Integer.shrink(10, lambda x: True, debug=True, random=Random(0))

    assert "initial=10" in o.getvalue()
    assert "shrinking to 0" in o.getvalue()


def test_includes_name_in_repr_if_set():
    assert (
        repr(Integer(10, lambda x: True, name="hi there", random=Random(0)))
        == "Integer('hi there', initial=10, current=10)"
    )


def test_normally_contains_no_space_for_name():
    assert (
        repr(Integer(10, lambda x: True, random=Random(0)))
        == "Integer(initial=10, current=10)"
    )
