# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=100, unique=True)


class Store(models.Model):
    name = models.CharField(max_length=100, unique=True)
    company = models.ForeignKey(Company, null=False)


class CharmField(models.Field):
    def db_type(self, connection):
        return "char(1)"


class CustomishField(models.Field):
    def db_type(self, connection):
        return "char(1)"


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
    me = models.ForeignKey('self', null=True)


class LoopA(models.Model):
    b = models.ForeignKey('LoopB', null=False)


class LoopB(models.Model):
    a = models.ForeignKey('LoopA', null=True)


class ManyInts(models.Model):
    i1 = models.IntegerField()
    i2 = models.SmallIntegerField()
    i3 = models.BigIntegerField()

    p1 = models.PositiveIntegerField()
    p2 = models.PositiveSmallIntegerField()
