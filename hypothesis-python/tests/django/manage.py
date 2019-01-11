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

import os
import sys

from hypothesis import HealthCheck, settings, unlimited
from tests.common.setup import run

if __name__ == u"__main__":
    run()

    settings.register_profile(
        "default",
        settings(timeout=unlimited, suppress_health_check=[HealthCheck.too_slow]),
    )

    settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))

    os.environ.setdefault(u"DJANGO_SETTINGS_MODULE", u"tests.django.toys.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
