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
from warnings import filterwarnings

from hypothesis import (
    HealthCheck,
    Phase,
    Verbosity,
    _settings as settings_module,
    settings,
)
from hypothesis._settings import CI, default as default_settings, is_in_ci, not_set
from hypothesis.internal.conjecture.providers import AVAILABLE_PROVIDERS
from hypothesis.internal.coverage import IN_COVERAGE_TESTS


def run():
    filterwarnings("error")
    filterwarnings("ignore", category=ImportWarning)
    filterwarnings("ignore", category=FutureWarning, module="pandas._version")

    # See https://github.com/numpy/numpy/pull/432; still a thing as of 2022.
    filterwarnings("ignore", message="numpy.dtype size changed")
    filterwarnings("ignore", message="numpy.ufunc size changed")

    # See https://github.com/HypothesisWorks/hypothesis/issues/1674
    filterwarnings(
        "ignore",
        message=(
            "The virtualenv distutils package at .+ appears to be in the "
            "same location as the system distutils?"
        ),
        category=UserWarning,
    )

    # We do a smoke test here before we mess around with settings.
    for setting_name in settings_module.all_settings:
        # database value is dynamically calculated
        if setting_name == "database":
            continue

        value = getattr(settings(), setting_name)
        default_value = getattr(default_settings, setting_name)
        assert value == default_value or (
            is_in_ci() and value == getattr(CI, setting_name)
        ), f"({value!r} == x.{setting_name}) != (s.{setting_name} == {default_value!r})"

    settings.register_profile(
        "default",
        settings(
            default_settings,
            max_examples=20 if IN_COVERAGE_TESTS else not_set,
            phases=list(Phase),  # Dogfooding the explain phase
        ),
    )
    settings.register_profile("speedy", settings(max_examples=5))
    settings.register_profile("debug", settings(verbosity=Verbosity.debug))

    if "crosshair" in AVAILABLE_PROVIDERS:
        settings.register_profile(
            "crosshair",
            backend="crosshair",
            max_examples=20,
            deadline=None,
            suppress_health_check=(HealthCheck.too_slow, HealthCheck.filter_too_much),
            report_multiple_bugs=False,
        )

    for backend in set(AVAILABLE_PROVIDERS) - {"hypothesis", "crosshair"}:
        settings.register_profile(backend, backend=backend)

    settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))
