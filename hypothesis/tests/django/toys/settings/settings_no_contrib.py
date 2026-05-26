# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from .settings import *  # noqa: F403

# We test django in two contexts: with some default django.contrib apps installed
# (which is settings.py), and with no django.contrib apps installed (which is this
# file). We set DJANGO_SETTINGS_MODULE in tox to select which settings file we
# use during testing.

INSTALLED_APPS = ["tests.django.toystore"]
ROOT_URLCONF = "tests.django.toys.settings.no_urls"
