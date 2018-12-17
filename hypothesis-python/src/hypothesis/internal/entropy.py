# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

from __future__ import absolute_import, division, print_function

import contextlib
import random

try:
    import numpy.random as npr
except ImportError:
    npr = None


@contextlib.contextmanager
def deterministic_PRNG():
    """Context manager that handles random.seed without polluting global state.

    See issue #1255 and PR #1295 for details and motivation - in short,
    leaving the global pseudo-random number generator (PRNG) seeded is a very
    bad idea in principle, and breaks all kinds of independence assumptions
    in practice.
    """
    _random_state = random.getstate()
    random.seed(0)
    # These branches are covered by tests/numpy/, not tests/cover/
    if npr is not None:  # pragma: no cover
        _npr_state = npr.get_state()
        npr.seed(0)
    try:
        yield
    finally:
        random.setstate(_random_state)
        if npr is not None:  # pragma: no cover
            npr.set_state(_npr_state)
