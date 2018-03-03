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

import re
import string
from decimal import Decimal
from datetime import timedelta

import django.db.models as dm
from django.db import IntegrityError
from django.conf import settings as django_settings
from django.core import validators
from django.core.exceptions import ValidationError

import hypothesis.strategies as st
from hypothesis import reject
from hypothesis.errors import InvalidArgument
from hypothesis.extra.pytz import timezones
from hypothesis.provisional import emails, ip4_addr_strings, \
    ip6_addr_strings
from hypothesis.utils.conventions import UniqueIdentifier


def get_tz_strat():
    if getattr(django_settings, 'USE_TZ', False):
        return timezones()
    return st.none()


__default_field_mappings = None


def field_mappings():
    global __default_field_mappings

    if __default_field_mappings is None:
        # Sized fields are handled in _get_strategy_for_field()
        # URL fields are not yet handled
        __default_field_mappings = {
            dm.SmallIntegerField: st.integers(-32768, 32767),
            dm.IntegerField: st.integers(-2147483648, 2147483647),
            dm.BigIntegerField:
                st.integers(-9223372036854775808, 9223372036854775807),
            dm.PositiveIntegerField: st.integers(0, 2147483647),
            dm.PositiveSmallIntegerField: st.integers(0, 32767),
            dm.BinaryField: st.binary(),
            dm.BooleanField: st.booleans(),
            dm.DateField: st.dates(),
            dm.DateTimeField: st.datetimes(timezones=get_tz_strat()),
            dm.DurationField: st.timedeltas(),
            dm.EmailField: emails(),
            dm.FloatField: st.floats(),
            dm.NullBooleanField: st.one_of(st.none(), st.booleans()),
            dm.TimeField: st.times(timezones=get_tz_strat()),
            dm.UUIDField: st.uuids(),
        }

        # SQLite does not support timezone-aware times, or timedeltas that
        # don't fit in six bytes of microseconds, so we override those
        db = getattr(django_settings, 'DATABASES', {}).get('default', {})
        if db.get('ENGINE', '').endswith('.sqlite3'):  # pragma: no branch
            sqlite_delta = timedelta(microseconds=2 ** 47 - 1)
            __default_field_mappings.update({
                dm.TimeField: st.times(),
                dm.DurationField: st.timedeltas(-sqlite_delta, sqlite_delta),
            })

    return __default_field_mappings


def add_default_field_mapping(field_type, strategy):
    field_mappings()[field_type] = strategy


default_value = UniqueIdentifier(u'default_value')


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


def _get_strategy_for_field(f):
    if f.choices:
        choices = []
        for value, name_or_optgroup in f.choices:
            if isinstance(name_or_optgroup, (list, tuple)):
                choices.extend(key for key, _ in name_or_optgroup)
            else:
                choices.append(value)
        if isinstance(f, (dm.CharField, dm.TextField)) and f.blank:
            choices.insert(0, u'')
        strategy = st.sampled_from(choices)
    elif type(f) == dm.SlugField:
        strategy = st.text(alphabet=string.ascii_letters + string.digits,
                           min_size=(None if f.blank else 1),
                           max_size=f.max_length)
    elif type(f) == dm.GenericIPAddressField:
        lookup = {'both': ip4_addr_strings() | ip6_addr_strings(),
                  'ipv4': ip4_addr_strings(), 'ipv6': ip6_addr_strings()}
        strategy = lookup[f.protocol.lower()]
    elif type(f) in (dm.TextField, dm.CharField):
        strategy = st.text(
            alphabet=st.characters(blacklist_characters=u'\x00',
                                   blacklist_categories=('Cs',)),
            min_size=(None if f.blank else 1),
            max_size=f.max_length,
        )
        # We can infer a vastly more precise strategy by considering the
        # validators as well as the field type.  This is a minimal proof of
        # concept, but we intend to leverage the idea much more heavily soon.
        # See https://github.com/HypothesisWorks/hypothesis-python/issues/1116
        re_validators = [
            v for v in f.validators
            if isinstance(v, validators.RegexValidator) and not v.inverse_match
        ]
        if re_validators:
            regexes = [re.compile(v.regex, v.flags) if isinstance(v.regex, str)
                       else v.regex for v in re_validators]
            # This strategy generates according to one of the regexes, and
            # filters using the others.  It can therefore learn to generate
            # from the most restrictive and filter with permissive patterns.
            # Not maximally efficient, but it makes pathological cases rarer.
            # If you want a challenge: extend https://qntm.org/greenery to
            # compute intersections of the full Python regex language.
            strategy = st.one_of(*[st.from_regex(r) for r in regexes])
    elif type(f) == dm.DecimalField:
        bound = Decimal(10 ** f.max_digits - 1) / (10 ** f.decimal_places)
        strategy = st.decimals(min_value=-bound, max_value=bound,
                               places=f.decimal_places)
    else:
        strategy = field_mappings().get(type(f), st.nothing())
    if f.validators:
        strategy = strategy.filter(validator_to_filter(f))
    if f.null:
        strategy = st.one_of(st.none(), strategy)
    return strategy


def models(model, **field_strategies):
    """Return a strategy for examples of ``model``.

    .. warning::
        Hypothesis creates saved models. This will run inside your testing
        transaction when using the test runner, but if you use the dev console
        this will leave debris in your database.

    ``model`` must be an subclass of :class:`~django:django.db.models.Model`.
    Strategies for fields may be passed as keyword arguments, for example
    ``is_staff=st.just(False)``.

    Hypothesis can often infer a strategy based the field type and validators
    - for best results, make sure your validators are derived from Django's
    and therefore have the known types and attributes.
    Passing a keyword argument skips inference for that field; pass a strategy
    or pass :const:`hypothesis.extra.django.models.default_value` to skip
    inference for that field.

    Foreign keys are not automatically derived. If they're nullable they will
    default to always being null, otherwise you always have to specify them.
    For example, examples of a Shop type with a foreign key to Company could
    be generated with::

      shop_strategy = models(Shop, company=models(Company))
    """
    result = {k: v for k, v in field_strategies.items()
              if v is not default_value}
    missed = []
    for f in model._meta.concrete_fields:
        if not (f.name in field_strategies or isinstance(f, dm.AutoField)):
            result[f.name] = _get_strategy_for_field(f)
            if result[f.name].is_empty:
                missed.append(f.name)
    if missed:
        raise InvalidArgument(
            u'Missing arguments for mandatory field%s %s for model %s'
            % (u's' if missed else u'', u', '.join(missed), model.__name__))
    return _models_impl(st.builds(model.objects.get_or_create, **result))


@st.composite
def _models_impl(draw, strat):
    """Handle the nasty part of drawing a value for models()"""
    try:
        return draw(strat)[0]
    except IntegrityError:
        reject()
