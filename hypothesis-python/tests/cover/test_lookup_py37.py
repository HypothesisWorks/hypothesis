# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import collections
import collections.abc
import contextlib
import re

import pytest

from hypothesis import assume, given


class Elem:
    pass


class Value:
    pass


def check(t, ex):
    assert isinstance(ex, t)
    assert all(isinstance(e, Elem) for e in ex)
    assume(ex)


@given(...)
def test_resolving_standard_tuple1_as_generic(x: tuple[Elem]):
    check(tuple, x)


@given(...)
def test_resolving_standard_tuple2_as_generic(x: tuple[Elem, Elem]):
    check(tuple, x)


@given(...)
def test_resolving_standard_tuple_variadic_as_generic(x: tuple[Elem, ...]):
    check(tuple, x)


@given(...)
def test_resolving_standard_list_as_generic(x: list[Elem]):
    check(list, x)


@given(...)
def test_resolving_standard_dict_as_generic(x: dict[Elem, Value]):
    check(dict, x)
    assert all(isinstance(e, Value) for e in x.values())


@given(...)
def test_resolving_standard_set_as_generic(x: set[Elem]):
    check(set, x)


@given(...)
def test_resolving_standard_frozenset_as_generic(x: frozenset[Elem]):
    check(frozenset, x)


@given(...)
def test_resolving_standard_deque_as_generic(x: collections.deque[Elem]):
    check(collections.deque, x)


@given(...)
def test_resolving_standard_defaultdict_as_generic(
    x: collections.defaultdict[Elem, Value],
):
    check(collections.defaultdict, x)
    assert all(isinstance(e, Value) for e in x.values())


@given(...)
def test_resolving_standard_ordered_dict_as_generic(
    x: collections.OrderedDict[Elem, Value],
):
    check(collections.OrderedDict, x)
    assert all(isinstance(e, Value) for e in x.values())


@given(...)
def test_resolving_standard_counter_as_generic(x: collections.Counter[Elem]):
    check(collections.Counter, x)
    assume(any(x.values()))  # Check that we generated at least one nonzero count


@given(...)
def test_resolving_standard_chainmap_as_generic(x: collections.ChainMap[Elem, Value]):
    check(collections.ChainMap, x)
    assert all(isinstance(e, Value) for e in x.values())


@given(...)
def test_resolving_standard_iterable_as_generic(x: collections.abc.Iterable[Elem]):
    check(collections.abc.Iterable, x)


@given(...)
def test_resolving_standard_iterator_as_generic(x: collections.abc.Iterator[Elem]):
    check(collections.abc.Iterator, x)


@given(...)
def test_resolving_standard_generator_as_generic(
    x: collections.abc.Generator[Elem, None, Value],
):
    assert isinstance(x, collections.abc.Generator)
    try:
        while True:
            e = next(x)
            assert isinstance(e, Elem)
            x.send(None)  # The generators we create don't check the send type
    except StopIteration as stop:
        assert isinstance(stop.value, Value)


@given(...)
def test_resolving_standard_reversible_as_generic(x: collections.abc.Reversible[Elem]):
    check(collections.abc.Reversible, x)


@given(...)
def test_resolving_standard_container_as_generic(x: collections.abc.Container[Elem]):
    check(collections.abc.Container, x)


@given(...)
def test_resolving_standard_collection_as_generic(x: collections.abc.Collection[Elem]):
    check(collections.abc.Collection, x)


@given(...)
def test_resolving_standard_callable_ellipsis(x: collections.abc.Callable[..., Elem]):
    assert isinstance(x, collections.abc.Callable)
    assert callable(x)
    # ... implies *args, **kwargs; as would any argument types
    assert isinstance(x(), Elem)
    assert isinstance(x(1, 2, 3, a=4, b=5, c=6), Elem)


@given(...)
def test_resolving_standard_callable_no_args(x: collections.abc.Callable[[], Elem]):
    assert isinstance(x, collections.abc.Callable)
    assert callable(x)
    # [] implies that no arguments are accepted
    assert isinstance(x(), Elem)
    with pytest.raises(TypeError):
        x(1)
    with pytest.raises(TypeError):
        x(a=1)


@given(...)
def test_resolving_standard_collections_set_as_generic(x: collections.abc.Set[Elem]):
    check(collections.abc.Set, x)


@given(...)
def test_resolving_standard_collections_mutableset_as_generic(
    x: collections.abc.MutableSet[Elem],
):
    check(collections.abc.MutableSet, x)


@given(...)
def test_resolving_standard_mapping_as_generic(x: collections.abc.Mapping[Elem, Value]):
    check(collections.abc.Mapping, x)
    assert all(isinstance(e, Value) for e in x.values())


@given(...)
def test_resolving_standard_mutable_mapping_as_generic(
    x: collections.abc.MutableMapping[Elem, Value],
):
    check(collections.abc.MutableMapping, x)
    assert all(isinstance(e, Value) for e in x.values())


@given(...)
def test_resolving_standard_sequence_as_generic(x: collections.abc.Sequence[Elem]):
    check(collections.abc.Sequence, x)


@given(...)
def test_resolving_standard_mutable_sequence_as_generic(
    x: collections.abc.MutableSequence[Elem],
):
    check(collections.abc.MutableSequence, x)


@given(...)
def test_resolving_standard_keysview_as_generic(x: collections.abc.KeysView[Elem]):
    check(collections.abc.KeysView, x)


@given(...)
def test_resolving_standard_itemsview_as_generic(
    x: collections.abc.ItemsView[Elem, Value],
):
    assert isinstance(x, collections.abc.ItemsView)
    assert all(isinstance(e, Elem) and isinstance(v, Value) for e, v in x)
    assume(x)


@given(...)
def test_resolving_standard_valuesview_as_generic(x: collections.abc.ValuesView[Elem]):
    check(collections.abc.ValuesView, x)


@pytest.mark.xfail  # Weird interaction with fixes in PR #2952
@given(...)
def test_resolving_standard_contextmanager_as_generic(
    x: contextlib.AbstractContextManager[Elem],
):
    assert isinstance(x, contextlib.AbstractContextManager)


@given(...)
def test_resolving_standard_re_match_bytes_as_generic(x: re.Match[bytes]):
    assert isinstance(x, re.Match)
    assert isinstance(x[0], bytes)


@given(...)
def test_resolving_standard_re_match_str_as_generic(x: re.Match[str]):
    assert isinstance(x, re.Match)
    assert isinstance(x[0], str)


@given(...)
def test_resolving_standard_re_pattern_bytes_as_generic(x: re.Pattern[bytes]):
    assert isinstance(x, re.Pattern)
    assert isinstance(x.pattern, bytes)


@given(...)
def test_resolving_standard_re_pattern_str_as_generic(x: re.Pattern[str]):
    assert isinstance(x, re.Pattern)
    assert isinstance(x.pattern, str)
