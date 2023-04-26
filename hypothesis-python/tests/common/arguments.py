# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis import given
from hypothesis.errors import InvalidArgument


def e(a, *args, **kwargs):
    return (a, args, kwargs)


def e_to_str(elt):
    f, args, kwargs = getattr(elt, "values", elt)
    bits = list(map(repr, args))
    bits.extend(sorted(f"{k}={v!r}" for k, v in kwargs.items()))
    return "{}({})".format(f.__name__, ", ".join(bits))


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
