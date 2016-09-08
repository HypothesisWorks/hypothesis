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

from __future__ import division, print_function, absolute_import, unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TestModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('big_integer_field', models.BigIntegerField()),
                ('binary_field', models.BinaryField()),
                ('boolean_field', models.BooleanField()),
                ('char_field', models.CharField(max_length=200)),
                ('char_field_blank', models.CharField(blank=True, max_length=200)),
                ('char_field_choices', models.CharField(choices=[('foo', 'Foo'), ('bar', 'Bar')], max_length=200)),
                ('char_field_default', models.CharField(default='default_value', max_length=200)),
                ('char_field_none', models.CharField(blank=True, max_length=200, null=True)),
                ('char_field_unique', models.CharField(max_length=200, unique=True)),
                ('date_field', models.DateField()),
                ('datetime_field', models.DateTimeField()),
                ('decimal_field', models.DecimalField(decimal_places=2, max_digits=8)),
                ('email_field', models.EmailField(max_length=254)),
                ('email_field_blank', models.EmailField(blank=True, max_length=254)),
                ('email_field_max_length', models.EmailField(max_length=50)),
                ('float_field', models.FloatField()),
                ('integer_field', models.IntegerField()),
                ('null_boolean_field', models.NullBooleanField()),
                ('positive_integer_field', models.PositiveIntegerField()),
                ('positive_small_integer_field', models.PositiveSmallIntegerField()),
                ('slug_field', models.SlugField(db_index=False)),
                ('small_integer_field', models.SmallIntegerField()),
                ('text_field', models.TextField()),
                ('time_field', models.TimeField()),
                ('url_field', models.URLField()),
                ('foreign_key_field', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='test_app.TestModel')),
            ],
        ),
    ]
