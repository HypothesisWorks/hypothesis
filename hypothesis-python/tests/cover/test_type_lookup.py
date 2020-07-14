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

import enum

import pytest

from hypothesis import given, infer, strategies as st
from hypothesis.errors import (
    HypothesisDeprecationWarning,
    InvalidArgument,
    ResolutionFailed,
)
from hypothesis.strategies._internal import types
from hypothesis.strategies._internal.core import _strategies
from hypothesis.strategies._internal.types import _global_type_lookup

# Build a set of all types output by core strategies
blacklist = [
    "builds",
    "from_regex",
    "from_type",
    "ip_addresses",
    "iterables",
    "permutations",
    "random_module",
    "randoms",
    "runner",
    "sampled_from",
]
types_with_core_strat = set()
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


class ParentUnknownType:
    pass


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


def test_given_can_infer_from_manual_annotations():
    # Editing annotations before decorating is hilariously awkward, but works!
    def inner(a):
        pass

    inner.__annotations__ = {"a": int}
    given(a=infer)(inner)()


class EmptyEnum(enum.Enum):
    pass


def test_error_if_enum_is_empty():
    with pytest.raises(InvalidArgument):
        assert st.from_type(EmptyEnum).is_empty


class BrokenClass:
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
