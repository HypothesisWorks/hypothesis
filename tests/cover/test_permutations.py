from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis import find, given
from hypothesis.strategies import permutations


def test_can_find_non_trivial_permutation():
    x = find(
        permutations(list(range(5))), lambda x: x[0] != 0
    )

    assert x == [1, 0, 2, 3, 4]


@given(permutations(list('abcd')))
def test_permutation_values_are_permutations(perm):
    assert len(perm) == 4
    assert set(perm) == set('abcd')
