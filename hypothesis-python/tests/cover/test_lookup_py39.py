# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
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

import typing

import pytest
from hypothesis import strategies as st


@pytest.mark.parametrize(
    "annotated_type,expected_strategy",
    [
        (typing.Annotated[int, "foo"], st.integers()),
        (typing.Annotated[typing.List[float], "foo"], st.lists(st.floats())),
        (typing.Annotated[typing.Annotated[str, "foo"], "bar"], st.text()),
        (
            typing.Annotated[
                typing.Annotated[typing.List[typing.Dict[str, bool]], "foo"], "bar"
            ],
            st.lists(st.dictionaries(keys=st.text(), values=st.booleans())),
        ),
    ],
)
def test_typing_Annotated(annotated_type, expected_strategy):
    assert repr(st.from_type(annotated_type)) == repr(expected_strategy)
