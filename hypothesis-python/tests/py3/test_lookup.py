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

import abc
import collections
import enum
import io
import string
import sys

import pytest

import hypothesis.strategies as st
from hypothesis import HealthCheck, assume, given, infer, settings
from hypothesis.errors import InvalidArgument, ResolutionFailed, Unsatisfiable
from hypothesis.internal.compat import (
    ForwardRef,
    get_type_hints,
    integer_types,
    typing_root_type,
)
from hypothesis.searchstrategy import types
from hypothesis.strategies import from_type
from tests.common.debug import minimal
from tests.common.utils import fails_with

typing = pytest.importorskip("typing")
sentinel = object()
generics = sorted(
    (t for t in types._global_type_lookup if isinstance(t, typing_root_type)), key=str
)


@pytest.mark.parametrize("typ", generics)
def test_resolve_typing_module(typ):
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    @given(from_type(typ))
    def inner(ex):
        if typ in (typing.BinaryIO, typing.TextIO):
            assert isinstance(ex, io.IOBase)
        elif typ is typing.Tuple:
            # isinstance is incompatible with Tuple on early 3.5
            assert ex == ()
        elif isinstance(typ, typing._ProtocolMeta):
            pass
        elif typ is typing.Type and not isinstance(typing.Type, type):
            assert isinstance(ex, typing.TypeVar)
        else:
            try:
                assert isinstance(ex, typ)
            except TypeError:
                if sys.version_info[:2] < (3, 6):
                    pytest.skip()
                raise

    inner()


@pytest.mark.parametrize("typ", [typing.Any, typing.Union])
def test_does_not_resolve_special_cases(typ):
    with pytest.raises(InvalidArgument):
        from_type(typ).example()


@pytest.mark.parametrize(
    "typ,instance_of",
    [(typing.Union[int, str], (int, str)), (typing.Optional[int], (int, type(None)))],
)
def test_specialised_scalar_types(typ, instance_of):
    @given(from_type(typ))
    def inner(ex):
        assert isinstance(ex, instance_of)

    inner()


@pytest.mark.skipif(not hasattr(typing, "Type"), reason="requires this attr")
def test_typing_Type_int():
    assert from_type(typing.Type[int]).example() is int


@pytest.mark.skipif(not hasattr(typing, "Type"), reason="requires this attr")
def test_typing_Type_Union():
    @given(from_type(typing.Type[typing.Union[str, list]]))
    def inner(ex):
        assert ex in (str, list)

    inner()


@pytest.mark.parametrize(
    "typ,coll_type,instance_of",
    [
        (typing.Set[int], set, int),
        (typing.FrozenSet[int], frozenset, int),
        (typing.Dict[int, int], dict, int),
        (typing.KeysView[int], type({}.keys()), int),
        (typing.ValuesView[int], type({}.values()), int),
        (typing.List[int], list, int),
        (typing.Tuple[int], tuple, int),
        (typing.Tuple[int, ...], tuple, int),
        (typing.Iterator[int], typing.Iterator, int),
        (typing.Sequence[int], typing.Sequence, int),
        (typing.Iterable[int], typing.Iterable, int),
        (typing.Mapping[int, None], typing.Mapping, int),
        (typing.Container[int], typing.Container, int),
        (typing.NamedTuple("A_NamedTuple", (("elem", int),)), tuple, int),
    ],
)
def test_specialised_collection_types(typ, coll_type, instance_of):
    @given(from_type(typ))
    def inner(ex):
        if sys.version_info[:2] >= (3, 6):
            assume(ex)
        assert isinstance(ex, coll_type)
        assert all(isinstance(elem, instance_of) for elem in ex)

    try:
        inner()
    except (ResolutionFailed, AssertionError):
        if sys.version_info[:2] < (3, 6):
            pytest.skip("Hard-to-reproduce bug (early version of typing?)")
        raise


@pytest.mark.skipif(sys.version_info[:2] < (3, 6), reason="new addition")
def test_36_specialised_collection_types():
    @given(from_type(typing.DefaultDict[int, int]))
    def inner(ex):
        if sys.version_info[:2] >= (3, 6):
            assume(ex)
        assert isinstance(ex, collections.defaultdict)
        assert all(isinstance(elem, int) for elem in ex)
        assert all(isinstance(elem, int) for elem in ex.values())

    inner()


@pytest.mark.skipif(sys.version_info[:3] <= (3, 5, 1), reason="broken")
def test_ItemsView():
    @given(from_type(typing.ItemsView[int, int]))
    def inner(ex):
        # See https://github.com/python/typing/issues/177
        if sys.version_info[:2] >= (3, 6):
            assume(ex)
        assert isinstance(ex, type({}.items()))
        assert all(isinstance(elem, tuple) and len(elem) == 2 for elem in ex)
        assert all(all(isinstance(e, int) for e in elem) for elem in ex)

    inner()


def test_Optional_minimises_to_None():
    assert minimal(from_type(typing.Optional[int]), lambda ex: True) is None


@pytest.mark.parametrize("n", range(10))
def test_variable_length_tuples(n):
    type_ = typing.Tuple[int, ...]
    try:
        from_type(type_).filter(lambda ex: len(ex) == n).example()
    except Unsatisfiable:
        if sys.version_info[:2] < (3, 6):
            pytest.skip()
        raise


@pytest.mark.skipif(sys.version_info[:3] <= (3, 5, 1), reason="broken")
def test_lookup_overrides_defaults():
    sentinel = object()
    try:
        st.register_type_strategy(int, st.just(sentinel))

        @given(from_type(typing.List[int]))
        def inner_1(ex):
            assert all(elem is sentinel for elem in ex)

        inner_1()
    finally:
        st.register_type_strategy(int, st.integers())
        st.from_type.__clear_cache()

    @given(from_type(typing.List[int]))
    def inner_2(ex):
        assert all(isinstance(elem, int) for elem in ex)

    inner_2()


def test_register_generic_typing_strats():
    # I don't expect anyone to do this, but good to check it works as expected
    try:
        # We register sets for the abstract sequence type, which masks subtypes
        # from supertype resolution but not direct resolution
        st.register_type_strategy(
            typing.Sequence, types._global_type_lookup[typing.Set]
        )

        @given(from_type(typing.Sequence[int]))
        def inner_1(ex):
            assert isinstance(ex, set)

        @given(from_type(typing.Container[int]))
        def inner_2(ex):
            assert not isinstance(ex, typing.Sequence)

        @given(from_type(typing.List[int]))
        def inner_3(ex):
            assert isinstance(ex, list)

        inner_1()
        inner_2()
        inner_3()
    finally:
        types._global_type_lookup.pop(typing.Sequence)
        st.from_type.__clear_cache()


def if_available(name):
    try:
        return getattr(typing, name)
    except AttributeError:
        return pytest.param(name, marks=[pytest.mark.skip])


@pytest.mark.parametrize(
    "typ",
    [
        typing.Sequence,
        typing.Container,
        typing.Mapping,
        typing.Reversible,
        typing.SupportsBytes,
        typing.SupportsAbs,
        typing.SupportsComplex,
        typing.SupportsFloat,
        typing.SupportsInt,
        typing.SupportsRound,
        if_available("SupportsIndex"),
    ],
)
def test_resolves_weird_types(typ):
    from_type(typ).example()


@pytest.mark.parametrize(
    "var,expected",
    [
        (typing.TypeVar("V"), object),
        (typing.TypeVar("V", bound=int), int),
        (typing.TypeVar("V", int, str), (int, str)),
    ],
)
@given(data=st.data())
def test_typevar_type_is_consistent(data, var, expected):
    strat = st.from_type(var)
    v1 = data.draw(strat)
    v2 = data.draw(strat)
    assume(v1 != v2)  # Values may vary, just not types
    assert type(v1) == type(v2)
    assert isinstance(v1, expected)


def annotated_func(a: int, b: int = 2, *, c: int, d: int = 4):
    return a + b + c + d


def test_issue_946_regression():
    # Turned type hints into kwargs even if the required posarg was passed
    st.builds(annotated_func, st.integers()).example()


@pytest.mark.parametrize(
    "thing",
    [
        annotated_func,  # Works via typing.get_type_hints
        typing.NamedTuple("N", [("a", int)]),  # Falls back to inspection
        int,  # Fails; returns empty dict
    ],
)
def test_can_get_type_hints(thing):
    assert isinstance(get_type_hints(thing), dict)


def test_force_builds_to_infer_strategies_for_default_args():
    # By default, leaves args with defaults and minimises to 2+4=6
    assert minimal(st.builds(annotated_func), lambda ex: True) == 6
    # Inferring integers() for args makes it minimise to zero
    assert minimal(st.builds(annotated_func, b=infer, d=infer), lambda ex: True) == 0


def non_annotated_func(a, b=2, *, c, d=4):
    pass


def test_cannot_pass_infer_as_posarg():
    with pytest.raises(InvalidArgument):
        st.builds(annotated_func, infer).example()


def test_cannot_force_inference_for_unannotated_arg():
    with pytest.raises(InvalidArgument):
        st.builds(non_annotated_func, a=infer, c=st.none()).example()
    with pytest.raises(InvalidArgument):
        st.builds(non_annotated_func, a=st.none(), c=infer).example()


class UnknownType(object):
    def __init__(self, arg):
        pass


class UnknownAnnotatedType(object):
    def __init__(self, arg: int):
        pass


@given(st.from_type(UnknownAnnotatedType))
def test_builds_for_unknown_annotated_type(ex):
    assert isinstance(ex, UnknownAnnotatedType)


def unknown_annotated_func(a: UnknownType, b=2, *, c: UnknownType, d=4):
    pass


def test_raises_for_arg_with_unresolvable_annotation():
    with pytest.raises(ResolutionFailed):
        st.builds(unknown_annotated_func).example()
    with pytest.raises(ResolutionFailed):
        st.builds(unknown_annotated_func, a=st.none(), c=infer).example()


@given(a=infer, b=infer)
def test_can_use_type_hints(a: int, b: float):
    assert isinstance(a, int) and isinstance(b, float)


def test_error_if_has_unresolvable_hints():
    @given(a=infer)
    def inner(a: UnknownType):
        pass

    with pytest.raises(InvalidArgument):
        inner()


@pytest.mark.skipif(not hasattr(typing, "NewType"), reason="test for NewType")
def test_resolves_NewType():
    typ = typing.NewType("T", int)
    nested = typing.NewType("NestedT", typ)
    uni = typing.NewType("UnionT", typing.Optional[int])
    assert isinstance(from_type(typ).example(), integer_types)
    assert isinstance(from_type(nested).example(), integer_types)
    assert isinstance(from_type(uni).example(), integer_types + (type(None),))


E = enum.Enum("E", "a b c")


@given(from_type(E))
def test_resolves_enum(ex):
    assert isinstance(ex, E)


@pytest.mark.skipif(not hasattr(enum, "Flag"), reason="test for Flag")
@pytest.mark.parametrize("resolver", [from_type, st.sampled_from])
def test_resolves_flag_enum(resolver):
    # Storing all combinations takes O(2^n) memory.  Using an enum of 52
    # members in this test ensures that we won't try!
    F = enum.Flag("F", " ".join(string.ascii_letters))
    # Filter to check that we can generate compound members of enum.Flags

    @given(resolver(F).filter(lambda ex: ex not in tuple(F)))
    def inner(ex):
        assert isinstance(ex, F)

    inner()


class AnnotatedTarget(object):
    def __init__(self, a: int, b: int):
        pass

    def method(self, a: int, b: int):
        pass


@pytest.mark.parametrize("target", [AnnotatedTarget, AnnotatedTarget(1, 2).method])
@pytest.mark.parametrize(
    "args,kwargs",
    [
        ((), {}),
        ((1,), {}),
        ((1, 2), {}),
        ((), dict(a=1)),
        ((), dict(b=2)),
        ((), dict(a=1, b=2)),
    ],
)
def test_required_args(target, args, kwargs):
    # Mostly checking that `self` (and only self) is correctly excluded
    st.builds(
        target, *map(st.just, args), **{k: st.just(v) for k, v in kwargs.items()}
    ).example()


AnnotatedNamedTuple = typing.NamedTuple("AnnotatedNamedTuple", [("a", str)])


@given(st.builds(AnnotatedNamedTuple))
def test_infers_args_for_namedtuple_builds(thing):
    assert isinstance(thing.a, str)


@given(st.from_type(AnnotatedNamedTuple))
def test_infers_args_for_namedtuple_from_type(thing):
    assert isinstance(thing.a, str)


@given(st.builds(AnnotatedNamedTuple, a=st.none()))
def test_override_args_for_namedtuple(thing):
    assert thing.a is None


@pytest.mark.parametrize(
    "thing", [typing.Optional, typing.List, getattr(typing, "Type", typing.Set)]
)  # check Type if it's available, otherwise Set is redundant but harmless
def test_cannot_resolve_bare_forward_reference(thing):
    with pytest.raises(InvalidArgument):
        t = thing["int"]
        if type(getattr(t, "__args__", [None])[0]) != ForwardRef:
            assert sys.version_info[:2] == (3, 5)
            pytest.xfail("python 3.5 typing module is really weird")
        st.from_type(t).example()


class Tree:
    def __init__(self, left: typing.Optional["Tree"], right: typing.Optional["Tree"]):
        self.left = left
        self.right = right

    def __repr__(self):
        return "Tree({}, {})".format(self.left, self.right)


def test_resolving_recursive_type():
    try:
        assert isinstance(st.builds(Tree).example(), Tree)
    except ResolutionFailed:
        assert sys.version_info[:2] == (3, 5)
        pytest.xfail("python 3.5 typing module may not resolve annotations")
    except TypeError:
        # TypeError raised if typing.get_type_hints(Tree.__init__) fails; see
        # https://github.com/HypothesisWorks/hypothesis-python/issues/1074
        assert sys.version_info[:2] == (3, 5)
        pytest.skip("Could not find type hints to resolve")


@given(from_type(typing.Tuple[()]))
def test_resolves_empty_Tuple_issue_1583_regression(ex):
    # See e.g. https://github.com/python/mypy/commit/71332d58
    assert ex == ()


def test_can_register_NewType():
    Name = typing.NewType("Name", str)
    st.register_type_strategy(Name, st.just("Eric Idle"))
    assert st.from_type(Name).example() == "Eric Idle"


@given(st.from_type(typing.Callable))
def test_resolves_bare_callable_to_function(f):
    val = f()
    assert val is None
    with pytest.raises(TypeError):
        f(1)


@given(st.from_type(typing.Callable[[str], int]))
def test_resolves_callable_with_arg_to_function(f):
    val = f("1")
    assert isinstance(val, int)


@given(st.from_type(typing.Callable[..., int]))
def test_resolves_ellipses_callable_to_function(f):
    val = f()
    assert isinstance(val, int)
    f(1)
    f(1, 2, 3)
    f(accepts_kwargs_too=1)


class AbstractFoo(abc.ABC):
    @abc.abstractmethod
    def foo(self):
        pass


class ConcreteFoo(AbstractFoo):
    def foo(self):
        pass


@given(st.from_type(AbstractFoo))
def test_can_resolve_abstract_class(instance):
    assert isinstance(instance, ConcreteFoo)
    instance.foo()


class AbstractBar(abc.ABC):
    @abc.abstractmethod
    def bar(self):
        pass


@fails_with(ResolutionFailed)
@given(st.from_type(AbstractBar))
def test_cannot_resolve_abstract_class_with_no_concrete_subclass(instance):
    assert False, "test body unreachable as strategy cannot resolve"
