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
from dpcontracts import require

from hypothesis import given
from hypothesis.errors import InvalidArgument
from hypothesis.extra.dpcontracts import fulfill
from hypothesis.internal.conjecture.utils import identity
from hypothesis.strategies import builds, integers


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
