# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

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

    try:
        from django.utils.deprecation import RemovedInDjango50Warning
    except ImportError:
        RemovedInDjango50Warning = ()

    try:
        from django.utils.deprecation import RemovedInDjango60Warning
    except ImportError:
        RemovedInDjango60Warning = ()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RemovedInDjango50Warning)
        warnings.simplefilter("ignore", category=RemovedInDjango60Warning)
        execute_from_command_line(sys.argv)
