# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
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

from __future__ import absolute_import, division, print_function

import pytest
from dpcontracts import require

from hypothesis import given
from hypothesis.errors import InvalidArgument
from hypothesis.extra.dpcontracts import fulfill
from hypothesis.strategies import builds, integers


def identity(x):
    return x


@require("division is undefined for zero", lambda args: args.n != 0)
def invert(n):
    return 1 / n


@given(builds(fulfill(invert), integers()))
def test_contract_filter_builds(x):
    assert -1 <= x <= 1


@given(integers())
def test_contract_filter_inline(n):
    assert -1 <= fulfill(invert)(n) <= 1


@pytest.mark.parametrize("f", [int, identity, lambda x: None])
def test_no_vacuous_fulfill(f):
    with pytest.raises(InvalidArgument):
        fulfill(f)
