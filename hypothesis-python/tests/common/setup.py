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

from hypothesis import Phase, Verbosity, settings
from hypothesis._settings import not_set
from hypothesis.internal.conjecture.data import AVAILABLE_PROVIDERS
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
    x = settings()

    from hypothesis import _settings as settings_module

    for s in settings_module.all_settings.values():
        v = getattr(x, s.name)
        # Check if it has a dynamically defined default and if so skip comparison.
        if getattr(settings, s.name).show_default:
            assert (
                v == s.default
            ), f"({v!r} == x.{s.name}) != (s.{s.name} == {s.default!r})"

    settings.register_profile(
        "default",
        settings(
            max_examples=20 if IN_COVERAGE_TESTS else not_set,
            phases=list(Phase),  # Dogfooding the explain phase
        ),
    )

    settings.register_profile("speedy", settings(max_examples=5))

    settings.register_profile("debug", settings(verbosity=Verbosity.debug))

    settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))

    for backend in set(AVAILABLE_PROVIDERS) - {"hypothesis"}:
        settings.register_profile(backend, backend=backend)  # e.g. "crosshair"
