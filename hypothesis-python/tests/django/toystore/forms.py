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
from django.contrib.auth.forms import ReadOnlyPasswordHashField, UsernameField
from django.core.validators import (
    MaxLengthValidator,
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
)
from django.forms import widgets

from tests.django.toystore.models import (
    Company,
    CouldBeCharming,
    Customer,
    ManyNumerics,
    ManyTimes,
    OddFields,
    Store,
)


class ReprModelForm(forms.ModelForm):
    def __repr__(self):
        """I recommend putting this in your form to show the failed cases."""
        return f"{self.data!r}\n{self.errors!r}"


class ReprForm(forms.Form):
    def __repr__(self):
        return f"{self.data!r}\n{self.errors!r}"


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
        super().__init__(**kwargs)
        for i in range(field_count):
            field_name = f"field-{i}"
            self.fields[field_name] = forms.CharField(required=False)


class BasicFieldForm(ReprForm):
    _boolean_required = forms.BooleanField()
    _boolean = forms.BooleanField(required=False)
    # This took me too long to figure out... The BooleanField will actually
    # raise a ValidationError when it receives a value of False. Why they
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


class WithValidatorsForm(ReprForm):
    num_validators = (MinValueValidator(1), MaxValueValidator(5))
    _int_one_to_five = forms.IntegerField(validators=num_validators)
    _decimal_one_to_five = forms.FloatField(validators=num_validators)
    _float_one_to_five = forms.FloatField(validators=num_validators)
    len_validators = (MinLengthValidator(5), MaxLengthValidator(10))
    _string_five_to_ten = forms.CharField(validators=len_validators)


class EmailFieldForm(ReprForm):
    _email = forms.EmailField()


class SlugFieldForm(ReprForm):
    _slug = forms.SlugField()


class URLFieldForm(ReprForm):
    _url = forms.URLField()


class RegexFieldForm(ReprForm):
    _regex = forms.RegexField(regex="[A-Z]{3}\\.[a-z]{4}")


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
        values = {"true": True, "false": False, "0": False, "1": True}
        if isinstance(value, str):
            value = values.get(value.lower(), value)
        return bool(value)


class MultiCheckboxWidget(widgets.MultiWidget):
    def __init__(self, subfield_count=12, **kwargs):
        _widgets = [BroadBooleanInput()] * subfield_count
        super().__init__(_widgets, **kwargs)

    def decompress(self, value):
        values = []
        for _value in value.split("::"):
            if _value in ("0", "", "False", 0, None, False):
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
        super().__init__(fields=subfields, widget=widget)

    def compress(self, values):
        return "::".join(str(x) for x in values)


class ManyMultiValueForm(ReprForm):
    def __init__(self, subfield_count=12, **kwargs):
        super().__init__(**kwargs)
        self.fields["mv_field"] = MultiBooleanField(subfield_count=subfield_count)


class ShortStringForm(ReprForm):
    _not_too_long = forms.CharField(max_length=20, required=False)


class UsernameForm(ReprForm):
    username = UsernameField()


class ReadOnlyPasswordHashFieldForm(ReprForm):
    password = ReadOnlyPasswordHashField()


class StoreForm(ReprModelForm):
    company = forms.ModelChoiceField(queryset=Company.objects.order_by("name"))

    class Meta:
        model = Store
        fields = "__all__"


class MultipleCompaniesForm(ReprForm):
    companies = forms.ModelMultipleChoiceField(
        queryset=Company.objects.order_by("name")
    )
