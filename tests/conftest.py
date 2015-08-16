# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import gc
import warnings
from tempfile import mkdtemp

import pytest
from hypothesis import Settings
from hypothesis.settings import set_hypothesis_home_dir

warnings.filterwarnings(u'error', category=UnicodeWarning)

set_hypothesis_home_dir(mkdtemp())

Settings.default.timeout = -1
Settings.default.strict = True


@pytest.fixture(scope=u'function', autouse=True)
def some_fixture():
    gc.collect()
