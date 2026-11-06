# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import types
import typing
from functools import wraps

import pytest

from hypothesis import given, settings, strategies as st


def make_module(name, source):
    module = types.ModuleType(name)
    exec("from __future__ import annotations\n" + source, module.__dict__)
    return module


@pytest.mark.parametrize(
    "kind", ["direct", "wraps", "function", "plain", "explicit-returns"]
)
@settings(max_examples=3, derandomize=True, database=None, deadline=None)
@given(data=st.data())
def test_authored_wrapper_keeps_existing_annotation_resolution(kind, data):
    foreign = make_module(
        "authored_wrapper_foreign",
        """
Alias = bytes
class Callable:
    def __call__(self, value: Alias) -> Alias:
        raise AssertionError("prototype body ran")
def function(value: Alias) -> Alias:
    raise AssertionError("function body ran")
""",
    )
    authored = make_module(
        "authored_wrapper_own",
        """
Alias = tuple[int, str]
def wrapper(value: Alias) -> Alias:
    raise AssertionError("wrapper body ran")
""",
    )
    wrapper = authored.wrapper
    if kind == "function":
        wrapper.__wrapped__ = foreign.function
    elif kind == "wraps":
        wraps(foreign.Callable(), assigned=())(wrapper)
    elif kind != "plain":
        wrapper.__wrapped__ = foreign.Callable()

    if kind in ("direct", "wraps", "explicit-returns"):
        # typing cannot obtain globals through this nonfunction __wrapped__.
        # Hypothesis must preserve its unresolved-hint fallback, rather than
        # resolving this user's annotations in the callable's foreign module.
        with pytest.raises(NameError):
            typing.get_type_hints(wrapper)
    else:
        expected = bytes if kind == "function" else tuple[int, str]
        assert typing.get_type_hints(wrapper)["return"] == expected

    strategy = (
        st.functions(like=wrapper, returns=st.just("sentinel"))
        if kind == "explicit-returns"
        else st.functions(like=wrapper)
    )
    generated = data.draw(strategy)
    value = generated((1, "argument"))
    if kind in ("direct", "wraps"):
        assert value is None
    elif kind == "function":
        assert isinstance(value, bytes)
    elif kind == "plain":
        assert isinstance(value, tuple)
        assert len(value) == 2
        assert isinstance(value[0], int)
        assert isinstance(value[1], str)
    else:
        assert value == "sentinel"
