# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from typing import Callable

import pytest

from hypothesis import strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.internal.compat import Concatenate, ParamSpec
from hypothesis.strategies._internal.types import NON_RUNTIME_TYPES

try:
    from typing import TypeGuard  # new in 3.10
except ImportError:
    TypeGuard = None


@pytest.mark.parametrize("non_runtime_type", NON_RUNTIME_TYPES)
def test_non_runtime_type_cannot_be_resolved(non_runtime_type):
    strategy = st.from_type(non_runtime_type)
    with pytest.raises(
        InvalidArgument, match="there is no such thing as a runtime instance"
    ):
        strategy.example()


@pytest.mark.parametrize("non_runtime_type", NON_RUNTIME_TYPES)
def test_non_runtime_type_cannot_be_registered(non_runtime_type):
    with pytest.raises(
        InvalidArgument, match="there is no such thing as a runtime instance"
    ):
        st.register_type_strategy(non_runtime_type, st.none())


@pytest.mark.skipif(Concatenate is None, reason="requires python3.10 or higher")
def test_callable_with_concatenate():
    P = ParamSpec("P")
    func_type = Callable[Concatenate[int, P], None]
    strategy = st.from_type(func_type)
    with pytest.raises(
        InvalidArgument,
        match="Hypothesis can't yet construct a strategy for instances of a Callable type",
    ):
        strategy.example()

    with pytest.raises(InvalidArgument, match="Cannot register generic type"):
        st.register_type_strategy(func_type, st.none())


@pytest.mark.skipif(ParamSpec is None, reason="requires python3.10 or higher")
def test_callable_with_paramspec():
    P = ParamSpec("P")
    func_type = Callable[P, None]
    strategy = st.from_type(func_type)
    with pytest.raises(
        InvalidArgument,
        match="Hypothesis can't yet construct a strategy for instances of a Callable type",
    ):
        strategy.example()

    with pytest.raises(InvalidArgument, match="Cannot register generic type"):
        st.register_type_strategy(func_type, st.none())


@pytest.mark.skipif(TypeGuard is None, reason="requires python3.10 or higher")
def test_callable_return_typegard_type():
    strategy = st.from_type(Callable[[], TypeGuard[int]])
    with pytest.raises(
        InvalidArgument,
        match="Hypothesis cannot yet construct a strategy for callables "
        "which are PEP-647 TypeGuards",
    ):
        strategy.example()

    with pytest.raises(InvalidArgument, match="Cannot register generic type"):
        st.register_type_strategy(Callable[[], TypeGuard[int]], st.none())
