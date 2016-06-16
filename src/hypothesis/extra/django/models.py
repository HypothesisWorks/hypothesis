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


import string
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.utils import DataError
from django.db import models as dm, transaction, router, IntegrityError
from functools import wraps, partial
from hypothesis import strategies as st, assume
from hypothesis.errors import InvalidArgument
from hypothesis.extra.datetime import datetimes
from hypothesis.extra.fakefactory import fake_factory
from hypothesis.utils.conventions import UniqueIdentifier


default_value = UniqueIdentifier(u'default_value')


def model_text(alphabet=st.characters(blacklist_characters="\x00",
               blacklist_categories=("Cs",)), **kwargs):
    """
    A modified text strategy that plays nicer with Django databases.

    - Excludes the null character, which results in field truncation
      in Postgres.
    """
    return st.text(alphabet=alphabet, **kwargs)


# Field strategies.

_field_mappings = {
    dm.AutoField: default_value,
}


def add_default_field_mapping(field_type, strategy):
    _field_mappings[field_type] = strategy


def validator_to_filter(field):
    def validate(value):
        try:
            field.run_validators(value)
            return True
        except ValidationError:
            return False
    return validate


def field_strategy(*field_types):
    """
    Decorates the given field strategy factory to add support for:

    - Passing in min_size and max_size kwargs for the field.
    - Blank fields.
    - Null fields.
    - Filtering by field validators.

    The field strategy is registered for the given fields.
    """
    def decorator(func):
        @wraps(func)
        def create_field_strategy(field, **kwargs):
            # Handle field choices.
            if field.choices:
                choices = [
                    value
                    for (value, name)
                    in field.get_choices(include_blank=field.blank)
                ]
                strategy = st.sampled_from(choices)
            else:
                # Run the factory function.
                strategy = func(field, **kwargs)
            # Add in null values.
            if field.null:
                strategy = st.one_of(strategy, st.none())
            # Filter by validators.
            strategy = strategy.filter(validator_to_filter(field))
            return strategy
        for field_type in field_types:
            add_default_field_mapping(field_type, create_field_strategy)
        return create_field_strategy
    return decorator


def _simple_field_strategy(*field_types):
    def decorator(func, **defaults):
        @field_strategy(*field_types)
        def create_simple_field_strategy(field, **kwargs):
            params = defaults.copy()
            params.update(kwargs)
            return func(**params)
        return create_simple_field_strategy
    return decorator


def _fake_factory_field_strategy(*field_types):
    def decorator(strategy_name):
        @field_strategy(*field_types)
        def create_fake_factory_field_strategy(field, min_size=None,
                                               max_size=None):
            strategy = fake_factory(strategy_name)
            # Add in blank values.
            if field.blank:
                strategy = st.one_of(strategy, st.just(u""))
            # Emulate min size.
            if min_size is not None:
                strategy = strategy.filter(lambda v: len(v) >= min_size)
            # Emulate max size.
            if max_size is not None:
                strategy = strategy.filter(lambda v: len(v) <= max_size)
            return strategy
        return create_fake_factory_field_strategy
    return decorator


big_integer_field_values = _simple_field_strategy(dm.BigIntegerField)(
    st.integers,
    min_value=-9223372036854775808,
    max_value=9223372036854775807,
)


binary_field_values = _simple_field_strategy(dm.BinaryField)(st.binary)


boolean_field_values = _simple_field_strategy(dm.BooleanField)(st.booleans)


char_field_values = _simple_field_strategy(
    dm.CharField,
    dm.TextField,
)(model_text)


@field_strategy(dm.CharField, dm.TextField)
def char_field_values(field, **kwargs):
    if field.blank:
        kwargs.setdefault("min_size", 0)
    if field.max_length:
        kwargs.setdefault("max_size", field.max_length)
    return model_text(**kwargs)


datetime_field_values = _simple_field_strategy(dm.DateTimeField)(
    datetimes,
    allow_naive=False,
)


@field_strategy(dm.DecimalField)
def decimal_field_values(field, **kwargs):
    """
    A strategy of valid values for the given decimal field.
    """
    m = 10 ** field.max_digits - 1
    div = 10 ** field.decimal_places
    q = Decimal('1.' + ('0' * field.decimal_places))
    kwargs.setdefault("min_value", -m)
    kwargs.setdefault("max_value", m)
    return (st.integers(**kwargs)
            .map(lambda n: (Decimal(n) / div).quantize(q)))


email_field_values = _fake_factory_field_strategy(dm.EmailField)(u"email")


float_field_values = _fake_factory_field_strategy(dm.FloatField)(st.floats)


integer_field_values = _simple_field_strategy(dm.IntegerField)(
    st.integers,
    min_value=-2147483648,
    max_value=2147483647,
)


null_boolean_field_values = _simple_field_strategy(dm.NullBooleanField)(
    partial(st.one_of, st.none(), st.booleans()),
)


positive_integer_field_values = _simple_field_strategy(
    dm.PositiveIntegerField,
)(
    st.integers,
    min_value=0,
    max_value=2147483647,
)


positive_small_integer_field_values = _simple_field_strategy(
    dm.PositiveSmallIntegerField,
)(
    st.integers,
    min_value=0,
    max_value=32767,
)


slug_field_values = _simple_field_strategy(dm.SlugField)(
    model_text,
    alphabet=string.digits + string.ascii_letters + "-",
)


small_integer_field_values = _simple_field_strategy(dm.SmallIntegerField)(
    st.integers,
    min_value=-32768,
    max_value=32767,
),


url_field_values = _fake_factory_field_strategy(dm.URLField)(u"uri"),


class UnmappedFieldError(Exception):
    pass


def field_values(field, **kwargs):
    """
    A strategy of valid values for the given field.
    """
    try:
        strategy = _field_mappings[type(field)]
    except KeyError:
        # Fallback field handlers.
        if field.null:
            return st.none()
        else:
            raise UnmappedFieldError(field)
    else:
        # Allow strategy factories.
        if callable(strategy):
            strategy = strategy(field, **kwargs)
    return strategy


# Model strategies.

def models(model, _db=None, _minimal=False, **field_strategies):
    for field in model._meta.concrete_fields:
        # Don't override developer choices.
        if field.name in field_strategies:
            continue
        # If in minimal mode, do not generate unnecessary data.
        if _minimal:
            if field.blank or field.null or field.has_default():
                continue
        # Get the mapped field strategy.
        try:
            strategy = field_values(field)
        except UnmappedFieldError:
            raise InvalidArgument(
                u"Missing argument for mandatory field {model}.{field}"
                .format(
                    model=model.__name__,
                    field=field.name,
                )
            )
        field_strategies[field.name] = strategy
    # Remove default_values so we don't try to generate anything for those.
    field_strategies = {
        field_name: strategy
        for field_name, strategy
        in field_strategies.items()
        if strategy is not default_value
    }
    # Create the model data.
    model_data_strategy = st.fixed_dictionaries(field_strategies)
    _db = _db or router.db_for_write(model)

    def _create_model(model_data):
        # Create the model.
        obj = model(**model_data)
        # We need to wrap the model create in an atomic block, which means we
        # need to use the correct write database for the model.
        try:
            # This should catch unique checks, plus any other custom
            # validation on the model.
            obj.full_clean()
            # If the save gives an IntegrityError, this will roll the
            # savepoint back.
            with transaction.atomic(using=_db):
                obj.save(using=_db)
            return obj
        except (ValidationError, IntegrityError, DataError):
            # ValidationError: The full_clean failed.
            # IntegrityError: A unique key was violated.
            # DataError: Something weird happened. For example,
            # some Postgres database encodings will refuse text that
            # is longer than a VARCHAR *once encoded by the database*.
            assume(False)
    return model_data_strategy.map(_create_model)


minimal_models = partial(models, _minimal=True)
