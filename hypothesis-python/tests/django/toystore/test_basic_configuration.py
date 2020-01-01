# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

from unittest import TestCase as VanillaTestCase

import pytest
from django.db import IntegrityError
from django.test import TestCase as DjangoTestCase

from hypothesis import HealthCheck, Verbosity, given, settings
from hypothesis.errors import InvalidArgument
from hypothesis.extra.django import TestCase, TransactionTestCase
from hypothesis.internal.compat import PYPY
from hypothesis.strategies import integers
from tests.django.toystore.models import Company


class SomeStuff:
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(integers())
    def test_is_blank_slate(self, unused):
        Company.objects.create(name="MickeyCo")

    def test_normal_test_1(self):
        Company.objects.create(name="MickeyCo")

    def test_normal_test_2(self):
        Company.objects.create(name="MickeyCo")


class TestConstraintsWithTransactions(SomeStuff, TestCase):
    pass


if not PYPY:
    # xfail
    # This is excessively slow in general, but particularly on pypy. We just
    # disable it altogether there as it's a niche case.
    class TestConstraintsWithoutTransactions(SomeStuff, TransactionTestCase):
        pass


class TestWorkflow(VanillaTestCase):
    def test_does_not_break_later_tests(self):
        def break_the_db(i):
            Company.objects.create(name="MickeyCo")
            Company.objects.create(name="MickeyCo")

        class LocalTest(TestCase):
            @given(integers().map(break_the_db))
            @settings(
                suppress_health_check=HealthCheck.all(), verbosity=Verbosity.quiet
            )
            def test_does_not_break_other_things(self, unused):
                pass

            def test_normal_test_1(self):
                Company.objects.create(name="MickeyCo")

        t = LocalTest("test_normal_test_1")
        try:
            t.test_does_not_break_other_things()
        except IntegrityError:
            pass
        t.test_normal_test_1()

    def test_given_needs_hypothesis_test_case(self):
        class LocalTest(DjangoTestCase):
            @given(integers())
            def tst(self, i):
                assert False, "InvalidArgument should be raised in @given"

        with pytest.raises(InvalidArgument):
            LocalTest("tst").tst()
