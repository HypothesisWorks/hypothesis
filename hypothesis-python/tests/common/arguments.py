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

from hypothesis import given
from hypothesis.errors import InvalidArgument


def e(a, *args, **kwargs):
    return (a, args, kwargs)


def e_to_str(elt):
    f, args, kwargs = elt
    bits = list(map(repr, args))
    bits.extend(sorted("%s=%r" % (k, v) for k, v in kwargs.items()))
    return "%s(%s)" % (f.__name__, ", ".join(bits))


def argument_validation_test(bad_args):
    @pytest.mark.parametrize(
        ("function", "args", "kwargs"), bad_args, ids=list(map(e_to_str, bad_args))
    )
    def test_raise_invalid_argument(function, args, kwargs):
        @given(function(*args, **kwargs))
        def test(x):
            pass

        with pytest.raises(InvalidArgument):
            test()

    return test_raise_invalid_argument
