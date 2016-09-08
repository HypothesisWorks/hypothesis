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


class TestModel(models.Model):

    big_integer_field = models.BigIntegerField()

    binary_field = models.BinaryField()

    boolean_field = models.BooleanField()

    char_field = models.CharField(
        max_length=200,
    )

    char_field_blank = models.CharField(
        max_length=200,
        blank=True,
    )

    char_field_choices = models.CharField(
        max_length=200,
        choices=(
            ("foo", "Foo"),
            ("bar", "Bar"),
        ),
    )

    char_field_default = models.CharField(
        max_length=200,
        default="default_value",
    )

    char_field_none = models.CharField(
        max_length=200,
        blank=True,
        null=True,
    )

    char_field_unique = models.CharField(
        max_length=200,
        unique=True,
    )

    date_field = models.DateField()

    datetime_field = models.DateTimeField()

    decimal_field = models.DecimalField(
        decimal_places=2,
        max_digits=8,
    )

    email_field = models.EmailField()

    email_field_blank = models.EmailField(
        blank=True,
    )

    email_field_max_length = models.EmailField(
        max_length=50,
    )

    float_field = models.FloatField()

    foreign_key_field = models.ForeignKey(
        "self",
        null=True,
        blank=True,
    )

    integer_field = models.IntegerField()

    null_boolean_field = models.NullBooleanField()

    positive_integer_field = models.PositiveIntegerField()

    positive_small_integer_field = models.PositiveSmallIntegerField()

    slug_field = models.SlugField(
        db_index=False,
    )

    small_integer_field = models.SmallIntegerField()

    text_field = models.TextField()

    time_field = models.TimeField()

    url_field = models.URLField()
