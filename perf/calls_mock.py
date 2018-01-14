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

import string
from time import time
from unittest.mock import MagicMock, call

import hypothesis.strategies as st
from hypothesis import given


def fut(D, nodes):
    return [D(n) for n in nodes]


@given(data=st.lists(st.text(alphabet=string.ascii_lowercase)))
def test_fut(data):
    d = MagicMock()

    fut(d, data)

    d.assert_has_calls([call(id) for id in data])


if __name__ == '__main__':
    t = time()
    test_fut()
    print('Took', time() - t)
