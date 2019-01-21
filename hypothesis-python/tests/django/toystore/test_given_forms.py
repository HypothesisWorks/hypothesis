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

from hypothesis import given
from hypothesis.extra.django import TestCase, from_form, register_field_strategy
from hypothesis.strategies import booleans, sampled_from
from tests.django.toystore.forms import (
    BasicFieldForm,
    TemporalFieldForm,
    NotQuiteCharFieldForm,
    ChoiceFieldForm,
    InternetProtocolForm,
    BroadBooleanField,
    CustomerForm,
    DynamicForm,
    ManyMultiValueForm,
    ManyNumericsForm,
    ManyTimesForm,
    OddFieldsForm,
    ShortStringForm,
)

register_field_strategy(
    BroadBooleanField, booleans() | sampled_from([u"1", u"0", u"True", u"False"])
)


class TestGetsBasicForms(TestCase):
    @given(from_form(CustomerForm))
    def test_valid_customer(self, customer_form):
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

    def test_dynamic_form(self):
        for field_count in range(2, 7):

            @given(from_form(DynamicForm, form_kwargs={"field_count": field_count}))
            def _test(dynamic_form):
                self.assertTrue(dynamic_form.is_valid())

            _test()

    @given(from_form(BasicFieldForm))
    def test_all_fields_form(self, basic_field_form):
        self.assertTrue(basic_field_form.is_valid())

    @given(from_form(TemporalFieldForm))
    def test_all_fields_form(self, time_field_form):
        self.assertTrue(time_field_form.is_valid())

    @given(from_form(NotQuiteCharFieldForm))
    def test_all_fields_form(self, charlike_field_form):
        self.assertTrue(charlike_field_form.is_valid())

    @given(from_form(ChoiceFieldForm))
    def test_all_fields_form(self, choice_field_form):
        self.assertTrue(choice_field_form.is_valid())

    @given(from_form(InternetProtocolForm))
    def test_all_fields_form(self, ip_field_form):
        self.assertTrue(ip_field_form.is_valid())

    @given(from_form(ManyMultiValueForm, form_kwargs={"subfield_count": 2}))
    def test_many_values_in_multi_value_field(self, many_multi_value_form):
        self.assertTrue(many_multi_value_form.is_valid())

    @given(from_form(ManyMultiValueForm, form_kwargs={"subfield_count": 105}))
    def test_excessive_values_in_multi_value_field(self, excessive_form):
        self.assertTrue(excessive_form.is_valid())

    @given(from_form(ShortStringForm))
    def test_short_string_form(self, short_string_form):
        self.assertTrue(short_string_form.is_valid())
