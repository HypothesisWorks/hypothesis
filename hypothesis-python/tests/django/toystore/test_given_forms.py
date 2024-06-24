# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from django import forms

from hypothesis import assume, given
from hypothesis.extra.django import (
    TestCase,
    from_field,
    from_form,
    register_field_strategy,
)
from hypothesis.strategies import booleans, sampled_from

from tests.django.toystore.forms import (
    BasicFieldForm,
    BroadBooleanField,
    ChoiceFieldForm,
    CustomerForm,
    DynamicForm,
    EmailFieldForm,
    InternetProtocolForm,
    ManyMultiValueForm,
    ManyNumericsForm,
    ManyTimesForm,
    MultipleCompaniesForm,
    OddFieldsForm,
    RegexFieldForm,
    ShortStringForm,
    SlugFieldForm,
    StoreForm,
    TemporalFieldForm,
    URLFieldForm,
    UsernameForm,
    UUIDFieldForm,
    WithValidatorsForm,
)
from tests.django.toystore.models import Company

register_field_strategy(
    BroadBooleanField, booleans() | sampled_from(["1", "0", "True", "False"])
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
    def test_basic_fields_form(self, basic_field_form):
        self.assertTrue(basic_field_form.is_valid())

    @given(from_form(TemporalFieldForm))
    def test_temporal_fields_form(self, time_field_form):
        self.assertTrue(time_field_form.is_valid())

    @given(from_form(EmailFieldForm))
    def test_email_field_form(self, email_field_form):
        self.assertTrue(email_field_form.is_valid())

    @given(from_form(SlugFieldForm))
    def test_slug_field_form(self, slug_field_form):
        self.assertTrue(slug_field_form.is_valid())

    @given(from_form(URLFieldForm))
    def test_url_field_form(self, url_field_form):
        self.assertTrue(url_field_form.is_valid())

    @given(from_form(RegexFieldForm))
    def test_regex_field_form(self, regex_field_form):
        self.assertTrue(regex_field_form.is_valid())

    @given(from_form(UUIDFieldForm))
    def test_uuid_field_form(self, uuid_field_form):
        self.assertTrue(uuid_field_form.is_valid())

    @given(from_form(ChoiceFieldForm))
    def test_choice_fields_form(self, choice_field_form):
        self.assertTrue(choice_field_form.is_valid())

    @given(from_form(InternetProtocolForm))
    def test_ip_fields_form(self, ip_field_form):
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

    @given(from_form(WithValidatorsForm))
    def test_tight_validators_form(self, x):
        self.assertTrue(1 <= x.data["_int_one_to_five"] <= 5)
        self.assertTrue(1 <= x.data["_decimal_one_to_five"] <= 5)
        self.assertTrue(1 <= x.data["_float_one_to_five"] <= 5)
        self.assertTrue(5 <= len(x.data["_string_five_to_ten"]) <= 10)

    @given(from_form(UsernameForm))
    def test_username_form(self, username_form):
        self.assertTrue(username_form.is_valid())

    @given(from_form(UsernameForm))
    def test_read_only_password_hash_field_form(self, password_form):
        self.assertTrue(password_form.is_valid())


class TestFormsWithModelChoices(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Set up example Company records to use as choices for
        # Store.company. These must exist before creating a strategy
        # for the ModelChoiceField.
        cls.company_names = ("Bill's Flowers", "Jane's Sporting Goods")
        for name in cls.company_names:
            Company.objects.create(name=name)

    @given(
        choice=from_field(
            forms.ModelChoiceField(queryset=Company.objects.order_by("name"))
        )
    )
    def test_from_model_choices_field(self, choice):
        assume(choice != "")  # Skip the empty choice.
        self.assertIsInstance(choice, int)
        Company.objects.get(id=choice)

    @given(
        choice=from_field(
            forms.ModelChoiceField(
                queryset=Company.objects.order_by("name"), empty_label=None
            )
        )
    )
    def test_from_model_choices_field_no_empty_choice(self, choice):
        Company.objects.get(id=choice)

    @given(choice=from_field(forms.ModelChoiceField(queryset=Company.objects.none())))
    def test_from_model_choices_field_empty(self, choice):
        self.assertEqual(choice, "")

    @given(form=from_form(StoreForm))
    def test_store_form_valid(self, form):
        assume(form.data["company"])
        self.assertTrue(form.is_valid())

    @given(
        choice=from_field(
            forms.ModelMultipleChoiceField(queryset=Company.objects.order_by("name"))
        )
    )
    def test_from_model_multiple_choices_field(self, choice):
        n_choices = len(choice)
        self.assertEqual(n_choices, len(set(choice)))
        self.assertEqual(n_choices, Company.objects.filter(pk__in=choice).count())

    @given(form=from_form(MultipleCompaniesForm))
    def test_multiple_companies_form_valid(self, form):
        self.assertTrue(form.is_valid())
