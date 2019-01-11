# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

from hypothesis import HealthCheck, given, reject, settings
from hypothesis.errors import Unsatisfiable
from hypothesis.strategies import integers
from tests.common.utils import raises


def test_contains_the_test_function_name_in_the_exception_string():
    look_for_one = settings(max_examples=1, suppress_health_check=HealthCheck.all())

    @given(integers())
    @look_for_one
    def this_has_a_totally_unique_name(x):
        reject()

    with raises(Unsatisfiable) as e:
        this_has_a_totally_unique_name()
    assert this_has_a_totally_unique_name.__name__ in e.value.args[0]

    class Foo(object):
        @given(integers())
        @look_for_one
        def this_has_a_unique_name_and_lives_on_a_class(self, x):
            reject()

    with raises(Unsatisfiable) as e:
        Foo().this_has_a_unique_name_and_lives_on_a_class()
    assert (Foo.this_has_a_unique_name_and_lives_on_a_class.__name__) in e.value.args[0]
