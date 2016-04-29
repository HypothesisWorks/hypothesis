# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

import sys
import contextlib
from io import BytesIO, StringIO

from hypothesis.reporting import default, with_reporter
from hypothesis.internal.compat import PY2
from hypothesis.internal.reflection import proxies


@contextlib.contextmanager
def capture_out():
    old_out = sys.stdout
    try:
        new_out = BytesIO() if PY2 else StringIO()
        sys.stdout = new_out
        with with_reporter(default):
            yield new_out
    finally:
        sys.stdout = old_out


class ExcInfo(object):
    pass


@contextlib.contextmanager
def raises(exctype):
    e = ExcInfo()
    try:
        yield e
        assert False, "Expected to raise an exception but didn't"
    except exctype as err:
        e.value = err
        return


def fails_with(e):
    def accepts(f):
        @proxies(f)
        def inverted_test(*arguments, **kwargs):
            with raises(e):
                f(*arguments, **kwargs)
        return inverted_test
    return accepts

fails = fails_with(AssertionError)
