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

from hypothesis import given, strategies as st

given_booleans = given(st.booleans())


@given_booleans
def test_has_an_arg_named_x(x):
    pass


@given_booleans
def test_has_an_arg_named_y(y):
    pass


given_named_booleans = given(z=st.text())


def test_fail_independently():
    @given_named_booleans
    def test_z1(z):
        raise AssertionError

    @given_named_booleans
    def test_z2(z):
        pass

    with pytest.raises(AssertionError):
        test_z1()

    test_z2()
