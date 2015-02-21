# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis.extra.django import TestCase
from hypothesis.extra.django.models import DjangoSkeleton, model_to_base_specifier, ModelNotSupported
from toystore.models import Company, Customer, Charming, CouldBeCharming
from hypothesis.internal.compat import text_type
import hypothesis.extra.fakefactory as ff
from hypothesis.descriptors import one_of
from hypothesis.extra.datetime import timezone_aware_datetime


class TestSkeletons(TestCase):
    def test_can_build_simple_skeleton(self):
        name = "A pretty cool company"
        skeleton = DjangoSkeleton(
            model=Company,
            build_args={'name': name}
        )
        model = skeleton.build()
        assert isinstance(model, Company)
        assert model.name == name
        assert model.pk
        Company.objects.get(name=name)

    def test_can_extract_skeleton_spec(self):
        self.assertEqual(
            model_to_base_specifier(Company),
            {'name': text_type}
        )

        self.assertEqual(
            model_to_base_specifier(Customer),
            {
                'name': text_type,
                'gender': one_of((None, text_type)),
                'age': int,
                'email': ff.FakeFactory('email'),
                'birthday': timezone_aware_datetime,
            }
        )

    def test_raises_with_unsupported_types(self):
        with self.assertRaises(ModelNotSupported):
            model_to_base_specifier(Charming)


    def test_does_not_raise_with_nullable_unsupported_type(self):
        model_to_base_specifier(CouldBeCharming)
