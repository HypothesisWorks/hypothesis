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
import hypothesis.extra.fakefactory as ff
from hypothesis.descriptors import one_of
from hypothesis.extra.datetime import timezone_aware_datetime
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.internal.compat import text_type, binary_type


class DjangoSkeleton(object):

    def __init__(self, model, build_args):
        self.build_args = build_args
        self.model = model

    def build(self):
        result = self.model(**self.build_args)
        result.save()
        return result


FIELD_MAPPINGS = {
    dm.BigIntegerField: int,
    dm.BinaryField: binary_type,
    dm.BooleanField: bool,
    dm.CharField: text_type,
    dm.DateTimeField: timezone_aware_datetime,
    dm.EmailField: ff.FakeFactory('email'),
    dm.FloatField: float,
    dm.IntegerField: int,
    dm.NullBooleanField: one_of((None, bool)),
}


class ModelNotSupported(Exception):
    pass


def model_to_base_specifier(model):
    result = {}
    for f in model._meta.concrete_fields:
        if isinstance(f, dm.AutoField):
            continue
        try:
            mapped = FIELD_MAPPINGS[type(f)]
        except KeyError:
            if f.null:
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


class ModelStrategy(SearchStrategy):

    def __init__(self, model, arg_strategy):
        self.descriptor = model
        self.model = model
        self.arg_strategy = arg_strategy
        self.parameter = self.arg_strategy.parameter

    def produce_template(self, random, parameter_value):
        args = self.arg_strategy.produce_template(random, parameter_value)
        return DjangoSkeleton(
            model=self.model, build_args=args
        )

    def could_have_produced(self, value):
        return isinstance(value, DjangoSkeleton) and (
            value.model == self.model
        )

    def custom_reify(self, value):
        return value.build()


def define_model_strategy(table, descriptor):
    specifier = model_to_base_specifier(descriptor)
    base_strategy = table.specification_for(specifier)
    return ModelStrategy(
        model=descriptor, arg_strategy=base_strategy
    )
