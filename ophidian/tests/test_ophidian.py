# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

import pytest

from ophidian.finder import find_pythons
from ophidian.core import Ophidian

SYSTEM_PYTHONS = list(find_pythons())


def test_finds_pythons():
    ophidian = Ophidian()
    assert list(ophidian.pythons()) == SYSTEM_PYTHONS
    assert list(ophidian.pythons()) == SYSTEM_PYTHONS


N = len(SYSTEM_PYTHONS)


@pytest.mark.parametrize('n', sorted({
    0, 1, N // 2, N - 1, N
}))
def test_can_stop_and_resume(n):
    ophidian = Ophidian()

    p = ophidian.pythons()
    for _ in range(n):
        next(p)

    assert list(ophidian.pythons()) == SYSTEM_PYTHONS
