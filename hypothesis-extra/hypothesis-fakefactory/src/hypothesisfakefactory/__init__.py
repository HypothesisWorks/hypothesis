# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER


def load():
    import hypothesis.extra.fakefactory as ff
    from hypothesis.strategytable import StrategyTable
    from hypothesis.database.converter import ConverterTable
    from hypothesis.internal.compat import text_type
    StrategyTable.default().define_specification_for_instances(
        ff.FakeFactory,
        lambda s, d: ff.FakeFactoryStrategy(d)
    )
    ConverterTable.default().define_specification_for_instances(
        ff.FakeFactory,
        lambda s, d: s.specification_for(text_type)
    )
