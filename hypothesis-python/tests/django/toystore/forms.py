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

from django import forms

from tests.django.toystore.models import (
    CouldBeCharming,
    Customer,
    ManyNumerics,
    ManyTimes,
    OddFields,
    RestrictedFields,
)


class CouldBeCharmingForm(forms.ModelForm):
    def __repr__(self):
        return repr(self.data)

    class Meta:
        model = CouldBeCharming
        fields = "__all__"


class CustomerForm(forms.ModelForm):
    def __repr__(self):
        return repr(self.data)

    class Meta:
        model = Customer
        fields = "__all__"


class ManyNumericsForm(forms.ModelForm):
    def __repr__(self):
        return repr(self.data)

    class Meta:
        model = ManyNumerics
        fields = "__all__"


class ManyTimesForm(forms.ModelForm):
    def __repr__(self):
        return repr(self.data)

    class Meta:
        model = ManyTimes
        fields = "__all__"


class OddFieldsForm(forms.ModelForm):
    def __repr__(self):
        return repr(self.data)

    class Meta:
        model = OddFields
        fields = "__all__"


class RestrictedFieldsForm(forms.ModelForm):
    def __repr__(self):
        """I recommend putting this in your form to show the failed cases"""
        return repr(self.data)

    class Meta:
        model = RestrictedFields
        fields = "__all__"


class DynamicForm(forms.Form):
    def __repr__(self):
        return repr(self.data)

    def __init__(self, *args, field_count=5, **kwargs):
        super(DynamicForm, self).__init__(*args, **kwargs)
        for i in range(field_count):
            field_name = "field-%d" % (i,)
            self.fields[field_name] = forms.CharField(required=False)


class AllFieldsForm(forms.Form):
    def __repr__(self):
        return repr(self.data)

    _boolean = forms.BooleanField()
    _char = forms.CharField()
    _choice = forms.ChoiceField(
        choices=(("cola", "Cola"), ("tea", "Tea"), ("water", "Water"))
    )
    _multiple = forms.MultipleChoiceField(
        choices=(("cola", "Cola"), ("tea", "Tea"), ("water", "Water"))
    )
    _typed = forms.TypedChoiceField(
        choices=(("1", "one"), ("2", "two"), ("3", "three"), ("4", "four")),
        coerce=int,
        empty_value=0,
    )
    _typed_multiple = forms.TypedMultipleChoiceField(
        choices=(("1", "one"), ("2", "two"), ("3", "three"), ("4", "four")),
        coerce=int,
        empty_value=0,
    )
    _date = forms.DateField()
    _date_time = forms.DateTimeField()
    _decimal = forms.DecimalField(max_digits=8, decimal_places=3)
    _duration = forms.DurationField()
    _email = forms.EmailField()
    _float = forms.FloatField()
    _generic = forms.GenericIPAddressField()
    _integer = forms.IntegerField()
    _null = forms.NullBooleanField()
    _regex = forms.RegexField(regex=r"[A-Z]{3}\.[a-z]{4}")
    _slug = forms.SlugField()
    _split_date_time = forms.SplitDateTimeField()
    _time = forms.TimeField()
    _url = forms.URLField()
    _uuid = forms.UUIDField()
