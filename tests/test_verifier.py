# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from random import Random

import pytest
from hypothesis import Verifier
from hypothesis.settings import Settings


def test_verifier_explodes_when_you_mix_random_and_derandom():
    settings = Settings(derandomize=True)
    with pytest.raises(ValueError):
        Verifier(settings=settings, random=Random())
