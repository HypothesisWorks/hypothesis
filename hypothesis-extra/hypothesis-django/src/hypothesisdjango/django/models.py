# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import django.db.models as dm
from django.db import IntegrityError
from hypothesis.control import assume
from hypothesis.specifiers import one_of, integers_in_range
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.searchstrategy.strategies import MappedSearchStrategy, \
    strategy


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


def model_to_base_specifier(model):
    import hypothesis.extra.fakefactory as ff
    from hypothesis.extra.datetime import timezone_aware_datetime
    mappings = {
        dm.SmallIntegerField: integers_in_range(-32768, 32767),
        dm.IntegerField: integers_in_range(-2147483648, 2147483647),
        dm.BigIntegerField:
            integers_in_range(-9223372036854775808, 9223372036854775807),
        dm.PositiveIntegerField: integers_in_range(0, 2147483647),
        dm.PositiveSmallIntegerField: integers_in_range(0, 32767),
        dm.BinaryField: binary_type,
        dm.BooleanField: bool,
        dm.CharField: text_type,
        dm.DateTimeField: timezone_aware_datetime,
        dm.EmailField: ff.FakeFactory('email'),
        dm.FloatField: float,
        dm.NullBooleanField: one_of((None, bool)),
    }

    result = {}
    for f in model._meta.concrete_fields:
        if isinstance(f, dm.AutoField):
            continue
        try:
            mapped = mappings[type(f)]
        except KeyError:
            if isinstance(f, dm.ForeignKey):
                mapped = f.rel.to
                if model in referenced_models(mapped):
                    if f.null:
                        continue
                    else:
                        raise ModelNotSupported((
                            'non-nullable cycle starting %s -> %s. This is '
                            'currently not supported.'
                        ) % (model.__name__, mapped.__name__))
            elif f.null:
                continue
            else:
                raise ModelNotSupported((
                    'No mapping defined for field type %s and %s is not '
                    'nullable') % (
                    type(f).__name__, f.name
                ))
        if f.null:
            mapped = one_of((None, mapped))
        result[f.name] = mapped
    return result


class ModelStrategy(MappedSearchStrategy):

    def __init__(self, model, settings):
        self.model = model
        specifier = model_to_base_specifier(model)
        super(ModelStrategy, self).__init__(
            strategy=strategy(specifier, settings))

    def pack(self, value):
        try:
            result = self.model(**value)
            result.save()
            return result
        except IntegrityError:
            assume(False)


@strategy.extend_static(dm.Model)
def define_model_strategy(model, settings):
    return ModelStrategy(model, settings)
