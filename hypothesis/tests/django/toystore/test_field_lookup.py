# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from unittest import mock

from django import forms as df
from django.db import models as dm
from django.test.utils import override_settings

from hypothesis import given, strategies as st
from hypothesis.errors import InvalidArgument, ResolutionFailed
from hypothesis.extra.django import (
    TestCase,
    _fields as _fields_module,
    from_field,
    register_field_strategy,
)

from tests.common.debug import check_can_generate_examples, find_any
from tests.django.toystore.models import Company


class TestFieldLookupEdgeCases(TestCase):
    def test_datetime_fields_without_use_tz(self):
        # Covers the non-timezone-aware branch of _for_datetime.
        with override_settings(USE_TZ=False):
            check_can_generate_examples(from_field(dm.DateTimeField()))
            check_can_generate_examples(from_field(df.DateTimeField()))

    def test_form_time_field_without_use_tz(self):
        # Covers the non-timezone-aware branch of _for_form_time.
        with override_settings(USE_TZ=False):
            check_can_generate_examples(from_field(df.TimeField()))

    def test_time_and_duration_fields_when_not_using_sqlite(self):
        # Covers the branches of _for_model_time and _for_duration that are
        # only taken on non-SQLite backends; patching using_sqlite() avoids
        # the need to actually reconfigure the test database connection.
        with mock.patch.object(_fields_module, "using_sqlite", return_value=False):
            check_can_generate_examples(from_field(dm.TimeField()))
            check_can_generate_examples(from_field(dm.DurationField()))

    @given(st.just(None))
    def test_optional_slug_fields_allow_the_empty_string(self, _):
        # find_any() is called nested inside this @given test (rather than as
        # a bare top-level call) because manage.py's test runner never
        # imports tests.conftest, and find_any()'s top-level code path
        # lazily imports it, which re-runs tests.common.setup.run() and
        # conflicts with the profile manage.py already configured.
        find_any(from_field(dm.SlugField(blank=True)), lambda s: s == "")
        find_any(from_field(df.SlugField(required=False)), lambda s: s == "")

    def test_form_ip_address_field_without_a_version_validator(self):
        field = df.GenericIPAddressField()
        field.default_validators = []
        with self.assertRaises(ResolutionFailed):
            from_field(field)

    @given(st.just(None))
    def test_binary_field(self, _):
        # Covers both branches of _for_binary.
        check_can_generate_examples(from_field(dm.BinaryField()))
        find_any(from_field(dm.BinaryField(blank=True)), lambda b: b == b"")

    def test_register_field_strategy_requires_a_field_subclass(self):
        with self.assertRaises(InvalidArgument):
            register_field_strategy(str, st.just("x"))

    def test_register_field_strategy_rejects_already_registered_fields(self):
        with self.assertRaises(InvalidArgument):
            register_field_strategy(dm.BooleanField, st.just(True))

    def test_register_field_strategy_rejects_autofield(self):
        with self.assertRaises(InvalidArgument):
            register_field_strategy(dm.AutoField, st.just(1))

    @given(st.just(None))
    def test_model_charfield_with_choices_and_blank_includes_empty_string(self, _):
        field = dm.CharField(
            max_length=10, choices=(("a", "A"), ("b", "B")), blank=True
        )
        find_any(from_field(field), lambda v: v == "")

    @given(st.just(None))
    def test_form_choicefield_with_blank_choice_and_not_required(self, _):
        field = df.ChoiceField(
            choices=(("", "---"), ("a", "A"), ("b", "B")), required=False
        )
        find_any(from_field(field), lambda v: v == "")

    def test_model_choice_field_with_no_choices_raises(self):
        field = df.ModelChoiceField(queryset=Company.objects.none())
        field.choices = None
        with self.assertRaises(InvalidArgument):
            check_can_generate_examples(from_field(field))

    def test_model_choice_field_with_manually_set_choices(self):
        Company.objects.create(name="Manual Co")
        field = df.ModelChoiceField(queryset=Company.objects.none())
        # Bypass the `choices` setter (which eagerly normalizes the value) by
        # setting the underlying attribute directly, as e.g. some third-party
        # libraries do to provide a pre-computed, ordered set of choices.
        field._choices = Company.objects.order_by("name").values_list("pk", "name")
        check_can_generate_examples(from_field(field))

    def test_model_choice_field_with_unordered_queryset_raises(self):
        field = df.ModelChoiceField(queryset=Company.objects.all())
        with self.assertRaises(InvalidArgument):
            check_can_generate_examples(from_field(field))
