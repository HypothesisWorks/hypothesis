# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

import threading

import hypothesis.strategies as st
from hypothesis import given


def test_can_run_given_in_thread():
    has_run_successfully = [False]

    @given(st.integers())
    def test(n):
        has_run_successfully[0] = True

    t = threading.Thread(target=test)
    t.start()
    t.join()
    assert has_run_successfully[0]
