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

import os
import sys

from ophidian.finder import find_pythons


def test_can_find_self():
    pythons = find_pythons()

    found_paths = [p.path for p in pythons]

    assert os.path.realpath(sys.executable) in found_paths


def test_does_not_duplicate_paths():
    pythons = find_pythons()

    found_paths = [p.path for p in pythons]
    assert len(set(found_paths)) == len(found_paths)
