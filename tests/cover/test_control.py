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

import pytest

from hypothesis.errors import CleanupFailed, InvalidArgument
from hypothesis.control import note, cleanup, BuildContext, \
    current_build_context, _current_build_context
from tests.common.utils import capture_out


def test_cannot_cleanup_with_no_context():
    with pytest.raises(InvalidArgument):
        cleanup(lambda: None)
    assert _current_build_context.value is None


def test_cleanup_executes_on_leaving_build_context():
    data = []
    with BuildContext():
        cleanup(lambda: data.append(1))
        assert not data
    assert data == [1]
    assert _current_build_context.value is None


def test_can_nest_build_context():
    data = []
    with BuildContext():
        cleanup(lambda: data.append(1))
        with BuildContext():
            cleanup(lambda: data.append(2))
            assert not data
        assert data == [2]
    assert data == [2, 1]
    assert _current_build_context.value is None


def test_does_not_suppress_exceptions():
    with pytest.raises(AssertionError):
        with BuildContext():
            assert False
    assert _current_build_context.value is None


def test_suppresses_exceptions_in_teardown():
    with capture_out() as o:
        with pytest.raises(AssertionError):
            with BuildContext():
                def foo():
                    raise ValueError()
                cleanup(foo)
                assert False

    assert u'ValueError' in o.getvalue()
    assert _current_build_context.value is None


def test_runs_multiple_cleanup_with_teardown():
    with capture_out() as o:
        with pytest.raises(AssertionError):
            with BuildContext():
                def foo():
                    raise ValueError()
                cleanup(foo)

                def bar():
                    raise TypeError()
                cleanup(foo)
                cleanup(bar)
                assert False

    assert u'ValueError' in o.getvalue()
    assert u'TypeError' in o.getvalue()
    assert _current_build_context.value is None


def test_raises_error_if_cleanup_fails_but_block_does_not():
    with pytest.raises(CleanupFailed):
        with BuildContext():
            def foo():
                raise ValueError()
            cleanup(foo)
    assert _current_build_context.value is None


def test_raises_if_note_out_of_context():
    with pytest.raises(InvalidArgument):
        note('Hi')


def test_raises_if_current_build_context_out_of_context():
    with pytest.raises(InvalidArgument):
        current_build_context()


def test_current_build_context_is_current():
    with BuildContext() as a:
        assert current_build_context() is a
