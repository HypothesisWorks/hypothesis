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

import abc
import enum
import sys
from typing import Callable, Dict, Generic, List, Sequence, TypeVar, Union

import pytest

from hypothesis import given, infer, strategies as st
from hypothesis.errors import (
    HypothesisDeprecationWarning,
    InvalidArgument,
    ResolutionFailed,
)
from hypothesis.internal.reflection import get_pretty_function_description
from hypothesis.strategies._internal import types
from hypothesis.strategies._internal.core import _from_type
from hypothesis.strategies._internal.types import _global_type_lookup
from hypothesis.strategies._internal.utils import _strategies

from tests.common.debug import assert_all_examples, find_any
from tests.common.utils import fails_with, temp_registered

# Build a set of all types output by core strategies
blocklist = {
    "builds",
    "data",
    "deferred",
    "from_regex",
    "from_type",
    "ip_addresses",
    "iterables",
    "just",
    "nothing",
    "one_of",
    "permutations",
    "random_module",
    "randoms",
    "recursive",
    "runner",
    "sampled_from",
    "shared",
    "timezone_keys",
    "timezones",
}
assert set(_strategies).issuperset(blocklist), blocklist.difference(_strategies)
types_with_core_strat = set()
for thing in (
    getattr(st, name)
    for name in sorted(_strategies)
    if name in dir(st) and name not in blocklist
):
    for n in range(3):
        try:
            ex = thing(*([st.nothing()] * n)).example()
            types_with_core_strat.add(type(ex))
            break
        except (TypeError, InvalidArgument, HypothesisDeprecationWarning):
            continue


def test_generic_sequence_of_integers_may_be_lists_or_bytes():
    strat = st.from_type(Sequence[int])
    find_any(strat, lambda x: isinstance(x, bytes))
    find_any(strat, lambda x: isinstance(x, list))


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
    with temp_registered(typ, st.just(sentinel)):
        assert st.from_type(typ).example() is sentinel
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
    with temp_registered(UnknownType, st.just(sentinel)):
        assert st.from_type(UnknownType).example() is sentinel
        # Also covered by registration of child class
        assert st.from_type(ParentUnknownType).example() is sentinel


def test_custom_type_resolution_with_function():
    sentinel = object()
    with temp_registered(UnknownType, lambda _: st.just(sentinel)):
        assert st.from_type(UnknownType).example() is sentinel
        assert st.from_type(ParentUnknownType).example() is sentinel


def test_custom_type_resolution_with_function_non_strategy():
    with temp_registered(UnknownType, lambda _: None):
        with pytest.raises(ResolutionFailed):
            st.from_type(UnknownType).example()
        with pytest.raises(ResolutionFailed):
            st.from_type(ParentUnknownType).example()


def test_errors_if_generic_resolves_empty():
    with temp_registered(UnknownType, lambda _: st.nothing()):
        fails_1 = st.from_type(UnknownType)
        with pytest.raises(ResolutionFailed):
            fails_1.example()
        fails_2 = st.from_type(ParentUnknownType)
        with pytest.raises(ResolutionFailed):
            fails_2.example()


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


@fails_with(InvalidArgument)
@given(st.from_type(EmptyEnum))
def test_error_if_enum_is_empty(x):
    pass


class BrokenClass:
    __init__ = "Hello!"


def test_uninspectable_builds():
    with pytest.raises(TypeError, match="object is not callable"):
        st.builds(BrokenClass).example()


def test_uninspectable_from_type():
    with pytest.raises(TypeError, match="object is not callable"):
        st.from_type(BrokenClass).example()


def _check_instances(t):
    # See https://github.com/samuelcolvin/pydantic/discussions/2508
    return t.__module__ != "typing" and not t.__module__.startswith("pydantic")


@pytest.mark.parametrize(
    "typ", sorted((x for x in _global_type_lookup if _check_instances(x)), key=str)
)
@given(data=st.data())
def test_can_generate_from_all_registered_types(data, typ):
    value = data.draw(st.from_type(typ), label="value")
    assert isinstance(value, typ)


T = TypeVar("T")


class MyGeneric(Generic[T]):
    def __init__(self, arg: T) -> None:
        self.arg = arg


class Lines(Sequence[str]):
    """Represent a sequence of text lines.

    It turns out that resolving a class which inherits from a parametrised generic
    type is... tricky.  See https://github.com/HypothesisWorks/hypothesis/issues/2951
    """


class SpecificDict(Dict[int, int]):
    pass


def using_generic(instance: MyGeneric[T]) -> T:
    return instance.arg


def using_concrete_generic(instance: MyGeneric[int]) -> int:
    return instance.arg


def test_generic_origin_empty():
    with pytest.raises(ResolutionFailed):
        find_any(st.builds(using_generic))


_skip_callables_mark = pytest.mark.skipif(sys.version_info[:2] < (3, 7), reason="old")


@_skip_callables_mark
def test_issue_2951_regression():
    lines_strat = st.builds(Lines, lines=st.lists(st.text()))
    with temp_registered(Lines, lines_strat):
        assert st.from_type(Lines) == lines_strat
        # Now let's test that the strategy for ``Sequence[int]`` did not
        # change just because we registered a strategy for ``Lines``:
        expected = "one_of(binary(), lists(integers()))"
        assert repr(st.from_type(Sequence[int])) == expected


@_skip_callables_mark
def test_issue_2951_regression_two_params():
    map_strat = st.builds(SpecificDict, st.dictionaries(st.integers(), st.integers()))
    expected = repr(st.from_type(Dict[int, int]))
    with temp_registered(SpecificDict, map_strat):
        assert st.from_type(SpecificDict) == map_strat
        assert expected == repr(st.from_type(Dict[int, int]))


@pytest.mark.parametrize(
    "generic",
    (
        Union[str, int],
        Sequence[Sequence[int]],
        MyGeneric[str],
        # On Python <= 3.6, we always trigger the multi-registration guard clause
        # and raise InvalidArgument on the first attempted registration.
        pytest.param(Callable[..., str], marks=_skip_callables_mark),
        pytest.param(Callable[[int], str], marks=_skip_callables_mark),
    ),
    ids=repr,
)
@pytest.mark.parametrize("strategy", [st.none(), lambda _: st.none()])
def test_generic_origin_with_type_args(generic, strategy):
    with pytest.raises(InvalidArgument):
        st.register_type_strategy(generic, strategy)
    assert generic not in types._global_type_lookup


@pytest.mark.parametrize(
    "generic",
    (
        Callable,
        List,
        Sequence,
        # you can register types with all generic parameters
        List[T],
        Sequence[T],
        # User-defined generics should also work
        MyGeneric,
        MyGeneric[T],
    ),
)
def test_generic_origin_without_type_args(generic):
    with temp_registered(generic, st.just("example")):
        pass


@pytest.mark.parametrize(
    "strat, type_",
    [
        (st.from_type, MyGeneric[T]),
        (st.from_type, MyGeneric[int]),
        (st.from_type, MyGeneric),
        (st.builds, using_generic),
        (st.builds, using_concrete_generic),
    ],
    ids=get_pretty_function_description,
)
def test_generic_origin_from_type(strat, type_):
    with temp_registered(MyGeneric, st.builds(MyGeneric)):
        find_any(strat(type_))


def test_generic_origin_concrete_builds():
    with temp_registered(MyGeneric, st.builds(MyGeneric, st.integers())):
        assert_all_examples(
            st.builds(using_generic), lambda example: isinstance(example, int)
        )


class AbstractFoo(abc.ABC):
    def __init__(self, x):
        pass

    @abc.abstractmethod
    def qux(self):
        pass


class ConcreteFoo1(AbstractFoo):
    # Can't resolve this one due to unannotated `x` param
    def qux(self):
        pass


class ConcreteFoo2(AbstractFoo):
    def __init__(self, x: int):
        pass

    def qux(self):
        pass


@given(st.from_type(AbstractFoo))
def test_gen_abstract(foo):
    # This requires that we correctly checked which of the subclasses
    # could be resolved, rather than unconditionally using all of them.
    assert isinstance(foo, ConcreteFoo2)


class AbstractBar(abc.ABC):
    def __init__(self, x):
        pass

    @abc.abstractmethod
    def qux(self):
        pass


class ConcreteBar(AbstractBar):
    def qux(self):
        pass


def test_abstract_resolver_fallback():
    # We create our distinct strategies for abstract and concrete types
    gen_abstractbar = _from_type(AbstractBar)
    gen_concretebar = st.builds(ConcreteBar, x=st.none())
    assert gen_abstractbar != gen_concretebar

    # And trying to generate an instance of the abstract type fails,
    # UNLESS the concrete type is currently resolvable
    with pytest.raises(ResolutionFailed):
        gen_abstractbar.example()
    with temp_registered(ConcreteBar, gen_concretebar):
        gen = gen_abstractbar.example()
    with pytest.raises(ResolutionFailed):
        gen_abstractbar.example()

    # which in turn means we resolve to the concrete subtype.
    assert isinstance(gen, ConcreteBar)
