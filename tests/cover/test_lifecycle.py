# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2016 David R. MacIver
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

from hypothesis import strategies as st
from hypothesis import LifeCycle, given, lifecycle


def test_setup_and_teardown_are_called_on_lifecycle_hooks():
    class L(LifeCycle):
        bad = True

        def setup_example(self):
            self.bad = False

        def teardown_example(self):
            assert not self.bad
            self.bad = True
            self.torn_down = True

    l = L()

    @lifecycle(l)
    @given(st.integers())
    def test(i):
        assert not l.bad

    test()
    assert l.torn_down


def test_post_process_output():
    class L(LifeCycle):
        test_called = False

        def execute_example_output(self, output):
            if output is not None:
                self.processed = True
            else:
                assert not self.test_called

    x = L()

    @lifecycle(x)
    @given(st.integers())
    def test(i):
        x.test_called = True
        return i

    test()
    assert x.processed


def test_can_define_a_lifecycle_on_self():
    class L(LifeCycle):
        def setup_example(self):
            self.setup_called = True

        def teardown_example(self):
            assert self.setup_called
            self.teardown_called = True

    l = L()

    class Test(object):
        def hypothesis_lifecycle_definition(self):
            return l

        @given(st.integers())
        def test(self, i):
            pass
    Test().test()
    assert l.setup_called
    assert l.teardown_called
