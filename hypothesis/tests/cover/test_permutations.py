# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import given
from hypothesis.errors import InvalidArgument
from hypothesis.strategies import permutations

from tests.common.debug import check_can_generate_examples, minimal
from tests.common.utils import fails_with


def test_can_find_non_trivial_permutation():
    x = minimal(permutations(list(range(5))), lambda x: x[0] != 0)

    assert x == [1, 0, 2, 3, 4]


@given(permutations(list("abcd")))
def test_permutation_values_are_permutations(perm):
    assert len(perm) == 4
    assert set(perm) == set("abcd")


@given(permutations([]))
def test_empty_permutations_are_empty(xs):
    assert xs == []


@fails_with(InvalidArgument)
def test_cannot_permute_non_sequence_types():
    check_can_generate_examples(permutations(set()))
