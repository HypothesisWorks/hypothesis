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

import string
from decimal import Decimal

import django.db.models as dm
from django.db import IntegrityError
from django.conf import settings as django_settings
from django.core.exceptions import ValidationError

import hypothesis.strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.extra.pytz import timezones
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


def get_datetime_strat():
    if getattr(django_settings, 'USE_TZ', False):
        return st.datetimes(timezones=timezones())
    return st.datetimes()


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
            dm.DateTimeField: get_datetime_strat(),
            dm.FloatField: st.floats(),
            dm.NullBooleanField: st.one_of(st.none(), st.booleans()),
        }
    return __default_field_mappings


def add_default_field_mapping(field_type, strategy):
    field_mappings()[field_type] = strategy


default_value = UniqueIdentifier(u'default_value')


class UnmappedFieldError(Exception):
    pass


def validator_to_filter(f):
    """Converts the field run_validators method to something suitable for use
    in filter."""

    def validate(value):
        try:
            f.run_validators(value)
            return True
        except ValidationError:
            return False

    return validate


safe_letters = string.ascii_letters + string.digits + '_-'

domains = st.builds(
    lambda x, y: '.'.join(x + [y]),
    st.lists(st.text(safe_letters, min_size=1), min_size=1), st.sampled_from([
        'com', 'net', 'org', 'biz', 'info',
    ])
)


email_domains = st.one_of(
    domains,
    st.sampled_from(['gmail.com', 'yahoo.com', 'hotmail.com'])
)

base_emails = st.text(safe_letters, min_size=1)

emails_with_plus = st.builds(
    lambda x, y: '%s+%s' % (x, y), base_emails, base_emails
)

emails = st.builds(
    lambda x, y: '%s@%s' % (x, y),
    st.one_of(base_emails, emails_with_plus), email_domains
)


def _get_strategy_for_field(f):
    if isinstance(f, dm.AutoField):
        return default_value
    elif f.choices:
        choices = [value for (value, name) in f.choices]
        if isinstance(f, (dm.CharField, dm.TextField)) and f.blank:
            choices.append(u'')
        strategy = st.sampled_from(choices)
    elif isinstance(f, dm.EmailField):
        return emails
    elif type(f) in (dm.TextField, dm.CharField):
        strategy = st.text(min_size=(None if f.blank else 1),
                           max_size=f.max_length)
    elif type(f) == dm.DecimalField:
        m = 10 ** f.max_digits - 1
        div = 10 ** f.decimal_places
        q = Decimal('1.' + ('0' * f.decimal_places))
        strategy = (
            st.integers(min_value=-m, max_value=m)
            .map(lambda n: (Decimal(n) / div).quantize(q)))
    else:
        try:
            strategy = field_mappings()[type(f)]
        except KeyError:
            if f.null:
                return None
            else:
                raise UnmappedFieldError(f)
    if f.validators:
        strategy = strategy.filter(validator_to_filter(f))
    if f.null:
        strategy = st.one_of(st.none(), strategy)
    return strategy


def models(model, **extra):
    result = {}
    mandatory = set()
    for f in model._meta.concrete_fields:
        try:
            strategy = _get_strategy_for_field(f)
        except UnmappedFieldError:
            mandatory.add(f.name)
            continue
        if strategy is not None:
            result[f.name] = strategy
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
