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

import math
import time
import signal

from hypothesis import settings as Settings
from hypothesis.core import find
from hypothesis.internal.reflection import proxies


class Timeout(BaseException):
    pass


class CatchableTimeout(Exception):
    pass

try:
    signal.SIGALRM
    # The tests here have a tendency to run away with themselves a it if
    # something goes wrong, so we use a relatively hard kill timeout.

    def timeout(seconds=1, catchable=False):
        def decorate(f):
            @proxies(f)
            def wrapped(*args, **kwargs):
                start = time.time()

                def handler(signum, frame):
                    if catchable:
                        raise CatchableTimeout(
                            u'Timed out after %.2fs' % (time.time() - start))
                    else:
                        raise Timeout(
                            u'Timed out after %.2fs' % (time.time() - start))

                old_handler = signal.signal(signal.SIGALRM, handler)
                signal.alarm(int(math.ceil(seconds)))
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


def minimal(
        definition, condition=None,
        settings=None, timeout_after=10, random=None
):
    settings = Settings(
        settings,
        max_examples=50000,
        max_iterations=100000,
        max_shrinks=5000,
        database=None,
        timeout=timeout_after,
    )

    condition = condition or (lambda x: True)

    @timeout(timeout_after * 1.20)
    def run():
        return find(
            definition,
            condition,
            settings=settings,
            random=random,
        )
    return run()
