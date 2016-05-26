# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

from django.db import models
from django.core.exceptions import ValidationError


class Company(models.Model):
    name = models.CharField(max_length=100, unique=True)


class Store(models.Model):
    name = models.CharField(max_length=100, unique=True)
    company = models.ForeignKey(Company, null=False)


class CharmField(models.Field):

    def db_type(self, connection):
        return u'char(1)'


class CustomishField(models.Field):

    def db_type(self, connection):
        return u'char(1)'


class Customish(models.Model):
    customish = CustomishField()


class Customer(models.Model):
    name = models.CharField(max_length=100, unique=True)
    email = models.EmailField(max_length=100, unique=True)
    gender = models.CharField(max_length=50, null=True)
    age = models.IntegerField()
    birthday = models.DateTimeField()


class Charming(models.Model):
    charm = CharmField()


class CouldBeCharming(models.Model):
    charm = CharmField(null=True)


class SelfLoop(models.Model):
    me = models.ForeignKey(u'self', null=True)


class LoopA(models.Model):
    b = models.ForeignKey(u'LoopB', null=False)


class LoopB(models.Model):
    a = models.ForeignKey(u'LoopA', null=True)


class ManyNumerics(models.Model):
    i1 = models.IntegerField()
    i2 = models.SmallIntegerField()
    i3 = models.BigIntegerField()

    p1 = models.PositiveIntegerField()
    p2 = models.PositiveSmallIntegerField()

    d = models.DecimalField(decimal_places=2, max_digits=5)


class CustomishDefault(models.Model):
    customish = CustomishField(default=u'b')


class MandatoryComputed(models.Model):
    name = models.CharField(max_length=100, unique=True)
    company = models.ForeignKey(Company, null=False)

    def __init__(self, **kw):
        if u'company' in kw:
            raise RuntimeError()
        cname = kw[u'name'] + u'_company'
        kw[u'company'] = Company.objects.create(name=cname)
        super(MandatoryComputed, self).__init__(**kw)


def validate_even(value):
    if value % 2 != 0:
        raise ValidationError('')


class RestrictedFields(models.Model):
    text_field_4 = models.TextField(max_length=4, blank=True)
    char_field_4 = models.CharField(max_length=4, blank=True)
    choice_field_text = models.TextField(
        choices=(('foo', 'Foo'), ('bar', 'Bar'))
    )
    choice_field_int = models.IntegerField(
        choices=((1, 'First'), (2, 'Second'))
    )
    null_choice_field_int = models.IntegerField(
        choices=((1, 'First'), (2, 'Second')),
        null=True, blank=True
    )
    even_number_field = models.IntegerField(
        validators=[validate_even]
    )
    non_blank_text_field = models.TextField(blank=False)
