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

import abc
import collections
import datetime
import enum
import io
import string
import sys
import typing
from numbers import Real

import pytest

from hypothesis import HealthCheck, assume, given, infer, settings, strategies as st
from hypothesis.errors import InvalidArgument, ResolutionFailed
from hypothesis.internal.compat import PYPY, get_type_hints, typing_root_type
from hypothesis.strategies import from_type
from hypothesis.strategies._internal import types
from tests.common.debug import assert_all_examples, find_any, minimal
from tests.common.utils import fails_with, temp_registered

sentinel = object()
generics = sorted(
    (
        t
        for t in types._global_type_lookup
        # We ignore TypeVar, because it is not a Generic type:
        if isinstance(t, typing_root_type) and t != typing.TypeVar
    ),
    key=str,
)
xfail_on_39 = () if sys.version_info[:2] < (3, 9) else pytest.mark.xfail


@pytest.mark.parametrize("typ", generics)
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
    elif typ is typing.Type and not isinstance(typing.Type, type):
        assert ex is type or isinstance(ex, typing.TypeVar)
    else:
        assert isinstance(ex, typ)


@pytest.mark.parametrize("typ", [typing.Any, typing.Union])
def test_does_not_resolve_special_cases(typ):
    with pytest.raises(InvalidArgument):
        from_type(typ).example()


@pytest.mark.parametrize(
    "typ,instance_of",
    [(typing.Union[int, str], (int, str)), (typing.Optional[int], (int, type(None)))],
)
@given(data=st.data())
def test_specialised_scalar_types(data, typ, instance_of):
    ex = data.draw(from_type(typ))
    assert isinstance(ex, instance_of)


def test_typing_Type_int():
    assert from_type(typing.Type[int]).example() is int


@given(from_type(typing.Type[typing.Union[str, list]]))
def test_typing_Type_Union(ex):
    assert ex in (str, list)


@pytest.mark.parametrize(
    "typ,coll_type,instance_of",
    [
        (typing.Set[int], set, int),
        (typing.FrozenSet[int], frozenset, int),
        (typing.Dict[int, int], dict, int),
        (typing.DefaultDict[int, int], collections.defaultdict, int),
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
@given(data=st.data())
def test_specialised_collection_types(data, typ, coll_type, instance_of):
    ex = data.draw(from_type(typ))
    assert isinstance(ex, coll_type)
    instances = [isinstance(elem, instance_of) for elem in ex]
    assert all(instances)
    assume(instances)  # non-empty collections without calling len(iterator)


@given(from_type(typing.DefaultDict[int, int]).filter(len))
def test_defaultdict_values_type(ex):
    assert all(isinstance(elem, int) for elem in ex.values())


@given(from_type(typing.ItemsView[int, int]).filter(len))
def test_ItemsView(ex):
    # See https://github.com/python/typing/issues/177
    assert isinstance(ex, type({}.items()))
    assert all(isinstance(elem, tuple) and len(elem) == 2 for elem in ex)
    assert all(all(isinstance(e, int) for e in elem) for elem in ex)


def test_Optional_minimises_to_None():
    assert minimal(from_type(typing.Optional[int]), lambda ex: True) is None


@pytest.mark.parametrize("n", range(10))
def test_variable_length_tuples(n):
    type_ = typing.Tuple[int, ...]
    from_type(type_).filter(lambda ex: len(ex) == n).example()


def test_lookup_overrides_defaults():
    sentinel = object()
    with temp_registered(int, st.just(sentinel)):

        @given(from_type(typing.List[int]))
        def inner_1(ex):
            assert all(elem is sentinel for elem in ex)

        inner_1()

    @given(from_type(typing.List[int]))
    def inner_2(ex):
        assert all(isinstance(elem, int) for elem in ex)

    inner_2()


def test_register_generic_typing_strats():
    # I don't expect anyone to do this, but good to check it works as expected
    with temp_registered(typing.Sequence, types._global_type_lookup[typing.Set]):
        # We register sets for the abstract sequence type, which masks subtypes
        # from supertype resolution but not direct resolution
        assert_all_examples(
            from_type(typing.Sequence[int]), lambda ex: isinstance(ex, set)
        )
        assert_all_examples(
            from_type(typing.Container[int]),
            lambda ex: not isinstance(ex, typing.Sequence),
        )
        assert_all_examples(
            from_type(typing.List[int]), lambda ex: isinstance(ex, list)
        )


def if_available(name):
    try:
        return getattr(typing, name)
    except AttributeError:
        return pytest.param(name, marks=[pytest.mark.skip])


@pytest.mark.parametrize(
    "typ",
    [
        pytest.param(typing.Sequence, marks=xfail_on_39),
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
        lambda ab: type(ab[0]) != type(ab[1]),  # noqa
    )


def test_distinct_typevars_distinct_type():
    """Ensures that two different type vars have at least one different type in their strategies."""
    A = typing.TypeVar("A")
    B = typing.TypeVar("B")
    find_any(
        st.tuples(st.from_type(A), st.from_type(B)),
        lambda ab: type(ab[0]) != type(ab[1]),  # noqa
    )


@given(st.data())
def test_same_typevars_same_type(data):
    """Ensures that single type argument will always have the same type in a single context."""
    A = typing.TypeVar("A")

    def same_type_args(a: A, b: A):
        assert type(a) == type(b)

    data.draw(st.builds(same_type_args))


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


def test_resolves_NewType():
    typ = typing.NewType("T", int)
    nested = typing.NewType("NestedT", typ)
    uni = typing.NewType("UnionT", typing.Optional[int])
    assert isinstance(from_type(typ).example(), int)
    assert isinstance(from_type(nested).example(), int)
    assert isinstance(from_type(uni).example(), (int, type(None)))


E = enum.Enum("E", "a b c")


@given(from_type(E))
def test_resolves_enum(ex):
    assert isinstance(ex, E)


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


@pytest.mark.parametrize("thing", [typing.Optional, typing.List, typing.Type])
def test_cannot_resolve_bare_forward_reference(thing):
    with pytest.raises(InvalidArgument):
        t = thing["int"]
        st.from_type(t).example()


class Tree:
    def __init__(self, left: typing.Optional["Tree"], right: typing.Optional["Tree"]):
        self.left = left
        self.right = right

    def __repr__(self):
        return "Tree({}, {})".format(self.left, self.right)


def test_resolving_recursive_type():
    assert isinstance(st.builds(Tree).example(), Tree)


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
    assert not isinstance(val, typing.ByteString)
    # Check it hasn't happened again from some other non-generic sequence type.
    for x in val:
        assert isinstance(x, set)


@pytest.mark.parametrize(
    "type_", [int, Real, object, typing.Union[int, str], typing.Union[Real, str]]
)
def test_bytestring_is_valid_sequence_of_int_and_parent_classes(type_):
    find_any(
        st.from_type(typing.Sequence[type_]),
        lambda val: isinstance(val, typing.ByteString),
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


@pytest.mark.parametrize(
    "protocol, typ",
    [
        (typing.SupportsFloat, float),
        (typing.SupportsInt, int),
        (typing.SupportsBytes, bytes),  # noqa: B1
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
    assert_all_examples(st.from_type(type_), lambda t: isinstance(t, datetime.timezone))


@pytest.mark.parametrize(
    "typ",
    [
        typing.Set[typing.Hashable],
        typing.FrozenSet[typing.Hashable],
        typing.Dict[typing.Hashable, int],
    ],
)
@settings(suppress_health_check=[HealthCheck.data_too_large])
@given(data=st.data())
def test_generic_collections_only_use_hashable_elements(typ, data):
    data.draw(from_type(typ))


def test_hashable_type_unhashable_value():
    # Decimal("snan") is not hashable; we should be able to generate it.
    # See https://github.com/HypothesisWorks/hypothesis/issues/2320
    find_any(
        from_type(typing.Hashable),
        lambda x: not types._can_hash(x),
        settings(max_examples=10 ** 5),
    )


@pytest.mark.parametrize(
    "typ,repr_",
    [
        (int, "integers()"),
        (typing.List[str], "lists(text())"),
        ("not a type", "from_type('not a type')"),
    ],
)
def test_repr_passthrough(typ, repr_):
    assert repr(st.from_type(typ)) == repr_


class TreeForwardRefs(typing.NamedTuple):
    val: int
    l: typing.Optional["TreeForwardRefs"]
    r: typing.Optional["TreeForwardRefs"]


@pytest.mark.skipif(PYPY, reason="pypy36 does not resolve the forward refs")
@given(st.builds(TreeForwardRefs))
def test_resolves_forward_references_outside_annotations(t):
    assert isinstance(t, TreeForwardRefs)
