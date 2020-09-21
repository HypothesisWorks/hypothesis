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

from hypothesis import given, strategies as st


def test_includes_non_default_args_in_repr():
    assert repr(st.integers()) == "integers()"
    assert repr(st.integers(min_value=1)) == "integers(min_value=1)"


def test_sampled_repr_leaves_range_as_range():
    huge = 10 ** 100
    assert repr(st.sampled_from(range(huge))) == "sampled_from(range(0, %s))" % (huge,)


def hi(there, stuff):
    return there


def test_supports_positional_and_keyword_args_in_builds():
    assert (
        repr(st.builds(hi, st.integers(), there=st.booleans()))
        == "builds(hi, integers(), there=booleans())"
    )


def test_preserves_sequence_type_of_argument():
    assert repr(st.sampled_from([0, 1])) == "sampled_from([0, 1])"
    assert repr(st.sampled_from((0, 1))) == "sampled_from((0, 1))"


class IHaveABadRepr:
    def __repr__(self):
        raise ValueError("Oh no!")


def test_errors_are_deferred_until_repr_is_calculated():
    s = (
        st.builds(
            lambda x, y: 1,
            st.just(IHaveABadRepr()),
            y=st.one_of(st.sampled_from((IHaveABadRepr(),)), st.just(IHaveABadRepr())),
        )
        .map(lambda t: t)
        .filter(lambda t: True)
        .flatmap(lambda t: st.just(IHaveABadRepr()))
    )

    with pytest.raises(ValueError):
        repr(s)


@given(st.iterables(st.integers()))
def test_iterables_repr_is_useful(it):
    # fairly hard-coded but useful; also ensures _values are inexhaustible
    assert repr(it) == f"iter({it._values!r})"
