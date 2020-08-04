# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

import os
import sys
import warnings

from hypothesis import HealthCheck, settings
from tests.common.setup import run

if __name__ == "__main__":
    run()

    settings.register_profile(
        "default", settings(suppress_health_check=[HealthCheck.too_slow])
    )

    settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.django.toys.settings")

    # This triggers a deprecation warning on some older versions of Django
    # because of its use of the imp module.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=DeprecationWarning)
        from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
