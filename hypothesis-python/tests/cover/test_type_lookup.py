# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import abc
import enum
import sys
import typing
from collections.abc import Sequence
from inspect import Parameter as P, Signature
from typing import Callable, Generic, List as _List, TypeVar, Union

import pytest

from hypothesis import given, infer, settings, strategies as st
from hypothesis.errors import InvalidArgument, ResolutionFailed
from hypothesis.internal.compat import get_type_hints
from hypothesis.internal.reflection import get_pretty_function_description
from hypothesis.strategies._internal import types
from hypothesis.strategies._internal.lazy import LazyStrategy
from hypothesis.strategies._internal.types import _global_type_lookup
from hypothesis.strategies._internal.utils import _strategies

from tests.common.debug import (
    assert_all_examples,
    assert_simple_property,
    check_can_generate_examples,
    find_any,
)
from tests.common.utils import Why, fails_with, temp_registered, xfail_on_crosshair

types_with_core_strat = {
    type_
    for type_, strat in _global_type_lookup.items()
    if isinstance(strat, LazyStrategy) and strat.function in vars(st).values()
}


@pytest.mark.skipif(sys.version_info[:2] >= (3, 14), reason="FIXME-py314")
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
    found = set()
    for thing in (
        getattr(st, name)
        for name in sorted(_strategies)
        if name in dir(st) and name not in blocklist
    ):
        for n in range(3):
            try:
                ex = find_any(thing(*([st.nothing()] * n)))
                found.add(type(ex))
                break
            except Exception:
                continue

    cannot_lookup = found - set(types._global_type_lookup)
    assert not cannot_lookup


def test_lookup_keys_are_types():
    with pytest.raises(InvalidArgument):
        st.register_type_strategy("int", st.integers())
    assert "int" not in types._global_type_lookup


@pytest.mark.parametrize(
    "typ, not_a_strategy",
    [
        (int, 42),  # Values must be strategies
        # Can't register NotImplemented directly, even though strategy functions
        # can return it.
        (int, NotImplemented),
    ],
)
def test_lookup_values_are_strategies(typ, not_a_strategy):
    with pytest.raises(InvalidArgument):
        st.register_type_strategy(typ, not_a_strategy)
    assert not_a_strategy not in types._global_type_lookup.values()


@pytest.mark.parametrize("typ", sorted(types_with_core_strat, key=str))
def test_lookup_overrides_defaults(typ):
    sentinel = object()
    with temp_registered(typ, st.just(sentinel)):
        assert_simple_property(st.from_type(typ), lambda v: v is sentinel)
    assert_simple_property(st.from_type(typ), lambda v: v is not sentinel)


class ParentUnknownType:
    pass


class UnknownType(ParentUnknownType):
    def __init__(self, arg):
        pass


def test_custom_type_resolution_fails_without_registering():
    fails = st.from_type(UnknownType)
    with pytest.raises(ResolutionFailed):
        check_can_generate_examples(fails)


def test_custom_type_resolution():
    sentinel = object()
    with temp_registered(UnknownType, st.just(sentinel)):
        assert_simple_property(st.from_type(UnknownType), lambda v: v is sentinel)
        # Also covered by registration of child class
        assert_simple_property(st.from_type(ParentUnknownType), lambda v: v is sentinel)


def test_custom_type_resolution_with_function():
    sentinel = object()
    with temp_registered(UnknownType, lambda _: st.just(sentinel)):
        assert_simple_property(st.from_type(UnknownType), lambda v: v is sentinel)
        assert_simple_property(st.from_type(ParentUnknownType), lambda v: v is sentinel)


def test_custom_type_resolution_with_function_non_strategy():
    with temp_registered(UnknownType, lambda _: None):
        with pytest.raises(ResolutionFailed):
            check_can_generate_examples(st.from_type(UnknownType))
        with pytest.raises(ResolutionFailed):
            check_can_generate_examples(st.from_type(ParentUnknownType))


@pytest.mark.parametrize("strategy_returned", [True, False])
def test_conditional_type_resolution_with_function(strategy_returned):
    sentinel = object()

    def resolve_strategy(thing):
        assert thing == UnknownType
        if strategy_returned:
            return st.just(sentinel)
        return NotImplemented

    with temp_registered(UnknownType, resolve_strategy):
        if strategy_returned:
            assert_simple_property(st.from_type(UnknownType), lambda v: v is sentinel)
        else:
            with pytest.raises(ResolutionFailed):
                check_can_generate_examples(st.from_type(UnknownType))


def test_errors_if_generic_resolves_empty():
    with temp_registered(UnknownType, lambda _: st.nothing()):
        fails_1 = st.from_type(UnknownType)
        with pytest.raises(ResolutionFailed):
            check_can_generate_examples(fails_1)
        fails_2 = st.from_type(ParentUnknownType)
        with pytest.raises(ResolutionFailed):
            check_can_generate_examples(fails_2)


def test_cannot_register_empty():
    # Cannot register and did not register
    with pytest.raises(InvalidArgument):
        st.register_type_strategy(UnknownType, st.nothing())
    fails = st.from_type(UnknownType)
    with pytest.raises(ResolutionFailed):
        check_can_generate_examples(fails)
    assert UnknownType not in types._global_type_lookup


def test_pulic_interface_works():
    check_can_generate_examples(st.from_type(int))
    fails = st.from_type("not a type or annotated function")
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(fails)


@pytest.mark.parametrize("infer_token", [infer, ...])
def test_given_can_infer_from_manual_annotations(infer_token):
    # Editing annotations before decorating is hilariously awkward, but works!
    def inner(a):
        assert isinstance(a, int)

    inner.__annotations__ = {"a": int}
    given(a=infer_token)(inner)()


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
        check_can_generate_examples(st.builds(BrokenClass))


def test_uninspectable_from_type():
    with pytest.raises(TypeError, match="object is not callable"):
        check_can_generate_examples(st.from_type(BrokenClass))


def _check_instances(t):
    # See https://github.com/samuelcolvin/pydantic/discussions/2508
    return (
        t.__module__ != "typing"
        and t.__name__ != "ByteString"
        and not t.__module__.startswith("pydantic")
        and t.__module__ != "typing_extensions"
    )


def maybe_mark(x):
    if x.__name__ in "Match Decimal IPv4Address":
        marks = xfail_on_crosshair(Why.other, as_marks=True, strict=False)
        return pytest.param(x, marks=marks)
    return x


@pytest.mark.parametrize(
    "typ",
    sorted(
        (maybe_mark(x) for x in _global_type_lookup if _check_instances(x)),
        key=str,
    ),
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


class SpecificDict(dict[int, int]):
    pass


def using_generic(instance: MyGeneric[T]) -> T:
    return instance.arg


def using_concrete_generic(instance: MyGeneric[int]) -> int:
    return instance.arg


def test_generic_origin_empty():
    with pytest.raises(ResolutionFailed):
        check_can_generate_examples(st.builds(using_generic))


def test_issue_2951_regression():
    lines_strat = st.builds(Lines, lines=st.lists(st.text()))
    prev_seq_int_repr = repr(st.from_type(Sequence[int]))
    with temp_registered(Lines, lines_strat):
        assert st.from_type(Lines) == lines_strat
        # Now let's test that the strategy for ``Sequence[int]`` did not
        # change just because we registered a strategy for ``Lines``:
        assert repr(st.from_type(Sequence[int])) == prev_seq_int_repr


def test_issue_2951_regression_two_params():
    map_strat = st.builds(SpecificDict, st.dictionaries(st.integers(), st.integers()))
    expected = repr(st.from_type(dict[int, int]))
    with temp_registered(SpecificDict, map_strat):
        assert st.from_type(SpecificDict) == map_strat
        assert expected == repr(st.from_type(dict[int, int]))


@pytest.mark.parametrize(
    "generic",
    (
        Union[str, int],
        Sequence[Sequence[int]],
        MyGeneric[str],
        Callable[..., str],
        Callable[[int], str],
    ),
    ids=repr,
)
@pytest.mark.parametrize("strategy", [st.none(), lambda _: st.none()])
def test_generic_origin_with_type_args(generic, strategy):
    with pytest.raises(InvalidArgument):
        st.register_type_strategy(generic, strategy)
    assert generic not in types._global_type_lookup


skip_39 = pytest.mark.skipif(sys.version_info[:2] == (3, 9), reason="early version")


@pytest.mark.parametrize(
    "generic",
    (
        Callable,
        list,
        Sequence,
        # you can register types with all generic parameters
        _List[T],
        getattr(typing, "Sequence", None)[T],  # pyupgrade workaround
        pytest.param(list[T], marks=skip_39),
        pytest.param(Sequence[T], marks=skip_39),
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
        check_can_generate_examples(strat(type_))


def test_generic_origin_concrete_builds():
    with temp_registered(MyGeneric, st.builds(MyGeneric, st.integers())):
        assert_all_examples(
            st.builds(using_generic), lambda example: isinstance(example, int)
        )


class AbstractFoo(abc.ABC):
    def __init__(self, x):  # noqa: B027
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
    def __init__(self, x):  # noqa: B027
        pass

    @abc.abstractmethod
    def qux(self):
        pass


class ConcreteBar(AbstractBar):
    def qux(self):
        pass


def test_abstract_resolver_fallback():
    # We create our distinct strategies for abstract and concrete types
    gen_abstractbar = st.from_type(AbstractBar)
    gen_concretebar = st.builds(ConcreteBar, x=st.none())
    assert gen_abstractbar != gen_concretebar

    # And trying to generate an instance of the abstract type fails,
    # UNLESS the concrete type is currently resolvable
    with pytest.raises(ResolutionFailed):
        check_can_generate_examples(gen_abstractbar)
    with temp_registered(ConcreteBar, gen_concretebar):
        # which in turn means we resolve to the concrete subtype.
        assert_simple_property(
            gen_abstractbar, lambda gen: isinstance(gen, ConcreteBar)
        )
    with pytest.raises(ResolutionFailed):
        check_can_generate_examples(gen_abstractbar)


def _one_arg(x: int):
    assert isinstance(x, int)


def _multi_arg(x: int, y: str):
    assert isinstance(x, int)
    assert isinstance(y, str)


def _kwd_only(*, y: str):
    assert isinstance(y, str)


def _pos_and_kwd_only(x: int, *, y: str):
    assert isinstance(x, int)
    assert isinstance(y, str)


@pytest.mark.parametrize("func", [_one_arg, _multi_arg, _kwd_only, _pos_and_kwd_only])
def test_infer_all(func):
    # tests @given(...) against various signatures
    settings(max_examples=1)(given(...))(func)()


def test_does_not_add_param_empty_to_type_hints():
    def f(x):
        pass

    f.__signature__ = Signature([P("y", P.KEYWORD_ONLY)], return_annotation=None)
    assert get_type_hints(f) == {}
