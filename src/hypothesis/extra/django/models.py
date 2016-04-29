# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

import django.db.models as dm
from django.db import IntegrityError

import hypothesis.strategies as st
import hypothesis.extra.fakefactory as ff
from hypothesis.errors import InvalidArgument
from hypothesis.extra.datetime import datetimes
from hypothesis.utils.conventions import UniqueIdentifier
from hypothesis.searchstrategy.strategies import SearchStrategy


class ModelNotSupported(Exception):
    pass


def referenced_models(model, seen=None):
    if seen is None:
        seen = set()
    for f in model._meta.concrete_fields:
        if isinstance(f, dm.ForeignKey):
            t = f.rel.to
            if t not in seen:
                seen.add(t)
                referenced_models(t, seen)
    return seen


__default_field_mappings = None


def field_mappings():
    global __default_field_mappings

    if __default_field_mappings is None:
        __default_field_mappings = {
            dm.SmallIntegerField: st.integers(-32768, 32767),
            dm.IntegerField: st.integers(-2147483648, 2147483647),
            dm.BigIntegerField:
                st.integers(-9223372036854775808, 9223372036854775807),
            dm.PositiveIntegerField: st.integers(0, 2147483647),
            dm.PositiveSmallIntegerField: st.integers(0, 32767),
            dm.BinaryField: st.binary(),
            dm.BooleanField: st.booleans(),
            dm.CharField: st.text(),
            dm.TextField: st.text(),
            dm.DateTimeField: datetimes(allow_naive=False),
            dm.EmailField: ff.fake_factory(u'email'),
            dm.FloatField: st.floats(),
            dm.NullBooleanField: st.one_of(st.none(), st.booleans()),
        }
    return __default_field_mappings


def add_default_field_mapping(field_type, strategy):
    field_mappings()[field_type] = strategy


default_value = UniqueIdentifier(u'default_value')


def models(model, **extra):
    result = {}
    mappings = field_mappings()
    mandatory = set()
    for f in model._meta.concrete_fields:
        if isinstance(f, dm.AutoField):
            continue
        try:
            mapped = mappings[type(f)]
        except KeyError:
            if not f.null:
                mandatory.add(f.name)
            continue
        if f.null:
            mapped = st.one_of(st.none(), mapped)
        result[f.name] = mapped
    missed = {x for x in mandatory if x not in extra}
    if missed:
        raise InvalidArgument((
            u'Missing arguments for mandatory field%s %s for model %s' % (
                u's' if len(missed) > 1 else u'',
                u', '.join(missed),
                model.__name__,
            )))
    result.update(extra)
    # Remove default_values so we don't try to generate anything for those.
    result = {k: v for k, v in result.items() if v is not default_value}
    return ModelStrategy(model, result)


class ModelStrategy(SearchStrategy):

    def __init__(self, model, mappings):
        super(ModelStrategy, self).__init__()
        self.model = model
        self.arg_strategy = st.fixed_dictionaries(mappings)

    def __repr__(self):
        return u'ModelStrategy(%s)' % (self.model.__name__,)

    def do_draw(self, data):
        try:
            result, _ = self.model.objects.get_or_create(
                **self.arg_strategy.do_draw(data)
            )
            return result
        except IntegrityError:
            data.mark_invalid()
