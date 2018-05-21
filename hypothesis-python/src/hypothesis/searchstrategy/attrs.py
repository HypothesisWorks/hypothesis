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

from functools import reduce
from itertools import chain
from collections import defaultdict

import attr

import hypothesis.strategies as st
from hypothesis.errors import ResolutionFailed
from hypothesis.internal.compat import get_type_hints
from hypothesis.utils.conventions import infer


def from_attrs(target, args, kwargs, to_infer):
    fields = attr.fields(target)
    kwargs = {k: v for k, v in kwargs.items() if v is not infer}
    for name in to_infer:
        kwargs[name] = from_attrs_attribute(getattr(fields, name))
    # TODO: add a layer here that retries drawing if validation fails, for
    # improved composition.  Precedent: timezones for datetimes().
    return st.tuples(st.tuples(*args), st.fixed_dictionaries(kwargs)).map(
        lambda value: target(*value[0], **value[1])
    )


def from_attrs_attribute(attrib):
    """Infer a strategy from an attr.Attribute object."""
    # Various things we know.  Updated below, then inferred to a strategy
    base = st.nothing()  # updated to none() if None is a possibility
    default = st.nothing()  # A strategy for the default value, if any
    in_collections = []  # list of in_ validator collections to sample from
    # value must be instance of all these types or tuples thereof
    types = defaultdict(list)  # maps type to list of locations, for error msgs

    # Try inferring from the default argument
    if isinstance(attrib.default, attr.Factory):
        if not getattr(attrib.default, 'takes_self', False):  # new in 17.1
            default = st.builds(attrib.default.factory)
    elif attrib.default is not attr.NOTHING:
        default = st.just(attrib.default)

    # Try inferring from the field type
    if getattr(attrib, 'type', None) is not None:
        types[attrib.type].append('type')

    # Try inferring from the converter, if any
    converter = getattr(attrib, 'converter', None)
    if isinstance(converter, type):
        # Could this ever work but give incorrect inference?
        types[converter].append('converter')
    elif callable(converter):
        hints = get_type_hints(converter)
        if 'return' in hints:
            types[hints['return']].append('converter')

    # Try inferring type or exact values from attrs provided validators
    if attrib.validator is not None:
        validator = attrib.validator
        if isinstance(validator, attr.validators._OptionalValidator):
            base, validator = st.none(), validator.validator
        if isinstance(validator, attr.validators._AndValidator):
            vs = validator._validators
        else:
            vs = [validator]
        for v in vs:
            if isinstance(v, attr.validators._InValidator):
                if isinstance(v.options, string_types):
                    in_collections.append(list(all_substrings(v.options)))
                else:
                    in_collections.append(v.options)
            elif isinstance(v, attr.validators._InstanceOfValidator):
                types[v.type].append('instance_of')

    # Get the valid values to sample, or empty strat
    sample = st.one_of(*map(st.sampled_from, in_collections))
    if len(in_collections) >= 2:
        # Note: not exhaustive if in_ members are strings (dubious upstream).
        # See https://github.com/python-attrs/attrs/issues/382
        sample = st.sampled_from(list(ordered_intersection(in_collections)))

    # Derive a strategy from the observed types, if that's an improvement.
    # Note to future contributors: tempting to filter the in_ values based on
    # type; bad ideas as we try a few extra things to get a usable type hint.
    type_strat = st.nothing()
    if types and not in_collections:
        type_tuples = [k if isinstance(k, tuple) else (k,) for k in types]
        type_strat = st.one_of(
            *map(st.from_type, ordered_intersection(type_tuples))
        )

    strat = base | default | sample | type_strat
    if strat.is_empty:
        raise ResolutionFailed(
            'Cannot infer a strategy from the default, vaildator, type, or '
            'converter for %r' % (attrib,))
    return strat


def ordered_intersection(in_):
    assert in_
    intersection = reduce(set.intersection, in_, set(in_[0]))
    for x in chain.from_iterable(in_):
        if x in intersection:
            yield x
            intersection.remove(x)


def all_substrings(s):
    """Generate all substrings of `s`, in order of length then occurrence.
    Includes the empty string (first), and any duplicates that are present.

    >>> list(all_substrings('010'))
    ['', '0', '1', '0', '01', '10', '010']
    """
    yield s[:0]
    for n, _ in enumerate(s):
        for i in range(len(s) - n):
            yield s[i:i + n + 1]
