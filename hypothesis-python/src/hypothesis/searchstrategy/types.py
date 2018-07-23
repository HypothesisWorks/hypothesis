# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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
import uuid
import decimal
import datetime
import fractions
import functools
import collections

import hypothesis.strategies as st
from hypothesis.errors import InvalidArgument, ResolutionFailed
from hypothesis.internal.compat import PY2, ForwardRef, abc, text_type, \
    typing_root_type


def type_sorting_key(t):
    """Minimise to None, then non-container types, then container types."""
    if not is_a_type(t):
        raise InvalidArgument('thing=%s must be a type' % (t,))
    if t is None or t is type(None):  # noqa: E721
        return (-1, repr(t))
    if not isinstance(t, type):  # pragma: no cover
        # Some generics in the typing module are not actually types in 3.7
        return (2, repr(t))
    return (int(issubclass(t, abc.Container)), repr(t))


def try_issubclass(thing, superclass):
    thing = getattr(thing, '__origin__', None) or thing
    superclass = getattr(superclass, '__origin__', None) or superclass
    try:
        return issubclass(thing, superclass)
    except (AttributeError, TypeError):  # pragma: no cover
        # Some types can't be the subject or object of an instance or
        # subclass check under Python 3.5
        return False


def is_a_type(thing):
    """Return True if thing is a type or a generic type like thing."""
    return isinstance(thing, type) or isinstance(thing, typing_root_type)


def from_typing_type(thing):
    # We start with special-case support for Union and Tuple - the latter
    # isn't actually a generic type.  Support for Callable may be added to
    # this section later.
    # We then explicitly error on non-Generic types, which don't carry enough
    # information to sensibly resolve to strategies at runtime.
    # Finally, we run a variation of the subclass lookup in st.from_type
    # among generic types in the lookup.
    import typing
    # Under 3.6 Union is handled directly in st.from_type, as the argument is
    # not an instance of `type`. However, under Python 3.5 Union *is* a type
    # and we have to handle it here, including failing if it has no parameters.
    if hasattr(thing, '__union_params__'):  # pragma: no cover
        args = sorted(thing.__union_params__ or (), key=type_sorting_key)
        if not args:
            raise ResolutionFailed('Cannot resolve Union of no types.')
        return st.one_of([st.from_type(t) for t in args])
    if getattr(thing, '__origin__', None) == tuple or \
            isinstance(thing, getattr(typing, 'TupleMeta', ())):
        elem_types = getattr(thing, '__tuple_params__', None) or ()
        elem_types += getattr(thing, '__args__', None) or ()
        if getattr(thing, '__tuple_use_ellipsis__', False) or \
                len(elem_types) == 2 and elem_types[-1] is Ellipsis:
            return st.lists(st.from_type(elem_types[0])).map(tuple)
        return st.tuples(*map(st.from_type, elem_types))
    if isinstance(thing, typing.TypeVar):
        if getattr(thing, '__bound__', None) is not None:
            return st.from_type(thing.__bound__)
        if getattr(thing, '__constraints__', None):
            return st.shared(
                st.sampled_from(thing.__constraints__),
                key='typevar-with-constraint'
            ).flatmap(st.from_type)
        # Constraints may be None or () on various Python versions.
        return st.text()  # An arbitrary type for the typevar
    # Now, confirm that we're dealing with a generic type as we expected
    if not isinstance(thing, typing_root_type):  # pragma: no cover
        raise ResolutionFailed('Cannot resolve %s to a strategy' % (thing,))
    # Parametrised generic types have their __origin__ attribute set to the
    # un-parametrised version, which we need to use in the subclass checks.
    # e.g.:     typing.List[int].__origin__ == typing.List
    mapping = {k: v for k, v in _global_type_lookup.items()
               if isinstance(k, typing_root_type) and try_issubclass(k, thing)}
    if typing.Dict in mapping:
        # The subtype relationships between generic and concrete View types
        # are sometimes inconsistent under Python 3.5, so we pop them out to
        # preserve our invariant that all examples of from_type(T) are
        # instances of type T - and simplify the strategy for abstract types
        # such as Container
        for t in (typing.KeysView, typing.ValuesView, typing.ItemsView):
            mapping.pop(t, None)
    strategies = [v if isinstance(v, st.SearchStrategy) else v(thing)
                  for k, v in mapping.items()
                  if sum(try_issubclass(k, T) for T in mapping) == 1]
    empty = ', '.join(repr(s) for s in strategies if s.is_empty)
    if empty or not strategies:  # pragma: no cover
        raise ResolutionFailed(
            'Could not resolve %s to a strategy; consider using '
            'register_type_strategy' % (empty or thing,))
    return st.one_of(strategies)


_global_type_lookup = {
    # Types with core Hypothesis strategies
    type(None): st.none(),
    bool: st.booleans(),
    int: st.integers(),
    float: st.floats(),
    complex: st.complex_numbers(),
    fractions.Fraction: st.fractions(),
    decimal.Decimal: st.decimals(),
    text_type: st.text(),
    bytes: st.binary(),
    datetime.datetime: st.datetimes(),
    datetime.date: st.dates(),
    datetime.time: st.times(),
    datetime.timedelta: st.timedeltas(),
    uuid.UUID: st.uuids(),
    tuple: st.builds(tuple),
    list: st.builds(list),
    set: st.builds(set),
    frozenset: st.builds(frozenset),
    dict: st.builds(dict),
    # Built-in types
    type: st.sampled_from([type(None), bool, int, str, list, set, dict]),
    type(Ellipsis): st.just(Ellipsis),
    type(NotImplemented): st.just(NotImplemented),
    bytearray: st.binary().map(bytearray),
    memoryview: st.binary().map(memoryview),
    # Pull requests with more types welcome!
}

if PY2:
    _global_type_lookup.update({
        int: st.integers().filter(lambda x: isinstance(x, int)),
        long: st.integers().map(long)  # noqa
    })

try:
    from hypothesis.extra.pytz import timezones
    _global_type_lookup[datetime.tzinfo] = timezones()
except ImportError:  # pragma: no cover
    pass
try:  # pragma: no cover
    import numpy as np
    from hypothesis.extra.numpy import \
        arrays, array_shapes, scalar_dtypes, nested_dtypes
    _global_type_lookup.update({
        np.dtype: nested_dtypes(),
        np.ndarray: arrays(scalar_dtypes(), array_shapes(max_dims=2)),
    })
except ImportError:  # pragma: no cover
    pass

try:
    import typing
except ImportError:  # pragma: no cover
    pass
else:
    _global_type_lookup.update({
        typing.ByteString: st.binary(),
        typing.io.BinaryIO: st.builds(io.BytesIO, st.binary()),  # type: ignore
        typing.io.TextIO: st.builds(io.StringIO, st.text()),  # type: ignore
        typing.Reversible: st.lists(st.integers()),
        typing.SupportsAbs: st.complex_numbers(),
        typing.SupportsComplex: st.complex_numbers(),
        typing.SupportsFloat: st.complex_numbers(),
        typing.SupportsInt: st.complex_numbers(),
    })

    try:
        # These aren't present in the typing module backport.
        _global_type_lookup[typing.SupportsBytes] = st.binary()
        _global_type_lookup[typing.SupportsRound] = st.complex_numbers()
    except AttributeError:  # pragma: no cover
        pass

    def register(type_, fallback=None):
        if isinstance(type_, str):
            # Use the name of generic types which are not available on all
            # versions, and the function just won't be added to the registry
            type_ = getattr(typing, type_, None)
            if type_ is None:  # pragma: no cover
                return lambda f: f

        def inner(func):
            if fallback is None:
                _global_type_lookup[type_] = func
                return func

            @functools.wraps(func)
            def really_inner(thing):
                if getattr(thing, '__args__', None) is None:
                    return fallback
                return func(thing)
            _global_type_lookup[type_] = really_inner
            return really_inner
        return inner

    @register('Type')
    def resolve_Type(thing):
        if thing.__args__ is None:
            return st.just(type)
        args = (thing.__args__[0],)
        if getattr(args[0], '__origin__', None) is typing.Union:
            args = args[0].__args__
        elif hasattr(args[0], '__union_params__'):  # pragma: no cover
            args = args[0].__union_params__
        if isinstance(ForwardRef, type):  # pragma: no cover
            # Duplicate check from from_type here - only paying when needed.
            for a in args:
                if type(a) == ForwardRef:
                    raise ResolutionFailed(
                        'thing=%s cannot be resolved.  Upgrading to '
                        'python>=3.6 may fix this problem via improvements '
                        'to the typing module.' % (thing,))
        return st.sampled_from(sorted(args, key=type_sorting_key))

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
