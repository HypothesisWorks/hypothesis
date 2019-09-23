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
from tempfile import mkdtemp
from warnings import filterwarnings

from hypothesis import Verbosity, settings
from hypothesis._settings import not_set
from hypothesis.configuration import set_hypothesis_home_dir
from hypothesis.errors import NonInteractiveExampleWarning
from hypothesis.internal.charmap import charmap, charmap_file
from hypothesis.internal.coverage import IN_COVERAGE_TESTS


def run():
    filterwarnings("error")
    filterwarnings("ignore", category=ImportWarning)
    filterwarnings("ignore", category=FutureWarning, module="pandas._version")

    # Fixed in recent versions but allowed by pytest=3.0.0; see #1630
    filterwarnings("ignore", category=DeprecationWarning, module="pluggy")

    # See https://github.com/numpy/numpy/pull/432
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

    # Imported by Pandas in version 1.9, but fixed in later versions.
    filterwarnings(
        "ignore", message="Importing from numpy.testing.decorators is deprecated"
    )
    filterwarnings(
        "ignore", message="Importing from numpy.testing.nosetester is deprecated"
    )

    # User-facing warning which does not apply to our own tests
    filterwarnings("ignore", category=NonInteractiveExampleWarning)

    new_home = mkdtemp()
    set_hypothesis_home_dir(new_home)
    assert settings.default.database.path.startswith(new_home)

    charmap()
    assert os.path.exists(charmap_file()), charmap_file()
    assert isinstance(settings, type)

    # We do a smoke test here before we mess around with settings.
    x = settings()

    import hypothesis._settings as settings_module

    for s in settings_module.all_settings.values():
        v = getattr(x, s.name)
        # Check if it has a dynamically defined default and if so skip
        # comparison.
        if getattr(settings, s.name).show_default:
            assert v == s.default, "%r == x.%s != s.%s == %r" % (
                v,
                s.name,
                s.name,
                s.default,
            )

    settings.register_profile(
        "default", settings(max_examples=10 if IN_COVERAGE_TESTS else not_set)
    )

    settings.register_profile("speedy", settings(max_examples=5))

    settings.register_profile("debug", settings(verbosity=Verbosity.debug))

    settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))
