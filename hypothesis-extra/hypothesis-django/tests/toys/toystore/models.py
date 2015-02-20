from __future__ import division, print_function, absolute_import, \
    unicode_literals

from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=100, unique=True)
