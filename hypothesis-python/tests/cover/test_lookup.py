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
import builtins
import collections
import contextlib
import datetime
import enum
import inspect
import io
import random
import re
import string
import sys
import typing
import warnings
from dataclasses import dataclass
from inspect import signature
from numbers import Real
from typing import (
    Dict as _Dict,
    FrozenSet as _FrozenSet,
    List as _List,
    Set as _Set,
    Tuple as _Tuple,
    Type as _Type,
)

import pytest

from hypothesis import HealthCheck, assume, given, settings, strategies as st
from hypothesis.errors import InvalidArgument, ResolutionFailed, SmallSearchSpaceWarning
from hypothesis.internal.compat import get_type_hints
from hypothesis.internal.conjecture.junkdrawer import stack_depth_of_caller
from hypothesis.internal.reflection import get_pretty_function_description
from hypothesis.strategies import from_type
from hypothesis.strategies._internal import types

from tests.common.debug import (
    assert_all_examples,
    assert_no_examples,
    assert_simple_property,
    check_can_generate_examples,
    find_any,
    minimal,
)
from tests.common.utils import fails_with, temp_registered

sentinel = object()
BUILTIN_TYPES = tuple(
    v
    for v in vars(builtins).values()
    if isinstance(v, type) and v.__name__ != "BuiltinImporter"
)
generics = sorted(
    (
        t
        for t in types._global_type_lookup
        # We ignore TypeVar, because it is not a Generic type:
        if isinstance(t, types.typing_root_type)
        and t != typing.TypeVar
        and (
            sys.version_info[:2] <= (3, 11)
            or t != getattr(typing, "ByteString", object())
        )
    ),
    key=str,
)


@pytest.mark.parametrize("typ", generics, ids=repr)
@settings(
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    database=None,
)
@given(data=st.data())
def test_resolve_typing_module(data, typ):
    ex = data.draw(from_type(typ))

    if typ in (typing.BinaryIO, typing.TextIO):
        assert isinstance(ex, io.IOBase)
    elif isinstance(typ, typing._ProtocolMeta):
        pass
    elif (typing.get_origin(typ) or typ) is type and not isinstance(type, type):
        assert ex is type or isinstance(ex, typing.TypeVar)
    else:
        assert isinstance(ex, typ)


@pytest.mark.parametrize("typ", [typing.Any, typing.Union])
def test_does_not_resolve_special_cases(typ):
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(from_type(typ))


@pytest.mark.parametrize(
    "typ,instance_of",
    [(typing.Union[int, str], (int, str)), (typing.Optional[int], (int, type(None)))],
)
@given(data=st.data())
def test_specialised_scalar_types(data, typ, instance_of):
    ex = data.draw(from_type(typ))
    assert isinstance(ex, instance_of)


def test_typing_Type_int():
    for t in (type[int], type["int"], _Type[int], _Type["int"]):
        assert_simple_property(from_type(t), lambda x: x is int)


@given(
    from_type(type[typing.Union[str, list]]) | from_type(_Type[typing.Union[str, list]])
)
def test_typing_Type_Union(ex):
    assert ex in (str, list)


@pytest.mark.parametrize(
    "typ",
    [
        pytest.param(
            getattr(collections.abc, "ByteString", ...),
            marks=pytest.mark.skipif(sys.version_info[:2] >= (3, 14), reason="removed"),
        ),
        typing.Match,
        typing.Pattern,
        re.Match,
        re.Pattern,
    ],
    ids=repr,
)
@given(data=st.data())
def test_rare_types(data, typ):
    ex = data.draw(from_type(typ))
    with warnings.catch_warnings():
        if sys.version_info[:2] >= (3, 12):
            warnings.simplefilter("ignore", DeprecationWarning)
        # ByteString is deprecated in Python 3.12
        assert isinstance(ex, typ)


class Elem:
    pass


@pytest.mark.parametrize(
    "typ,coll_type",
    [
        (_Set[Elem], set),
        (_FrozenSet[Elem], frozenset),
        (_Dict[Elem, None], dict),
        (set[Elem], set),
        (frozenset[Elem], frozenset),
        # (dict[Elem, None], dict),  # FIXME this should work
        (typing.DefaultDict[Elem, None], collections.defaultdict),
        (typing.KeysView[Elem], type({}.keys())),
        (typing.ValuesView[Elem], type({}.values())),
        (_List[Elem], list),
        (_Tuple[Elem], tuple),
        (_Tuple[Elem, ...], tuple),
        (list[Elem], list),
        (tuple[Elem], tuple),
        (tuple[Elem, ...], tuple),
        (typing.Iterator[Elem], typing.Iterator),
        (typing.Sequence[Elem], typing.Sequence),
        (typing.Iterable[Elem], typing.Iterable),
        (typing.Mapping[Elem, None], typing.Mapping),
        (typing.Container[Elem], typing.Container),
        (typing.NamedTuple("A_NamedTuple", (("elem", Elem),)), tuple),
        (typing.Counter[Elem], typing.Counter),
        (typing.Deque[Elem], typing.Deque),
    ],
    ids=repr,
)
@given(data=st.data())
def test_specialised_collection_types(data, typ, coll_type):
    ex = data.draw(from_type(typ))
    assert isinstance(ex, coll_type)
    instances = [isinstance(elem, Elem) for elem in ex]
    assert all(instances)
    assume(instances)  # non-empty collections without calling len(iterator)


class ElemValue:
    pass


@pytest.mark.parametrize(
    "typ,coll_type",
    [
        (typing.ChainMap[Elem, ElemValue], typing.ChainMap),
        (typing.DefaultDict[Elem, ElemValue], typing.DefaultDict),
        (typing.OrderedDict[Elem, ElemValue], typing.OrderedDict),
    ],
    ids=repr,
)
@given(data=st.data())
def test_specialised_mapping_types(data, typ, coll_type):
    ex = data.draw(from_type(typ).filter(len))
    assert isinstance(ex, coll_type)
    instances = [isinstance(elem, Elem) for elem in ex]
    assert all(instances)
    assert all(isinstance(elem, ElemValue) for elem in ex.values())


@given(from_type(typing.ItemsView[Elem, Elem]).filter(len))
def test_ItemsView(ex):
    # See https://github.com/python/typing/issues/177
    assert isinstance(ex, type({}.items()))
    assert all(isinstance(elem, tuple) and len(elem) == 2 for elem in ex)
    assert all(all(isinstance(e, Elem) for e in elem) for elem in ex)


@pytest.mark.parametrize("generic", [typing.Match, typing.Pattern])
@pytest.mark.parametrize("typ", [bytes, str])
@given(data=st.data())
def test_regex_types(data, generic, typ):
    x = data.draw(from_type(generic[typ]))
    assert isinstance(x[0] if generic is typing.Match else x.pattern, typ)


@given(x=...)
def test_Generator(x: typing.Generator[Elem, None, ElemValue]):
    assert isinstance(x, typing.Generator)
    try:
        while True:
            e = next(x)
            assert isinstance(e, Elem)
            x.send(None)  # The generators we create don't check the send type
    except StopIteration as stop:
        assert isinstance(stop.value, ElemValue)


def test_Optional_minimises_to_None():
    assert minimal(from_type(typing.Optional[int]), lambda ex: True) is None


@pytest.mark.parametrize("n", [0, 1, 5])
@pytest.mark.parametrize("t", [tuple, _Tuple])
def test_variable_length_tuples(t, n):
    type_ = t[int, ...]
    check_can_generate_examples(from_type(type_).filter(lambda ex: len(ex) == n))


def test_lookup_overrides_defaults():
    sentinel = object()
    with temp_registered(int, st.just(sentinel)):

        @given(from_type(list[int]))
        def inner_1(ex):
            assert all(elem is sentinel for elem in ex)

        inner_1()

    @given(from_type(list[int]))
    def inner_2(ex):
        assert all(isinstance(elem, int) for elem in ex)

    inner_2()


def test_register_generic_typing_strats():
    # I don't expect anyone to do this, but good to check it works as expected
    with temp_registered(
        typing.Sequence,
        types._global_type_lookup[set],
    ):
        # We register sets for the abstract sequence type, which masks subtypes
        # from supertype resolution but not direct resolution
        assert_all_examples(
            from_type(typing.Sequence[int]), lambda ex: isinstance(ex, set)
        )
        assert_all_examples(
            from_type(typing.Container[int]),
            lambda ex: not isinstance(ex, typing.Sequence),
        )
        assert_all_examples(from_type(list[int]), lambda ex: isinstance(ex, list))


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
    ids=get_pretty_function_description,
)
def test_resolves_weird_types(typ):
    check_can_generate_examples(from_type(typ))


class Foo:
    def __init__(self, x):
        pass


class Bar(Foo):
    pass


class Baz(Foo):
    pass


st.register_type_strategy(Bar, st.builds(Bar, st.integers()))
st.register_type_strategy(Baz, st.builds(Baz, st.integers()))


@pytest.mark.parametrize(
    "var,expected",
    [
        (typing.TypeVar("V"), object),
        (typing.TypeVar("V", bound=int), int),
        (typing.TypeVar("V", bound=Foo), (Bar, Baz)),
        (typing.TypeVar("V", bound=typing.Union[int, str]), (int, str)),
        (typing.TypeVar("V", int, str), (int, str)),
    ],
)
@settings(suppress_health_check=[HealthCheck.too_slow])
@given(data=st.data())
def test_typevar_type_is_consistent(data, var, expected):
    strat = st.from_type(var)
    v1 = data.draw(strat)
    v2 = data.draw(strat)
    assume(v1 != v2)  # Values may vary, just not types
    assert type(v1) == type(v2)
    assert isinstance(v1, expected)


def test_distinct_typevars_same_constraint():
    A = typing.TypeVar("A", int, str)
    B = typing.TypeVar("B", int, str)
    find_any(
        st.tuples(st.from_type(A), st.from_type(B)),
        lambda ab: type(ab[0]) != type(ab[1]),
    )


def test_distinct_typevars_distinct_type():
    """Ensures that two different type vars have at least one different type in their strategies."""
    A = typing.TypeVar("A")
    B = typing.TypeVar("B")
    find_any(
        st.tuples(st.from_type(A), st.from_type(B)),
        lambda ab: type(ab[0]) != type(ab[1]),
    )


A = typing.TypeVar("A")


def same_type_args(a: A, b: A):
    assert type(a) == type(b)


@given(st.builds(same_type_args))
def test_same_typevars_same_type(_):
    """Ensures that single type argument will always have the same type in a single context."""


def test_typevars_can_be_redefined():
    """We test that one can register a custom strategy for all type vars."""
    A = typing.TypeVar("A")

    with temp_registered(typing.TypeVar, st.just(1)):
        assert_all_examples(st.from_type(A), lambda obj: obj == 1)


def test_typevars_can_be_redefine_with_factory():
    """We test that one can register a custom strategy for all type vars."""
    A = typing.TypeVar("A")

    with temp_registered(typing.TypeVar, lambda thing: st.just(thing.__name__)):
        assert_all_examples(st.from_type(A), lambda obj: obj == "A")


def test_typevars_can_be_resolved_conditionally():
    sentinel = object()
    A = typing.TypeVar("A")
    B = typing.TypeVar("B")

    def resolve_type_var(thing):
        assert thing in (A, B)
        if thing == A:
            return st.just(sentinel)
        return NotImplemented

    with temp_registered(typing.TypeVar, resolve_type_var):
        assert_simple_property(st.from_type(A), lambda x: x is sentinel)
        # We've re-defined the default TypeVar resolver, so there is no fallback.
        # This causes the lookup to fail.
        with pytest.raises(InvalidArgument):
            check_can_generate_examples(st.from_type(B))


def annotated_func(a: int, b: int = 2, *, c: int, d: int = 4):
    return a + b + c + d


def test_issue_946_regression():
    # Turned type hints into kwargs even if the required posarg was passed
    check_can_generate_examples(st.builds(annotated_func, st.integers()))


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
    assert minimal(st.builds(annotated_func, b=..., d=...), lambda ex: True) == 0


def non_annotated_func(a, b=2, *, c, d=4):
    pass


def test_cannot_pass_infer_as_posarg():
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(st.builds(annotated_func, ...))


def test_cannot_force_inference_for_unannotated_arg():
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(st.builds(non_annotated_func, a=..., c=st.none()))
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(st.builds(non_annotated_func, a=st.none(), c=...))


class UnknownType:
    def __init__(self, arg):
        pass


class UnknownAnnotatedType:
    def __init__(self, arg: int):
        pass


@given(st.from_type(UnknownAnnotatedType))
def test_builds_for_unknown_annotated_type(ex):
    assert isinstance(ex, UnknownAnnotatedType)


def unknown_annotated_func(a: UnknownType, b=2, *, c: UnknownType, d=4):
    pass


def test_raises_for_arg_with_unresolvable_annotation():
    with pytest.raises(ResolutionFailed):
        check_can_generate_examples(st.builds(unknown_annotated_func))
    with pytest.raises(ResolutionFailed):
        check_can_generate_examples(
            st.builds(unknown_annotated_func, a=st.none(), c=...)
        )


@given(a=..., b=...)
def test_can_use_type_hints(a: int, b: float):
    assert isinstance(a, int)
    assert isinstance(b, float)


def test_error_if_has_unresolvable_hints():
    @given(a=...)
    def inner(a: UnknownType):
        pass

    with pytest.raises(InvalidArgument):
        inner()


def test_resolves_NewType():
    typ = typing.NewType("T", int)
    nested = typing.NewType("NestedT", typ)
    uni = typing.NewType("UnionT", typing.Optional[int])
    assert_simple_property(from_type(typ), lambda x: isinstance(x, int))
    assert_simple_property(from_type(nested), lambda x: isinstance(x, int))
    assert_simple_property(from_type(uni), lambda x: isinstance(x, (int, type(None))))
    find_any(from_type(uni), lambda x: isinstance(x, int))
    find_any(from_type(uni), lambda x: isinstance(x, type(None)))


@pytest.mark.parametrize("is_handled", [True, False])
def test_resolves_NewType_conditionally(is_handled):
    sentinel = object()
    typ = typing.NewType("T", int)

    def resolve_custom_strategy(thing):
        assert thing is typ
        if is_handled:
            return st.just(sentinel)
        return NotImplemented

    with temp_registered(typ, resolve_custom_strategy):
        if is_handled:
            assert_simple_property(st.from_type(typ), lambda x: x is sentinel)
        else:
            assert_simple_property(st.from_type(typ), lambda x: isinstance(x, int))


E = enum.Enum("E", "a b c")


@given(from_type(E))
def test_resolves_enum(ex):
    assert isinstance(ex, E)


@pytest.mark.parametrize("resolver", [from_type, st.sampled_from])
def test_resolves_flag_enum(resolver):
    # Storing all combinations takes O(2^n) memory.  Using an enum of 52
    # members in this test ensures that we won't try!
    F = enum.Flag("F", " ".join(string.ascii_letters))

    # Checks for combination coverage are found in nocover/test_sampled_from
    @given(resolver(F))
    def inner(ex):
        assert isinstance(ex, F)

    inner()


class AnnotatedTarget:
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
        ((), {"a": 1}),
        ((), {"b": 2}),
        ((), {"a": 1, "b": 2}),
    ],
)
def test_required_args(target, args, kwargs):
    # Mostly checking that `self` (and only self) is correctly excluded
    check_can_generate_examples(
        st.builds(
            target, *map(st.just, args), **{k: st.just(v) for k, v in kwargs.items()}
        )
    )


class AnnotatedNamedTuple(typing.NamedTuple):
    a: str


@given(st.builds(AnnotatedNamedTuple))
def test_infers_args_for_namedtuple_builds(thing):
    assert isinstance(thing.a, str)


@given(st.from_type(AnnotatedNamedTuple))
def test_infers_args_for_namedtuple_from_type(thing):
    assert isinstance(thing.a, str)


@given(st.builds(AnnotatedNamedTuple, a=st.none()))
def test_override_args_for_namedtuple(thing):
    assert thing.a is None


@pytest.mark.parametrize("thing", [typing.Optional, list, type, _List, _Type])
def test_cannot_resolve_bare_forward_reference(thing):
    t = thing["ConcreteFoo"]
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(st.from_type(t))


class Tree:
    def __init__(self, left: typing.Optional["Tree"], right: typing.Optional["Tree"]):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Tree({self.left}, {self.right})"


@given(tree=st.builds(Tree))
def test_resolving_recursive_type(tree):
    assert isinstance(tree, Tree)


class TypedTree(typing.TypedDict):
    nxt: typing.Optional["TypedTree"]


def test_resolving_recursive_typeddict():
    assert_simple_property(
        st.from_type(TypedTree),
        lambda tree: isinstance(tree, dict) and len(tree) == 1 and "nxt" in tree,
    )


class MyList:
    def __init__(self, nxt: typing.Optional["MyList"] = None):
        self.nxt = nxt

    def __repr__(self):
        return f"MyList({self.nxt})"

    def __eq__(self, other):
        return type(self) == type(other) and self.nxt == other.nxt


@given(lst=st.from_type(MyList))
def test_resolving_recursive_type_with_defaults(lst):
    assert isinstance(lst, MyList)


def test_recursive_type_with_defaults_minimizes_to_defaults():
    assert minimal(from_type(MyList), lambda ex: True) == MyList()


class A:
    def __init__(self, nxt: typing.Optional["B"]):
        self.nxt = nxt

    def __repr__(self):
        return f"A({self.nxt})"


class B:
    def __init__(self, nxt: typing.Optional["A"]):
        self.nxt = nxt

    def __repr__(self):
        return f"B({self.nxt})"


@given(nxt=st.from_type(A))
def test_resolving_mutually_recursive_types(nxt):
    i = 0
    while nxt:
        assert isinstance(nxt, [A, B][i % 2])
        nxt = nxt.nxt
        i += 1


def test_resolving_mutually_recursive_types_with_limited_stack():
    orig_recursionlimit = sys.getrecursionlimit()
    current_stack_depth = stack_depth_of_caller()
    sys.setrecursionlimit(current_stack_depth + 100)
    try:

        @given(nxt=st.from_type(A))
        def test(nxt):
            pass

        test()
    finally:
        assert sys.getrecursionlimit() == current_stack_depth + 100
        sys.setrecursionlimit(orig_recursionlimit)


class A_with_default:
    def __init__(self, nxt: typing.Optional["B_with_default"] = None):
        self.nxt = nxt

    def __repr__(self):
        return f"A_with_default({self.nxt})"


class B_with_default:
    def __init__(self, nxt: typing.Optional["A_with_default"] = None):
        self.nxt = nxt

    def __repr__(self):
        return f"B_with_default({self.nxt})"


@given(nxt=st.from_type(A_with_default))
def test_resolving_mutually_recursive_types_with_defaults(nxt):
    # This test is required to cover the raise/except part of the recursion
    # check in from_type, see
    # https://github.com/HypothesisWorks/hypothesis/issues/3655. If the
    # skip-nondefaulted-args check is removed, this test becomes redundant.
    i = 0
    while nxt:
        assert isinstance(nxt, [A_with_default, B_with_default][i % 2])
        nxt = nxt.nxt
        i += 1


class SomeClass:
    def __init__(self, value: int, next_node: typing.Optional["SomeClass"]) -> None:
        assert value > 0
        self.value = value
        self.next_node = next_node

    def __repr__(self) -> str:
        return f"SomeClass({self.value}, next_node={self.next_node})"


def test_resolving_recursive_type_with_registered_constraint():
    with temp_registered(
        SomeClass, st.builds(SomeClass, value=st.integers(min_value=1))
    ):

        @given(s=st.from_type(SomeClass))
        def test(s):
            assert isinstance(s, SomeClass)

        test()


def test_resolving_recursive_type_with_registered_constraint_not_none():
    with temp_registered(
        SomeClass, st.builds(SomeClass, value=st.integers(min_value=1))
    ):
        s = st.from_type(SomeClass)
        print(s, s.wrapped_strategy)
        find_any(s, lambda s: s.next_node is not None)


@given(from_type(tuple[()]) | from_type(_Tuple[()]))
def test_resolves_empty_Tuple_issue_1583_regression(ex):
    # See e.g. https://github.com/python/mypy/commit/71332d58
    assert ex == ()


def test_can_register_NewType():
    Name = typing.NewType("Name", str)
    st.register_type_strategy(Name, st.just("Eric Idle"))
    assert_simple_property(st.from_type(Name), lambda x: x == "Eric Idle")


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
    raise AssertionError("test body unreachable as strategy cannot resolve")


@fails_with(ResolutionFailed)
@given(st.from_type(type["ConcreteFoo"]))
def test_cannot_resolve_type_with_forwardref(instance):
    raise AssertionError("test body unreachable as strategy cannot resolve")


@fails_with(ResolutionFailed)
@given(st.from_type(_Type["ConcreteFoo"]))
def test_cannot_resolve_type_with_forwardref_old(instance):
    raise AssertionError("test body unreachable as strategy cannot resolve")


@pytest.mark.parametrize("typ", [typing.Hashable, typing.Sized])
@given(data=st.data())
def test_inference_on_generic_collections_abc_aliases(typ, data):
    # regression test for inference bug on types that are just aliases
    # types for simple interfaces in collections abc and take no args
    # the typing module such as Hashable and Sized
    # see https://github.com/HypothesisWorks/hypothesis/issues/2272
    value = data.draw(st.from_type(typ))
    assert isinstance(value, typ)


@given(st.from_type(typing.Sequence[set]))
def test_bytestring_not_treated_as_generic_sequence(val):
    # Check that we don't fall into the specific problem from
    # https://github.com/HypothesisWorks/hypothesis/issues/2257
    assert not isinstance(val, bytes)
    # Check it hasn't happened again from some other non-generic sequence type.
    for x in val:
        assert isinstance(x, set)


@pytest.mark.skipif(sys.version_info[:2] >= (3, 14), reason="FIXME-py314")
@pytest.mark.parametrize(
    "type_", [int, Real, object, typing.Union[int, str], typing.Union[Real, str]]
)
def test_bytestring_is_valid_sequence_of_int_and_parent_classes(type_):
    find_any(
        st.from_type(typing.Sequence[type_]),
        lambda val: isinstance(val, bytes),
    )


@pytest.mark.parametrize("protocol", [typing.SupportsAbs, typing.SupportsRound])
@given(data=st.data())
def test_supportsop_types_support_protocol(protocol, data):
    # test values drawn from SupportsOp types are indeed considered instances
    # of that type.
    value = data.draw(st.from_type(protocol))
    # check that we aren't somehow generating instances of the protocol itself
    assert value.__class__ != protocol
    assert issubclass(type(value), protocol)


@pytest.mark.parametrize("restrict_custom_strategy", [True, False])
def test_generic_aliases_can_be_conditionally_resolved_by_registered_function(
    restrict_custom_strategy,
):
    # Check that a custom strategy function may provide no strategy for a
    # generic alias request like Container[T]. We test this under two scenarios:
    # - where CustomContainer CANNOT be generated from requests for Container[T]
    #   (only for requests for exactly CustomContainer[T])
    # - where CustomContainer CAN be generated from requests for Container[T]
    T = typing.TypeVar("T")

    @dataclass
    class CustomContainer(typing.Container[T]):
        content: T

        def __contains__(self, value: object) -> bool:
            return self.content == value

    def get_custom_container_strategy(thing):
        if restrict_custom_strategy and typing.get_origin(thing) != CustomContainer:
            return NotImplemented
        return st.builds(
            CustomContainer, content=st.from_type(typing.get_args(thing)[0])
        )

    with temp_registered(CustomContainer, get_custom_container_strategy):

        def is_custom_container_with_str(example):
            return isinstance(example, CustomContainer) and isinstance(
                example.content, str
            )

        def is_non_custom_container(example):
            return isinstance(example, typing.Container) and not isinstance(
                example, CustomContainer
            )

        assert_all_examples(
            st.from_type(CustomContainer[str]), is_custom_container_with_str
        )
        # If the strategy function is restricting, it doesn't return a strategy
        # for requests for Container[...], so it's never generated. When not
        # restricting, it is generated.
        if restrict_custom_strategy:
            assert_all_examples(
                st.from_type(typing.Container[str]), is_non_custom_container
            )
        else:
            find_any(st.from_type(typing.Container[str]), is_custom_container_with_str)
            find_any(st.from_type(typing.Container[str]), is_non_custom_container)


@pytest.mark.parametrize(
    "protocol, typ",
    [
        (typing.SupportsFloat, float),
        (typing.SupportsInt, int),
        (typing.SupportsBytes, bytes),
        (typing.SupportsComplex, complex),
    ],
)
@given(data=st.data())
def test_supportscast_types_support_protocol_or_are_castable(protocol, typ, data):
    value = data.draw(st.from_type(protocol))
    # check that we aren't somehow generating instances of the protocol itself
    assert value.__class__ != protocol
    # test values drawn from the protocol types either support the protocol
    # or can be cast to typ
    assert issubclass(type(value), protocol) or types.can_cast(typ, value)


def test_can_cast():
    assert types.can_cast(int, "0")
    assert not types.can_cast(int, "abc")


@pytest.mark.parametrize("type_", [datetime.timezone, datetime.tzinfo])
def test_timezone_lookup(type_):
    assert issubclass(type_, datetime.tzinfo)
    assert_all_examples(st.from_type(type_), lambda t: isinstance(t, type_))


@pytest.mark.parametrize(
    "typ",
    [
        _Set[typing.Hashable],
        _FrozenSet[typing.Hashable],
        _Dict[typing.Hashable, int],
        set[typing.Hashable],
        frozenset[typing.Hashable],
        dict[typing.Hashable, int],
    ],
)
@settings(suppress_health_check=[HealthCheck.data_too_large])
@given(data=st.data())
def test_generic_collections_only_use_hashable_elements(typ, data):
    data.draw(from_type(typ))


@given(st.sets(st.integers() | st.binary(), min_size=2))
def test_no_byteswarning(_):
    pass


def test_hashable_type_unhashable_value():
    # Decimal("snan") is not hashable; we should be able to generate it.
    # See https://github.com/HypothesisWorks/hypothesis/issues/2320
    find_any(
        from_type(typing.Hashable),
        lambda x: not types._can_hash(x),
        settings(max_examples=10**5),
    )


class _EmptyClass:
    def __init__(self, value=-1) -> None:
        pass


@pytest.mark.parametrize(
    "typ,repr_",
    [
        (int, "integers()"),
        (list[str], "lists(text())"),
        (_List[str], "lists(text())"),
        ("not a type", "from_type('not a type')"),
        (random.Random, "randoms()"),
        (_EmptyClass, "from_type(tests.cover.test_lookup._EmptyClass)"),
        (
            st.SearchStrategy[str],
            "from_type(hypothesis.strategies.SearchStrategy[str])",
        ),
    ],
)
def test_repr_passthrough(typ, repr_):
    assert repr(st.from_type(typ)) == repr_


class TreeForwardRefs(typing.NamedTuple):
    val: int
    l: typing.Optional["TreeForwardRefs"]
    r: typing.Optional["TreeForwardRefs"]


@given(st.builds(TreeForwardRefs))
def test_resolves_forward_references_outside_annotations(t):
    assert isinstance(t, TreeForwardRefs)


def constructor(a: str = None):  # noqa  # deprecated implicit optional, for testing
    pass


class WithOptionalInSignature:
    __signature__ = inspect.signature(constructor)
    __annotations__ = typing.get_type_hints(constructor)

    def __init__(self, **kwargs):
        assert set(kwargs) == {"a"}
        self.a = kwargs["a"]


def test_compat_get_type_hints_aware_of_None_default():
    # Regression test for https://github.com/HypothesisWorks/hypothesis/issues/2648
    strategy = st.builds(WithOptionalInSignature, a=...)
    find_any(strategy, lambda x: x.a is None)
    find_any(strategy, lambda x: x.a is not None)

    if sys.version_info[:2] >= (3, 11):
        # https://docs.python.org/3.11/library/typing.html#typing.get_type_hints
        assert typing.get_type_hints(constructor)["a"] == str
    else:
        assert typing.get_type_hints(constructor)["a"] == typing.Optional[str]
    assert inspect.signature(constructor).parameters["a"].annotation == str


_ValueType = typing.TypeVar("_ValueType")


class Wrapper(typing.Generic[_ValueType]):
    _inner_value: _ValueType

    def __init__(self, inner_value: _ValueType) -> None:
        self._inner_value = inner_value


@given(st.builds(Wrapper))
def test_issue_2603_regression(built):
    """It was impossible to build annotated classes with constructors."""
    assert isinstance(built, Wrapper)


class AnnotatedConstructor(typing.Generic[_ValueType]):
    value: _ValueType  # the same name we have in `__init__`

    def __init__(self, value: int) -> None:
        """By this example we show, that ``int`` is more important than ``_ValueType``."""
        assert isinstance(value, int)


@given(st.data())
def test_constructor_is_more_important(data):
    """Constructor types should take precedence over all other annotations."""
    data.draw(st.builds(AnnotatedConstructor))


def use_signature(self, value: str) -> None: ...


class AnnotatedConstructorWithSignature(typing.Generic[_ValueType]):
    value: _ValueType  # the same name we have in `__init__`

    __signature__ = signature(use_signature)

    def __init__(self, value: int) -> None:
        """By this example we show, that ``__signature__`` is the most important source."""
        assert isinstance(value, str)


def selfless_signature(value: str) -> None: ...


class AnnotatedConstructorWithSelflessSignature(AnnotatedConstructorWithSignature):
    __signature__ = signature(selfless_signature)


def really_takes_str(value: int) -> None:
    """By this example we show, that ``__signature__`` is the most important source."""
    assert isinstance(value, str)


really_takes_str.__signature__ = signature(selfless_signature)


@pytest.mark.parametrize(
    "thing",
    [
        AnnotatedConstructorWithSignature,
        AnnotatedConstructorWithSelflessSignature,
        really_takes_str,
    ],
)
def test_signature_is_the_most_important_source(thing):
    """Signature types should take precedence over all other annotations."""
    check_can_generate_examples(st.builds(thing))


class AnnotatedAndDefault:
    def __init__(self, foo: typing.Optional[bool] = None):
        self.foo = foo


def test_from_type_can_be_default_or_annotation():
    find_any(st.from_type(AnnotatedAndDefault), lambda x: x.foo is None)
    find_any(st.from_type(AnnotatedAndDefault), lambda x: isinstance(x.foo, bool))


@pytest.mark.parametrize("t", BUILTIN_TYPES, ids=lambda t: t.__name__)
def test_resolves_builtin_types(t):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SmallSearchSpaceWarning)
        assert_simple_property(st.from_type(t), lambda v: isinstance(v, t))


@pytest.mark.parametrize("t", BUILTIN_TYPES, ids=lambda t: t.__name__)
@given(data=st.data())
def test_resolves_forwardrefs_to_builtin_types(t, data):
    s = st.from_type(typing.ForwardRef(t.__name__))
    v = data.draw(s)
    assert isinstance(v, t)


@pytest.mark.parametrize("t", BUILTIN_TYPES, ids=lambda t: t.__name__)
def test_resolves_type_of_builtin_types(t):
    assert_simple_property(st.from_type(type[t.__name__]), lambda v: v is t)


@given(
    st.from_type(type[typing.Union["str", "int"]])
    | st.from_type(_Type[typing.Union["str", "int"]])
)
def test_resolves_type_of_union_of_forwardrefs_to_builtins(x):
    assert x in (str, int)


@pytest.mark.parametrize(
    # Old-style `List` because `list[int]() == list()`, so no need for the hint.
    "type_",
    [getattr(typing, "List", None)[int], typing.Optional[int]],
)
def test_builds_suggests_from_type(type_):
    with pytest.raises(
        InvalidArgument, match=re.escape(f"try using from_type({type_!r})")
    ):
        check_can_generate_examples(st.builds(type_))
    try:
        check_can_generate_examples(st.builds(type_, st.just("has an argument")))
        raise AssertionError("Expected strategy to raise an error")
    except TypeError as err:
        assert not isinstance(err, InvalidArgument)


def test_builds_mentions_no_type_check():
    @typing.no_type_check
    def f(x: int):
        pass

    msg = "@no_type_check decorator prevented Hypothesis from inferring a strategy"
    with pytest.raises(TypeError, match=msg):
        check_can_generate_examples(st.builds(f))


class TupleSubtype(tuple):
    pass


def test_tuple_subclasses_not_generic_sequences():
    # see https://github.com/HypothesisWorks/hypothesis/issues/3767.
    with temp_registered(TupleSubtype, st.builds(TupleSubtype)):
        s = st.from_type(typing.Sequence[int])
        assert_no_examples(s, lambda x: isinstance(x, tuple))


def test_custom_strategy_function_resolves_types_conditionally():
    sentinel = object()

    class A:
        pass

    class B(A):
        pass

    class C(A):
        pass

    def resolve_custom_strategy_for_b(thing):
        if thing == B:
            return st.just(sentinel)
        return NotImplemented

    with contextlib.ExitStack() as stack:
        stack.enter_context(temp_registered(B, resolve_custom_strategy_for_b))
        stack.enter_context(temp_registered(C, st.builds(C)))

        # C's strategy can be used for A, but B's cannot because its function
        # only returns a strategy for requests for exactly B.
        assert_all_examples(st.from_type(A), lambda example: type(example) == C)
        assert_all_examples(st.from_type(B), lambda example: example is sentinel)
        assert_all_examples(st.from_type(C), lambda example: type(example) == C)


class CustomInteger(int):
    def __init__(self, value: int, /) -> None:
        if not isinstance(value, int):
            raise TypeError


@given(...)
def test_from_type_resolves_required_posonly_args(n: CustomInteger):
    # st.builds() does not infer for positional arguments, but st.from_type()
    # does.  See e.g. https://stackoverflow.com/q/79199376/ for motivation.
    assert isinstance(n, CustomInteger)
