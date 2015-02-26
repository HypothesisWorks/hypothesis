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
from hypothesis.searchstrategy import MappedSearchStrategy, strategy
from hypothesis.internal.compat import text_type, binary_type

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


class ModelStrategy(MappedSearchStrategy):

    def pack(self, value):
        result = self.descriptor(**value)
        result.save()
        return result


@strategy.extend_static(dm.Model)
def define_model_strategy(model, settings):
    specifier = model_to_base_specifier(model)
    return ModelStrategy(
        descriptor=model, strategy=strategy(specifier, settings)
    )
