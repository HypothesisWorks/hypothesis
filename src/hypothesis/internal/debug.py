# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import time
import signal
from functools import wraps

from hypothesis import Settings, given
from hypothesis.core import _debugging_return_failing_example


class Timeout(BaseException):
    pass


try:
    signal.SIGALRM
    # The tests here have a tendency to run away with themselves a it if
    # something goes wrong, so we use a relatively hard kill timeout.

    def timeout(seconds=1):
        def decorate(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                start = time.time()

                def handler(signum, frame):
                    raise Timeout(
                        'Timed out after %.2fs' % (time.time() - start))

                old_handler = signal.signal(signal.SIGALRM, handler)
                signal.alarm(seconds)
                try:
                    return f(*args, **kwargs)
                finally:
                    signal.signal(signal.SIGALRM, old_handler)
                    signal.alarm(0)
            return wrapped
        return decorate
except AttributeError:
    # We're on an OS with no SIGALRM. Fall back to no timeout.
    def timeout(seconds=1):
        def decorate(f):
            return f
        return decorate


quality_settings = Settings(
    max_examples=5000
)


def minimal(definition, condition=None, settings=None):
    @timeout(5)
    @given(definition, settings=settings or quality_settings)
    def everything_is_terrible(x):
        if condition is None:
            assert False
        else:
            assert not condition(x)
    try:
        everything_is_terrible()
    except AssertionError:
        pass

    with _debugging_return_failing_example.with_value(True):
        result = everything_is_terrible()
        assert result is not None
        return result[1]['x']
