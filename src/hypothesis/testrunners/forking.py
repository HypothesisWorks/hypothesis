# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import os
import pickle
import inspect
import traceback
from unittest import TestCase
from collections import namedtuple

from hypothesis.errors import AbnormalExit
from hypothesis.reporting import with_reporter, current_reporter
from hypothesis.internal.conjecture.data import TestData, uniform
from hypothesis.internal.reflection import proxies
from hypothesis.executors import TestRunner
from random import Random


try:
    os.fork
except AttributeError:  # pragma: no cover
    raise ImportError(
        u'hypothesis.testrunner.forking is only available on '
        u'platforms with fork.'
    )


Report = namedtuple(u'Report', (u'data',))
Error = namedtuple(u'Error', (u'exception',))
MethodCall = namedtuple('MethodCall', ('name', 'args', 'kwargs'))
PropertyAccess = namedtuple('PropertyAccess', ('name', ))


def method_proxy(base):
    @proxies(base)
    def proxy(self, *args, **kwargs):
        return self._call_remote_method(base.__name__, *args, **kwargs)
    return proxy


class StaticDistribution(object):
    def __init__(self, buffer):
        self.buffer = buffer

    def __call__(self, random, n):
        assert n == len(self.buffer)
        return self.buffer


def is_picklable(distribution):
    try:
        return distribution.__hypothesis_forking_is_picklable
    except AttributeError:
        pass

    try:
        pickle.dumps(distribution)
        picklable = True
    except (pickle.PicklingError, AttributeError):
        picklable = False
    try:
        distribution.__hypothesis_forking_is_picklable = picklable
    except AttributeError:
        pass
    return picklable


class RemoteData(TestData):
    def __init__(self, child_reader, child_writer):
        # Note: Deliberately not calling parent init.
        # I'm a terrible person, but if you're reading this file you already
        # knew that.
        self.child_reader = child_reader
        self.child_writer = child_writer
        self.random = Random()

    def _call_remote_method(self, name, *args, **kwargs):
        try:
            pickle.dump(
                MethodCall(name, args, kwargs),
                self.child_writer,
            )
            self.child_writer.flush()
            failed, result = pickle.load(self.child_reader)
            if failed:
                raise result
            else:
                return result
        except BrokenPipeError:
            os._exit(0)

    def __getattr__(self, name):
        try:
            pickle.dump(
                PropertyAccess(name),
                self.child_writer,
            )
            self.child_writer.flush()
            failed, result = pickle.load(self.child_reader)
        except BrokenPipeError:
            os._exit(0)
        if failed:
            raise result
        else:
            return result

    def draw_bytes(self, n, distribution=uniform):
        if is_picklable(distribution):
            return self._call_remote_method('draw_bytes', n, distribution)
        else:
            distribution_result = distribution(self.random, n)
            return self._call_remote_method(
                'draw_bytes', n, StaticDistribution(distribution_result))


reserved = set([
    'draw', 'draw_bytes', '__init__',
])

for k, v in TestData.__dict__.items():
    if k not in reserved and inspect.isfunction(v):
        setattr(RemoteData, k, method_proxy(v))


def report_to(w):  # pragma: no cover
    def writer(s):
        pickle.dump(Report(s), w)
        w.flush()
    return writer


class ForkingTestCase(TestCase, TestRunner):

    """ForkingTestcase lets you write tests such that Hypothesis will run each
    example in a subprocess.

    This is useful when using Hypothesis to test C programs, because it
    means that segfaults and assertion errors do not take down the whole
    program.

    Note that this will not work correctly with coverage. This might be fixable
    but it's not currently obvious how.

    """

    def hypothesis_execute_example_with_data(self, data, function):
        _r, _w = os.pipe()
        parent_read = os.fdopen(_r, 'rb')
        child_write = os.fdopen(_w, 'wb')
        _r, _w = os.pipe()

        child_read = os.fdopen(_r, 'rb')
        parent_write = os.fdopen(_w, 'wb')

        pid = os.fork()
        if not pid:  # pragma: no cover
            succeeded = False
            try:
                parent_read.close()
                parent_write.close()

                remote_data = RemoteData(
                    child_reader=child_read, child_writer=child_write
                )

                with with_reporter(report_to(child_write)):
                    function(remote_data)
                    succeeded = True
            except BaseException as e:
                try:
                    pickle.dump(Error(e), child_write)
                    child_write.close()
                    child_read.close()
                except:
                    traceback.print_exc()
            finally:
                if succeeded:
                    os._exit(0)
                else:
                    os._exit(1)
        child_write.close()
        child_read.close()
        error = None
        try:
            while True:
                message = pickle.load(parent_read)
                if isinstance(message, MethodCall):
                    try:
                        failed, result = False, getattr(data, message.name)(
                            *message.args, **message.kwargs)
                    except Exception as e:
                        failed, result = True, e
                    pickle.dump((failed, result), parent_write)
                    parent_write.flush()
                elif isinstance(message, PropertyAccess):
                    try:
                        failed, result = False, getattr(data, message.name)
                    except Exception as e:
                        failed, result = True, e
                    pickle.dump((failed, result), parent_write)
                    parent_write.flush()
                elif isinstance(message, Report):
                    current_reporter()(message.data)
                else:
                    assert isinstance(message, Error)
                    error = message.exception
                    break
        except EOFError:
            pass
        finally:
            parent_read.close()

        if error is not None:
            raise error
        _, exitstatus = os.waitpid(pid, 0)
        if exitstatus:
            raise AbnormalExit()
