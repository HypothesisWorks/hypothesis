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

import pytest

from tests.common.utils import raises, capture_out
from hypothesis.internal.compat import print_unicode
from hypothesis.tests.cover.test_stateful import bad_machines


@pytest.mark.parametrize(
    u'machine',
    bad_machines, ids=[t.__name__ for t in bad_machines]
)
def test_bad_machines_fail(machine):
    test_class = machine.TestCase
    try:
        with capture_out() as o:
            with raises(AssertionError):
                test_class().runTest()
    except Exception:
        print_unicode(o.getvalue())
        raise
    v = o.getvalue()
    print_unicode(v)
    steps = [l for l in v.splitlines() if 'Step ' in l or 'state.' in l]
    assert 1 <= len(steps) <= 50
