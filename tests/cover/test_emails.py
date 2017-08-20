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

import hypothesis.strategies as st
from hypothesis import given


@given(st.emails())
def test_all_emails_passes_basic_validation(email):
    local_part, at, domain = email.rpartion("@")
    labels, dot, top_level = domain.rpartion(".")

    assert at == "@"
    assert dot == "."
    assert len(local_part) >= 1
    assert len(top_level) >= 2
    assert len(labels) >= 1
