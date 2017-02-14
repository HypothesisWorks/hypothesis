# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2016 David R. MacIver
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

from hypothesis.internal.conjecture.data import Status, StopTest, \
    ConjectureData


def bogus_dist(dist, n):
    assert False


def test_notes_repr():
    x = ConjectureData.for_buffer(b'')
    x.note(b'hi')
    assert repr(b'hi') in x.output


def test_can_mark_interesting():
    x = ConjectureData.for_buffer(bytes())
    with pytest.raises(StopTest):
        x.mark_interesting()
    assert x.frozen
    assert x.status == Status.INTERESTING


def test_can_mark_invalid():
    x = ConjectureData.for_buffer(bytes())
    with pytest.raises(StopTest):
        x.mark_invalid()
    assert x.frozen
    assert x.status == Status.INVALID
