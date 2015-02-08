# coding=utf-8

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function, unicode_literals, division

# END HEADER

from hypothesis import Verifier
from hypothesis.settings import Settings
from random import Random
import pytest


def test_verifier_explodes_when_you_mix_random_and_derandom():
    settings = Settings(derandomize=True)
    with pytest.raises(ValueError):
        Verifier(settings=settings, random=Random())
