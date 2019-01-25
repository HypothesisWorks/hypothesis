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
from django.forms import widgets

from tests.django.toystore.models import (
    CouldBeCharming,
    Customer,
    ManyNumerics,
    ManyTimes,
    OddFields,
)


class ReprModelForm(forms.ModelForm):
    def __repr__(self):
        """I recommend putting this in your form to show the failed cases."""
        return "%r\n%r" % (self.data, self.errors)


class ReprForm(forms.Form):
    def __repr__(self):
        return "%r\n%r" % (self.data, self.errors)


class CouldBeCharmingForm(ReprModelForm):
    class Meta:
        model = CouldBeCharming
        fields = "__all__"


class CustomerForm(ReprModelForm):
    class Meta:
        model = Customer
        fields = "__all__"


class ManyNumericsForm(ReprModelForm):
    class Meta:
        model = ManyNumerics
        fields = "__all__"


class ManyTimesForm(ReprModelForm):
    class Meta:
        model = ManyTimes
        fields = "__all__"


class OddFieldsForm(ReprModelForm):
    class Meta:
        model = OddFields
        fields = "__all__"


class DynamicForm(ReprForm):
    def __init__(self, field_count=5, **kwargs):
        super(DynamicForm, self).__init__(**kwargs)
        for i in range(field_count):
            field_name = "field-%d" % (i,)
            self.fields[field_name] = forms.CharField(required=False)


class BasicFieldForm(ReprForm):
    _boolean_required = forms.BooleanField()
    _boolean = forms.BooleanField(required=False)
    # This took me too long to figure out... The BooleanField will actually
    # raise a ValidationError when it recieves a value of False. Why they
    # didn't call it a TrueOnlyField escapes me, but *if* you actually want
    # to accept both True and False in your BooleanField, make sure you set
    # `required=False`. This behavior has been hotly contested in the bug
    # tracker (e.g. https://code.djangoproject.com/ticket/23547), but it
    # seems that since the tests and documentation are already written
    # this behavior is Truth.
    # see the note in the documentation
    # https://docs.djangoproject.com/en/dev/ref/forms/fields/#booleanfield

    _char_required = forms.CharField(required=True)
    _char = forms.CharField(required=False)
    _decimal = forms.DecimalField(max_digits=8, decimal_places=3)
    _float = forms.FloatField()
    _integer = forms.IntegerField()
    _null_boolean = forms.NullBooleanField()


class TemporalFieldForm(ReprForm):
    _date = forms.DateField()
    _date_time = forms.DateTimeField()
    _duration = forms.DurationField()
    _time = forms.TimeField()
    _split_date_time = forms.SplitDateTimeField()


class EmailFieldForm(ReprForm):
    _email = forms.EmailField()


class SlugFieldForm(ReprForm):
    _slug = forms.SlugField()


class URLFieldForm(ReprForm):
    _url = forms.URLField()


class RegexFieldForm(ReprForm):
    _regex = forms.RegexField(regex=u"[A-Z]{3}\\.[a-z]{4}")


class UUIDFieldForm(ReprForm):
    _uuid = forms.UUIDField()


class ChoiceFieldForm(ReprForm):
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


class InternetProtocolForm(ReprForm):
    _ip_both = forms.GenericIPAddressField()
    _ip_v4 = forms.GenericIPAddressField(protocol="IPv4")
    _ip_v6 = forms.GenericIPAddressField(protocol="IPv6")


class BroadBooleanInput(widgets.CheckboxInput):
    """Basically pulled directly from the Django CheckboxInput. I added
    some stuff to ``values``
    """

    def value_from_datadict(self, data, files, name):
        if name not in data:
            return False
        value = data.get(name)
        # Translate true and false strings to boolean values.
        values = {u"true": True, u"false": False, u"0": False, u"1": True}
        if isinstance(value, str):
            value = values.get(value.lower(), value)
        return bool(value)


class MultiCheckboxWidget(widgets.MultiWidget):
    def __init__(self, subfield_count=12, **kwargs):
        _widgets = [BroadBooleanInput()] * subfield_count
        super(MultiCheckboxWidget, self).__init__(_widgets, **kwargs)

    def decompress(self, value):
        values = []
        for _value in value.split(u"::"):
            if _value in (u"0", u"", u"False", 0, None, False):
                values.append(False)
            else:
                values.append(True)
        return values


class BroadBooleanField(forms.BooleanField):
    pass


class MultiBooleanField(forms.MultiValueField):
    def __init__(self, subfield_count=12, **kwargs):
        subfields = [BroadBooleanField()] * subfield_count
        widget = MultiCheckboxWidget(subfield_count=subfield_count)
        super(MultiBooleanField, self).__init__(fields=subfields, widget=widget)

    def compress(self, values):
        return u"::".join([str(x) for x in values])


class ManyMultiValueForm(ReprForm):
    def __init__(self, subfield_count=12, **kwargs):
        super(ManyMultiValueForm, self).__init__(**kwargs)
        self.fields["mv_field"] = MultiBooleanField(subfield_count=subfield_count)


class ShortStringForm(ReprForm):
    _not_too_long = forms.CharField(max_length=20, required=False)
