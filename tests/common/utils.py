# coding=utf-8

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function, unicode_literals

# END HEADER
import contextlib
import sys
from io import StringIO
from functools import wraps
import pytest


@contextlib.contextmanager
def capture_out():
    old_out = sys.stdout
    try:
        new_out = StringIO()
        sys.stdout = new_out
        yield new_out
    finally:
        sys.stdout = old_out


def fails_with(e):
    def accepts(f):
        @wraps(f)
        def inverted_test(*arguments, **kwargs):
            with pytest.raises(e):
                f(*arguments, **kwargs)
        return inverted_test
    return accepts

fails = fails_with(AssertionError)
