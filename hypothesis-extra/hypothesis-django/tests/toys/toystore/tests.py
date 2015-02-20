from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis import given
from toystore.models import Company
from hypothesis.extra.django import TestCase


class TestContraints(TestCase):
    @given(int)
    def test_is_blank_slate(self, unused):
        Company.objects.create(name="MickeyCo")

    def test_normal_test_1(self):
        Company.objects.create(name="MickeyCo")

    def test_normal_test_2(self):
        Company.objects.create(name="MickeyCo")
