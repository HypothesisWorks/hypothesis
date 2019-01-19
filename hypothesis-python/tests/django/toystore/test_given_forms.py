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

from hypothesis import assume, given
from hypothesis.extra.django import TestCase, from_form
from tests.django.toystore.forms import (  # RestrictedFieldsForm,
    AllFieldsForm,
    CustomerForm,
    DynamicForm,
    ManyNumericsForm,
    ManyTimesForm,
    OddFieldsForm,
)


class TestGetsBasicForms(TestCase):
    @given(from_form(CustomerForm))
    def test_valid_customer(self, customer_form):
        assume(customer_form.data["name"].strip())
        self.assertTrue(customer_form.is_valid())

    @given(from_form(ManyNumericsForm))
    def test_valid_numerics(self, numerics_form):
        self.assertTrue(numerics_form.is_valid())

    @given(from_form(ManyTimesForm))
    def test_valid_times(self, times_form):
        self.assertTrue(times_form.is_valid())

    @given(from_form(OddFieldsForm))
    def test_valid_odd_fields(self, odd_form):
        self.assertTrue(odd_form.is_valid())

    # # this one doesn't work right... it seems that the model field validator
    # #  doesn't get passed to the form field validator
    # @given(from_form(RestrictedFieldsForm))
    # def test_valid_restricted_fields(self, restricted_fields_form):
    #     # if not restricted_fields_form.is_valid():
    #     #     print(restricted_fields_form.errors)
    #     self.assertTrue(restricted_fields_form.is_valid())

    def test_dynamic_form(self):
        for field_count in range(2, 7):

            @given(from_form(DynamicForm, form_kwargs={"field_count": field_count}))
            def _test(dynamic_form):
                self.assertTrue(dynamic_form.is_valid())

            _test()

    @given(from_form(AllFieldsForm))
    def test_all_fields_form(self, all_fields_form):
        assume(all_fields_form.data["_char"].strip())
        print(all_fields_form.data["_regex"])
        self.assertTrue(all_fields_form.is_valid())
