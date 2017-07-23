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
import functools
import collections

import hypothesis.strategies as st
from hypothesis.errors import ResolutionFailed
from hypothesis.internal.compat import text_type, integer_types

_global_type_to_strategy_lookup = {}


@st.cacheable
def type_strategy_mapping():
    """Return a dict mapping from types to corresponding search strategies.

    Most resolutions will terminate here or in the special handling for
    generics from the typing module.

    """
    import uuid
    import decimal
    import datetime as dt
    import fractions

    known_type_strats = {
        # Types with core Hypothesis strategies
        type(None): st.none(),
        bool: st.booleans(),
        float: st.floats(),
        complex: st.complex_numbers(),
        fractions.Fraction: st.fractions(),
        decimal.Decimal: st.decimals(),
        text_type: st.text(),
        bytes: st.binary(),
        dt.datetime: st.datetimes(),
        dt.date: st.dates(),
        dt.time: st.times(),
        dt.timedelta: st.timedeltas(),
        uuid.UUID: st.uuids(),
        # Built-in types
        type: st.sampled_from([type(None), bool, int, str, list, set, dict]),
        type(Ellipsis): st.just(Ellipsis),
        type(NotImplemented): st.just(NotImplemented),
        bytearray: st.binary().map(bytearray),
        memoryview: st.binary().map(memoryview),
        # Pull requests with more types welcome!
    }
    for t in integer_types:
        known_type_strats[t] = st.integers()
    # build empty collections, as only generics know their contents
    known_type_strats.update({
        t: st.builds(t) for t in (tuple, list, set, frozenset, dict)
    })
    try:
        from hypothesis.extra.pytz import timezones
        known_type_strats[dt.tzinfo] = timezones()
    except ImportError:  # pragma: no cover
        pass
    try:  # pragma: no cover
        import numpy as np
        from hypothesis.extra.numpy import \
            arrays, array_shapes, scalar_dtypes, nested_dtypes
        known_type_strats.update({
            np.dtype: nested_dtypes(),
            np.ndarray: arrays(scalar_dtypes(), array_shapes(max_dims=2)),
        })
    except ImportError:
        pass
    return known_type_strats


def type_sorting_key(t):
    """Minimise to None, then non-container types, then container types."""
    if t is None or t is type(None):
        return -1
    return issubclass(t, collections.abc.Container)


def check_by_origin(thing, super_):
    return thing is super_ or getattr(thing, '__origin__', None) is super_


def try_issubclass(thing, maybe_superclass):
    try:
        return issubclass(thing, maybe_superclass)
    except (AttributeError, TypeError):
        # Some types can't be the subject or object of an instance or
        # subclass check, including _TypeAlias and Union
        return False


def from_typing_type(thing):
    import typing
    # `Any` and `Type` mess up our subclass lookups, so handle them first
    if thing is typing.Any:
        raise ResolutionFailed('Cannot resolve typing.Any to any strategy.')
    if check_by_origin(thing, getattr(typing, 'Type', object())):
        if thing.__args__ in (None, typing.Any):
            return st.just(type)
        return st.from_type(thing.__args__[0]).map(type)
    if check_by_origin(thing, typing.Union) or \
            (sys.version_info[:2] == (3, 5) and thing.__name__ == 'Union'):
        params = getattr(thing, '__union_params__', None) or ()
        args = getattr(thing, '__args__', None) or ()
        possible = sorted(params + args, key=type_sorting_key)
        if not possible:
            raise ResolutionFailed('Cannot resolve Union of no types.')
        return st.one_of([st.from_type(t) for t in possible])
    if isinstance(thing, typing.TypeVar):
        if getattr(thing, '__contravariant__', False):
            raise ResolutionFailed('Cannot resolve contravariant %s' % thing)
        constraints = getattr(thing, '__constraints__', ())
        if not constraints:
            return st.builds(object)
        # Pick a single constraint per run, and resolve it to a strategy
        return st.shared(st.sampled_from(constraints), key=thing
                         ).flatmap(st.from_type)
    to_match = getattr(thing, '__origin__', None) or thing
    # Of all types with a strategy, select the supertypes of this thing that
    # whose subtypes have no strategy, and return their strategic union
    mapping = dict(generic_type_strategy_mapping())
    mapping.update({k: v for k, v in _global_type_to_strategy_lookup.items()
                    if k.__module__ == 'typing'})
    mapping = {k: v for k, v in mapping.items() if try_issubclass(k, to_match)}
    if typing.Dict in mapping:
        # View types are weird - the metaclasses are subclasses of (eg)
        # Collection, but a concrete instance isn't an instance of Collection!
        for t in (typing.KeysView, typing.ValuesView, typing.ItemsView):
            mapping.pop(t, None)
    return st.one_of([v if isinstance(v, st.SearchStrategy) else v(thing)
                      for k, v in mapping.items()
                      if sum(try_issubclass(k, T) for T in mapping) == 1])


@st.cacheable
def generic_type_strategy_mapping():
    """Cache most of our generic type resolution logic.

    Requires the ``typing`` module to be importable.

    """
    try:
        import typing
    except ImportError:  # pragma: no cover
        return {}

    registry = {
        typing.ByteString: st.binary(),
        typing.io.BinaryIO: st.builds(io.BytesIO, st.binary()),
        typing.io.TextIO: st.builds(io.StringIO, st.text()),
        typing.Reversible: st.lists(st.integers()),
        typing.SupportsBytes: st.binary(),
        typing.SupportsAbs: st.complex_numbers(),
        typing.SupportsComplex: st.complex_numbers(),
        typing.SupportsFloat: st.complex_numbers(),
        typing.SupportsInt: st.complex_numbers(),
        typing.SupportsRound: st.complex_numbers(),
    }

    def register(type_, fallback=None):
        if isinstance(type_, str):
            # Use the name of generic types which are not available on all
            # versions, and the function just won't be added to the registry
            type_ = getattr(typing, type_, None)
            if type_ is None:  # pragma: no cover
                return lambda f: f

        def inner(func):
            if fallback is None:
                registry[type_] = func
                return func

            @functools.wraps(func)
            def really_inner(thing):
                if getattr(thing, '__args__', None) is None:
                    return fallback
                return func(thing)
            registry[type_] = really_inner
            return really_inner
        return inner

    @register(typing.Tuple)
    def resolve_Tuple(thing):
        # NamedTuple has special handling above due to user-defined __module__
        elem_types = getattr(thing, '__tuple_params__', None) or ()
        elem_types += getattr(thing, '__args__', None) or ()
        if getattr(thing, '__tuple_use_ellipsis__', False) or \
                len(elem_types) == 2 and elem_types[-1] is Ellipsis:
            return st.lists(st.from_type(elem_types[0])).map(tuple)
        return st.tuples(*map(st.from_type, elem_types))

    @register(typing.List, st.builds(list))
    def resolve_List(thing):
        return st.lists(st.from_type(thing.__args__[0]))

    @register(typing.Set, st.builds(set))
    def resolve_Set(thing):
        return st.sets(st.from_type(thing.__args__[0]))

    @register(typing.FrozenSet, st.builds(frozenset))
    def resolve_FrozenSet(thing):
        return st.frozensets(st.from_type(thing.__args__[0]))

    @register(typing.Dict, st.builds(dict))
    def resolve_Dict(thing):
        # If thing is a Collection instance, we need to fill in the values
        keys_vals = [st.from_type(t) for t in thing.__args__] * 2
        return st.dictionaries(keys_vals[0], keys_vals[1])

    @register('DefaultDict', st.builds(collections.defaultdict))
    def resolve_DefaultDict(thing):
        return resolve_Dict(thing).map(
            lambda d: collections.defaultdict(None, d))

    @register(typing.ItemsView, st.builds(dict).map(dict.items))
    def resolve_ItemsView(thing):
        return resolve_Dict(thing).map(dict.items)

    @register(typing.KeysView, st.builds(dict).map(dict.keys))
    def resolve_KeysView(thing):
        return st.dictionaries(st.from_type(thing.__args__[0]), st.none()
                               ).map(dict.keys)

    @register(typing.ValuesView, st.builds(dict).map(dict.values))
    def resolve_ValuesView(thing):
        return st.dictionaries(st.integers(), st.from_type(thing.__args__[0])
                               ).map(dict.values)

    @register(typing.Iterator, st.iterables(st.nothing()))
    def resolve_Iterator(thing):
        return st.iterables(st.from_type(thing.__args__[0]))

    return registry
