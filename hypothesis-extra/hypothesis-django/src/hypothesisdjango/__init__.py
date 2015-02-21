# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals


def load():
    from hypothesis.extra import load_entry_points
    load_entry_points('hypothesisfakefactory')
    load_entry_points('hypothesisdatetime')
    from hypothesis.extra.django.models import define_model_strategy
    from hypothesis.strategytable import StrategyTable
    import django.db.models as dm
    StrategyTable.default().define_specification_for_classes(
        define_model_strategy, subclasses_of=dm.Model
    )
