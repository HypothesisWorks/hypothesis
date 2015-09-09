# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import os
import pickle
import traceback
from unittest import TestCase
from collections import namedtuple

from hypothesis.errors import AbnormalExit
from hypothesis.reporting import with_reporter, current_reporter

try:
    os.fork
except AttributeError:  # pragma: no cover
    raise ImportError(
        u'hypothesis.testrunner.forking is only available on '
        u'platforms with fork.'
    )


Report = namedtuple(u'Report', (u'data',))
Error = namedtuple(u'Error', (u'exception',))


def report_to(w):  # pragma: no cover
    def writer(s):
        pickle.dump(Report(s), w)
        w.flush()
    return writer


class ForkingTestCase(TestCase):

    """ForkingTestcase lets you write tests such that Hypothesis will run each
    example in a subprocess.

    This is useful when using Hypothesis to test C programs, because it
    means that segfaults and assertion errors do not take down the whole
    program.

    Note that this will not work correctly with coverage. This might be fixable
    but it's not currently obvious how.

    """

    def execute_example(self, function):
        r, w = os.pipe()
        r = os.fdopen(r, u'rb')
        w = os.fdopen(w, u'wb')
        pid = os.fork()
        if not pid:  # pragma: no cover
            succeeded = False
            try:
                r.close()
                with with_reporter(report_to(w)):
                    function()
                    succeeded = True
            except BaseException as e:
                try:
                    pickle.dump(Error(e), w)
                    w.close()
                except:
                    traceback.print_exc()
            finally:
                if succeeded:
                    os._exit(0)
                else:
                    os._exit(1)
        w.close()
        error = None
        try:
            while True:
                message = pickle.load(r)
                if isinstance(message, Report):
                    current_reporter()(message.data)
                else:
                    assert isinstance(message, Error)
                    error = message.exception
                    break
        except EOFError:
            pass
        finally:
            r.close()

        if error is not None:
            raise error
        _, exitstatus = os.waitpid(pid, 0)
        if exitstatus:
            raise AbnormalExit()
