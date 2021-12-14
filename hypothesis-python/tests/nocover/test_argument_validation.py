# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from inspect import Parameter

import pytest

from hypothesis import strategies as st
from hypothesis.strategies._internal.utils import _strategies

from tests.common.arguments import argument_validation_test, e

BAD_ARGS = []


def adjust(ex, **kwargs):
    f, a, b = ex
    b = dict(b)
    b.update(kwargs)
    BAD_ARGS.append((f, a, b))


for ex in [
    e(st.lists, st.integers()),
    e(st.sets, st.integers()),
    e(st.frozensets, st.integers()),
    e(st.dictionaries, st.integers(), st.integers()),
    e(st.text),
    e(st.binary),
]:
    adjust(ex, min_size=-1)
    adjust(ex, max_size=-1)
    adjust(ex, min_size="no")
    adjust(ex, max_size="no")


BAD_ARGS.extend([e(st.lists, st.nothing(), unique=True, min_size=1)])

test_raise_invalid_argument = argument_validation_test(BAD_ARGS)


@pytest.mark.parametrize("name", sorted(_strategies))
def test_consistent_with_api_guide_on_kwonly_args(name):
    # Enforce our style-guide: if it has a default value, it should be
    # keyword-only with a very few exceptions.
    for arg in _strategies[name].parameters.values():
        assert (
            arg.default == Parameter.empty
            or arg.kind != Parameter.POSITIONAL_OR_KEYWORD
            or arg.name in ("min_value", "max_value", "subtype_strategy", "columns")
            or name in ("text", "range_indexes", "badly_draw_lists", "write_pattern")
        ), f"need kwonly args in {name}"
