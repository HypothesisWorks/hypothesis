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

from hypothesis import settings as Settings
from hypothesis.core import find


def minimal(
        definition, condition=None,
        settings=None, timeout_after=10, random=None
):
    settings = Settings(
        settings,
        max_examples=50000,
        max_iterations=100000,
        max_shrinks=5000,
        database=None,
        timeout=timeout_after,
    )

    condition = condition or (lambda x: True)

    return find(
        definition,
        condition,
        settings=settings,
        random=random,
    )
