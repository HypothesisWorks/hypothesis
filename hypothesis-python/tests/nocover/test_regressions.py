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

from __future__ import division, print_function, absolute_import

import warnings

from hypothesis.errors import HypothesisDeprecationWarning
from hypothesis._settings import note_deprecation
from hypothesis.strategies import integers, composite


def test_note_deprecation_blames_right_code_issue_652():
    msg = 'this is an arbitrary deprecation warning message'

    @composite
    def deprecated_strategy(draw):
        draw(integers())
        note_deprecation(msg)

    with warnings.catch_warnings(record=True) as log:
        warnings.simplefilter('always')
        deprecated_strategy().example()

    assert len(log) == 1
    record, = log
    # We got the warning we expected, from the right file
    assert isinstance(record.message, HypothesisDeprecationWarning)
    assert record.message.args == (msg,)
    assert record.filename == __file__
