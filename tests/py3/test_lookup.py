# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import io
import sys
import collections

import pytest

import hypothesis.strategies as st
from hypothesis import find, given, infer, assume
from hypothesis.errors import NoExamples, InvalidArgument, ResolutionFailed
from hypothesis.strategies import from_type
from hypothesis.searchstrategy import types
from hypothesis.internal.compat import get_type_hints

typing = pytest.importorskip('typing')
sentinel = object()
generics = sorted((t for t in types._global_type_lookup
                   if isinstance(t, typing.GenericMeta)), key=str)


@pytest.mark.parametrize('typ', generics)
def test_resolve_typing_module(typ):
    @given(from_type(typ))
    def inner(ex):
        if typ in (typing.BinaryIO, typing.TextIO):
            assert isinstance(ex, io.IOBase)
        elif typ is typing.Tuple:
            # isinstance is incompatible with Tuple on early 3.5
            assert ex == ()
        elif isinstance(typ, typing._ProtocolMeta):
            pass
        else:
            try:
                assert isinstance(ex, typ)
            except TypeError:
                if sys.version_info[:2] < (3, 6):
                    pytest.skip()
                raise

    inner()


@pytest.mark.parametrize('typ', [typing.Any, typing.Union])
def test_does_not_resolve_special_cases(typ):
    with pytest.raises(InvalidArgument):
        from_type(typ).example()


@pytest.mark.parametrize('typ,instance_of', [
    (typing.Union[int, str], (int, str)),
    (typing.Optional[int], (int, type(None))),
])
def test_specialised_scalar_types(typ, instance_of):
    @given(from_type(typ))
    def inner(ex):
        assert isinstance(ex, instance_of)

    inner()


@pytest.mark.skipif(not hasattr(typing, 'Type'), reason='requires this attr')
def test_typing_Type_int():
    assert from_type(typing.Type[int]).example() is int


@pytest.mark.skipif(not hasattr(typing, 'Type'), reason='requires this attr')
def test_typing_Type_Union():
    @given(from_type(typing.Type[typing.Union[str, list]]))
    def inner(ex):
        assert ex in (str, list)

    inner()


@pytest.mark.parametrize('typ,coll_type,instance_of', [
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
    (typing.NamedTuple('A_NamedTuple', (('elem', int),)), tuple, int),
])
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
            pytest.skip('Hard-to-reproduce bug (early version of typing?)')
        raise


@pytest.mark.skipif(sys.version_info[:2] < (3, 6), reason='new addition')
def test_36_specialised_collection_types():
    @given(from_type(typing.DefaultDict[int, int]))
    def inner(ex):
        if sys.version_info[:2] >= (3, 6):
            assume(ex)
        assert isinstance(ex, collections.defaultdict)
        assert all(isinstance(elem, int) for elem in ex)
        assert all(isinstance(elem, int) for elem in ex.values())

    inner()


@pytest.mark.skipif(sys.version_info[:3] <= (3, 5, 1), reason='broken')
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
    assert find(from_type(typing.Optional[int]), lambda ex: True) is None


@pytest.mark.parametrize('n', range(10))
def test_variable_length_tuples(n):
    type_ = typing.Tuple[int, ...]
    try:
        from_type(type_).filter(lambda ex: len(ex) == n).example()
    except NoExamples:
        if sys.version_info[:2] < (3, 6):
            pytest.skip()
        raise


@pytest.mark.skipif(sys.version_info[:3] <= (3, 5, 1), reason='broken')
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
            typing.Sequence,
            types._global_type_lookup[typing.Set]
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


@pytest.mark.parametrize('typ', [
    typing.Sequence, typing.Container, typing.Mapping, typing.Reversible,
    typing.SupportsBytes, typing.SupportsAbs, typing.SupportsComplex,
    typing.SupportsFloat, typing.SupportsInt, typing.SupportsRound,
])
def test_resolves_weird_types(typ):
    from_type(typ).example()


def annotated_func(a: int, b: int=2, *, c: int, d: int=4):
    return a + b + c + d


@pytest.mark.parametrize('thing', [
    annotated_func,  # Works via typing.get_type_hints
    typing.NamedTuple('N', [('a', int)]),  # Falls back to inspection
    int,  # Fails; returns empty dict
])
def test_can_get_type_hints(thing):
    assert isinstance(get_type_hints(thing), dict)


def test_force_builds_to_infer_strategies_for_default_args():
    # By default, leaves args with defaults and minimises to 2+4=6
    assert find(st.builds(annotated_func), lambda ex: True) == 6
    # Inferring integers() for args makes it minimise to zero
    assert find(st.builds(annotated_func, b=infer, d=infer),
                lambda ex: True) == 0


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


@pytest.mark.skipif(not hasattr(typing, 'NewType'), reason='test for NewType')
def test_resolves_NewType():
    for t in [
        typing.NewType('T', int),
        typing.NewType('UnionT', typing.Optional[int]),
        typing.NewType('NestedT', typing.NewType('T', int)),
    ]:
        from_type(t).example()
