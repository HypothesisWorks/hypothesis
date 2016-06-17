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

import string
from decimal import Decimal
from functools import wraps, partial

from django.db import models as dm
from django.db import router, transaction, IntegrityError
from django.db.utils import DataError
from django.core.exceptions import ValidationError

from hypothesis import strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.extra.datetime import dates, datetimes, times
from hypothesis.extra.fakefactory import fake_factory
from hypothesis.searchstrategy.strategies import SearchStrategy
from hypothesis.strategies import defines_strategy


@defines_strategy
def model_text(alphabet=st.characters(blacklist_characters='\x00',
                                      blacklist_categories=('Cs',)), **kwargs):
    """A modified text strategy that plays nicer with Django databases.

    - Excludes the null character, which results in field truncation
      in Postgres.

    """
    return st.text(alphabet=alphabet, **kwargs)


# Field strategies.

_field_mappings = {}


def add_default_field_mapping(field_type, strategy=None):
    """Registers a strategy or strategy factory as the default handler for a
    Django model field type."""
    # Allow use as a decorator.
    if strategy is None:
        return partial(add_default_field_mapping, field_type)
    # Allow use directly.
    _field_mappings[field_type] = strategy
    # Return the strategy, to complete usage as a decorator.
    return strategy


@add_default_field_mapping(dm.AutoField)
@defines_strategy
def default_value(field):
    """A strategy that returns the default value for the field."""
    return st.just(field.get_default())


def validator_to_filter(field):
    """Creates a filter for the given field that filters out values that do not
    pass field validation."""
    def validate(value):
        try:
            field.run_validators(value)
            return True
        except ValidationError:
            return False
    return validate


def defines_field_strategy(func):
    """
    Decorates the given field strategy factory to add support for:

    - Fields with choices.
    - Null fields.
    - Filtering by field validators.

    """
    @defines_strategy
    @wraps(func)
    def create_field_strategy(field, **kwargs):
        # Handle field choices.
        if field.choices:
            choices = [
                value
                for (value, name)
                in field.choices
            ]
            if field.blank and field.empty_strings_allowed:
                choices.extend(u'')
            strategy = st.sampled_from(choices)
        else:
            # Run the factory function.
            strategy = func(field, **kwargs)
        # Add in null values.
        if field.null:
            strategy = st.one_of(st.none(), strategy)
        # Filter by validators.
        strategy = strategy.filter(validator_to_filter(field))
        return strategy
    return create_field_strategy


def _simple_field_strategy(func, **defaults):
    @defines_field_strategy
    def create_simple_field_strategy(field, **kwargs):
        params = defaults.copy()
        params.update(kwargs)
        return func(**params)
    return create_simple_field_strategy


def _fake_factory_field_strategy(strategy_name):
    @defines_field_strategy
    def create_fake_factory_field_strategy(field, min_size=None,
                                           max_size=None):
        strategy = fake_factory(strategy_name)
        # Emulate blank.
        if field.blank and field.empty_strings_allowed:
            strategy = st.one_of(strategy, u'')
        # Emulate min size.
        if min_size is not None:
            strategy = strategy.filter(lambda v: len(v) >= min_size)
        # Emulate max size.
        if max_size is not None:
            strategy = strategy.filter(lambda v: len(v) <= max_size)
        # All done!
        return strategy
    return create_fake_factory_field_strategy


big_integer_field_values = _simple_field_strategy(
    st.integers,
    min_value=-9223372036854775808,
    max_value=9223372036854775807,
)
add_default_field_mapping(dm.BigIntegerField, big_integer_field_values)


binary_field_values = _simple_field_strategy(st.binary)
add_default_field_mapping(dm.BinaryField, binary_field_values)


boolean_field_values = _simple_field_strategy(st.booleans)
add_default_field_mapping(dm.BooleanField, boolean_field_values)


@add_default_field_mapping(dm.CharField)
@add_default_field_mapping(dm.TextField)
@defines_field_strategy
def char_field_values(field, **kwargs):
    """A strategy of valid values for the given CharField."""
    if not field.blank:
        kwargs.setdefault('min_size', 1)
    if field.max_length:
        kwargs.setdefault('max_size', field.max_length)
    return model_text(**kwargs)


date_field_values = _simple_field_strategy(dates)
add_default_field_mapping(dm.DateField, date_field_values)


datetime_field_values = _simple_field_strategy(
    datetimes,
    allow_naive=False,
)
add_default_field_mapping(dm.DateTimeField, datetime_field_values)


@add_default_field_mapping(dm.DecimalField)
@defines_field_strategy
def decimal_field_values(field, **kwargs):
    """A strategy of valid values for the given DecimalField."""
    m = 10 ** field.max_digits - 1
    div = 10 ** field.decimal_places
    q = Decimal('1.' + ('0' * field.decimal_places))
    kwargs.setdefault('min_value', -m)
    kwargs.setdefault('max_value', m)
    return (st.integers(**kwargs)
            .map(lambda n: (Decimal(n) / div).quantize(q)))


email_field_values = _fake_factory_field_strategy(u'email')
add_default_field_mapping(dm.EmailField, email_field_values)


float_field_values = _simple_field_strategy(st.floats)
add_default_field_mapping(dm.FloatField, float_field_values)


integer_field_values = _simple_field_strategy(
    st.integers,
    min_value=-2147483648,
    max_value=2147483647,
)
add_default_field_mapping(dm.IntegerField, integer_field_values)


null_boolean_field_values = _simple_field_strategy(
    partial(st.one_of, st.none(), st.booleans()),
)
add_default_field_mapping(dm.NullBooleanField, null_boolean_field_values)


positive_integer_field_values = _simple_field_strategy(
    st.integers,
    min_value=0,
    max_value=2147483647,
)
add_default_field_mapping(
    dm.PositiveIntegerField,
    positive_integer_field_values,
)


positive_small_integer_field_values = _simple_field_strategy(
    st.integers,
    min_value=0,
    max_value=32767,
)
add_default_field_mapping(
    dm.PositiveSmallIntegerField,
    positive_small_integer_field_values,
)


slug_field_values = partial(
    char_field_values,
    alphabet=string.digits + string.ascii_letters + '-',
)
add_default_field_mapping(dm.SlugField, slug_field_values)


small_integer_field_values = _simple_field_strategy(
    st.integers,
    min_value=-32768,
    max_value=32767,
)
add_default_field_mapping(dm.SmallIntegerField, small_integer_field_values)


time_field_values = _simple_field_strategy(
    times,
    timezones=(),
)
add_default_field_mapping(dm.TimeField, time_field_values)


url_field_values = _fake_factory_field_strategy(u'uri')
add_default_field_mapping(dm.URLField, url_field_values)


class UnmappedFieldError(Exception):
    pass


def _resolve_strategy_factory(strategy, *args, **kwargs):
    if callable(strategy):
        return strategy(*args, **kwargs)
    return strategy


def _field_has_default(field):
    return ((field.blank and field.empty_strings_allowed) or
            field.null or field.has_default())


@defines_strategy
def field_values(field, **kwargs):
    """A strategy of valid values for the given field."""
    try:
        strategy = _field_mappings[type(field)]
    except KeyError:
        # Fallback field handlers.
        if _field_has_default(field):
            strategy = default_value
        else:
            raise UnmappedFieldError(field)
    strategy = _resolve_strategy_factory(strategy, field, **kwargs)
    return strategy


@defines_strategy
def optional_field_values(field, strategy, default_bias=0.9):
    """Modifies the strategy to produce the default field value in
    default_bias percent of examples."""
    return (st.floats(min_value=0.0, max_value=1.0)
            .flatmap(lambda v: (
                default_value(field)
                if v < default_bias
                else strategy
            )))


# Model strategies.

@defines_strategy
def models(model, __db=st.none(), __default_bias=0.9, **field_strategies):
    # Allow strategy factories.
    field_strategies = {
        field_name: _resolve_strategy_factory(
            strategy,
            model._meta.get_field(field_name),
        )
        for field_name, strategy
        in field_strategies.items()
    }
    # Introspect model for extra fields.
    for field in model._meta.concrete_fields:
        # Don't override developer choices.
        if field.name in field_strategies:
            continue
        # Get the mapped field strategy.
        strategy = field_values(field)
        # Apply default bias.
        if _field_has_default(field):
            strategy = optional_field_values(field, strategy, __default_bias)
        # Store generated field strategy.
        field_strategies[field.name] = strategy
    # Create the model data.
    model_data_strategy = st.fixed_dictionaries(field_strategies)
    return ModelStrategy(model, __db, model_data_strategy)


class ModelStrategy(SearchStrategy):

    def __init__(self, model, db, model_data_strategy):
        super(ModelStrategy, self).__init__()
        self.model = model
        self.db = db
        self.model_data_strategy = model_data_strategy

    def __repr__(self):
        return u'ModelStrategy(%s)' % (self.model.__name__,)

    def do_draw(self, data):
        try:
            model_data = data.draw(self.model_data_strategy)
        except UnmappedFieldError as ex:
            raise InvalidArgument(
                u'Missing argument for mandatory field {model}.{field}'
                .format(
                    model=self.model.__name__,
                    field=ex.args[0].name,
                )
            )
        model_data = {
            field_name: field_value
            for field_name, field_value
            in model_data.items()
            # Remove None AutoFields from the model data, since these
            # will change with every instance and mess up the get_or_create
            # functionality.
            if field_value is not None or not isinstance(
                self.model._meta.get_field(field_name),
                dm.AutoField,
            )
        }
        try:
            # We need to wrap the model create in an atomic block, so
            # we need to use the correct write database for the model.
            db = data.draw(self.db) or router.db_for_write(self.model)
            # If the save gives an IntegrityError, this will roll the
            # savepoint back.
            with transaction.atomic(using=db):
                # Try to get the identical model first. This is needed
                # for example() calls, which expect to be able to call the
                # strategy idempotently. We don't use get_or_create because
                # we want to call full_clean() before save, and there's
                # no worry about race conditions in tests.
                try:
                    obj = self.model._default_manager.get(**model_data)
                except self.model.DoesNotExist:
                    # Create the model inside the transaction, just in case it
                    # performs database actions in __init__.
                    obj = self.model(**model_data)
                    # This should catch unique checks, plus any other custom
                    # validation on the model.
                    obj.full_clean()
                    obj.save(using=db)
            return obj
        except (DataError, ValidationError, IntegrityError) as ex:
            # DataError: Something weird happened. For example,
            # some Postgres database encodings will refuse text that
            # is longer than a VARCHAR *once encoded by the database*.
            # ValidationError/IntegrityError: Validation failed. Hopefully
            # this won't filter out too much data.
            print(ex)
            pass
        # No model could be created.
        data.mark_invalid()
