# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

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
        'hypothesis.testrunner.forking is only available on '
        'platforms with fork.'
    )


Report = namedtuple('Report', ('data',))
Error = namedtuple('Error', ('exception',))


def report_to(w):  # pragma: no cover
    def writer(s):
        pickle.dump(Report(s), w)
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
        r = os.fdopen(r, 'rb')
        w = os.fdopen(w, 'wb')
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
