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

import enum

import pytest

import hypothesis.strategies as st
from hypothesis import given, infer
from hypothesis._strategies import _strategies
from hypothesis.errors import (
    HypothesisDeprecationWarning,
    InvalidArgument,
    ResolutionFailed,
)
from hypothesis.internal.compat import PY2, integer_types
from hypothesis.searchstrategy import types
from hypothesis.searchstrategy.types import _global_type_lookup
from tests.common.utils import checks_deprecated_behaviour

# Build a set of all types output by core strategies
blacklist = [
    "builds",
    "iterables",
    "permutations",
    "random_module",
    "randoms",
    "runner",
    "sampled_from",
]
types_with_core_strat = set(integer_types)
for thing in (
    getattr(st, name)
    for name in sorted(_strategies)
    if name in dir(st) and name not in blacklist
):
    for n in range(3):
        try:
            ex = thing(*([st.nothing()] * n)).example()
            types_with_core_strat.add(type(ex))
            break
        except (TypeError, InvalidArgument, HypothesisDeprecationWarning):
            continue


@pytest.mark.parametrize("typ", sorted(types_with_core_strat, key=str))
def test_resolve_core_strategies(typ):
    @given(st.from_type(typ))
    def inner(ex):
        if PY2 and issubclass(typ, integer_types):
            assert isinstance(ex, integer_types)
        else:
            assert isinstance(ex, typ)

    inner()


def test_lookup_knows_about_all_core_strategies():
    cannot_lookup = types_with_core_strat - set(types._global_type_lookup)
    assert not cannot_lookup


def test_lookup_keys_are_types():
    with pytest.raises(InvalidArgument):
        st.register_type_strategy("int", st.integers())
    assert "int" not in types._global_type_lookup


def test_lookup_values_are_strategies():
    with pytest.raises(InvalidArgument):
        st.register_type_strategy(int, 42)
    assert 42 not in types._global_type_lookup.values()


@pytest.mark.parametrize("typ", sorted(types_with_core_strat, key=str))
def test_lookup_overrides_defaults(typ):
    sentinel = object()
    try:
        strat = types._global_type_lookup[typ]
        st.register_type_strategy(typ, st.just(sentinel))
        assert st.from_type(typ).example() is sentinel
    finally:
        st.register_type_strategy(typ, strat)
        st.from_type.__clear_cache()
    assert st.from_type(typ).example() is not sentinel


class ParentUnknownType(object):
    pass


def test_can_resolve_trivial_types():
    # Under Python 2, this inherits a special wrapper_descriptor slots
    # thing from object.__init__, which chokes inspect.getargspec.
    # from_type should and does work anyway; see issues #1655 and #1656.
    st.from_type(ParentUnknownType).example()


class UnknownType(ParentUnknownType):
    def __init__(self, arg):
        pass


def test_custom_type_resolution_fails_without_registering():
    fails = st.from_type(UnknownType)
    with pytest.raises(ResolutionFailed):
        fails.example()


def test_custom_type_resolution():
    sentinel = object()
    try:
        st.register_type_strategy(UnknownType, st.just(sentinel))
        assert st.from_type(UnknownType).example() is sentinel
        # Also covered by registration of child class
        assert st.from_type(ParentUnknownType).example() is sentinel
    finally:
        types._global_type_lookup.pop(UnknownType)
        st.from_type.__clear_cache()
        assert UnknownType not in types._global_type_lookup


def test_custom_type_resolution_with_function():
    sentinel = object()
    try:
        st.register_type_strategy(UnknownType, lambda _: st.just(sentinel))
        assert st.from_type(UnknownType).example() is sentinel
        assert st.from_type(ParentUnknownType).example() is sentinel
    finally:
        types._global_type_lookup.pop(UnknownType)
        st.from_type.__clear_cache()


def test_custom_type_resolution_with_function_non_strategy():
    try:
        st.register_type_strategy(UnknownType, lambda _: None)
        with pytest.raises(ResolutionFailed):
            st.from_type(UnknownType).example()
        with pytest.raises(ResolutionFailed):
            st.from_type(ParentUnknownType).example()
    finally:
        types._global_type_lookup.pop(UnknownType)


def test_errors_if_generic_resolves_empty():
    try:
        st.register_type_strategy(UnknownType, lambda _: st.nothing())
        fails_1 = st.from_type(UnknownType)
        with pytest.raises(ResolutionFailed):
            fails_1.example()
        fails_2 = st.from_type(ParentUnknownType)
        with pytest.raises(ResolutionFailed):
            fails_2.example()
    finally:
        types._global_type_lookup.pop(UnknownType)
        st.from_type.__clear_cache()


def test_cannot_register_empty():
    # Cannot register and did not register
    with pytest.raises(InvalidArgument):
        st.register_type_strategy(UnknownType, st.nothing())
    fails = st.from_type(UnknownType)
    with pytest.raises(ResolutionFailed):
        fails.example()
    assert UnknownType not in types._global_type_lookup


def test_pulic_interface_works():
    st.from_type(int).example()
    fails = st.from_type("not a type or annotated function")
    with pytest.raises(InvalidArgument):
        fails.example()


def test_given_can_infer_on_py2():
    # Editing annotations before decorating is hilariously awkward, but works!
    def inner(a):
        pass

    inner.__annotations__ = {"a": int}
    given(a=infer)(inner)()


class EmptyEnum(enum.Enum):
    pass


@checks_deprecated_behaviour
def test_error_if_enum_is_empty():
    assert st.from_type(EmptyEnum).is_empty


class BrokenClass(object):
    __init__ = "Hello!"


def test_uninspectable_builds():
    with pytest.raises(TypeError, match="object is not callable"):
        st.builds(BrokenClass).example()


def test_uninspectable_from_type():
    with pytest.raises(TypeError, match="object is not callable"):
        st.from_type(BrokenClass).example()


@pytest.mark.parametrize(
    "typ", sorted((x for x in _global_type_lookup if x.__module__ != "typing"), key=str)
)
@given(data=st.data())
def test_can_generate_from_all_registered_types(data, typ):
    value = data.draw(st.from_type(typ), label="value")
    assert isinstance(value, typ)
