# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
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

"""Hypothesis is a library for writing unit tests which are parametrized by
some source of data.

It verifies your code against a wide range of input and minimizes any
failing examples it finds.
"""

import hypothesis._error_if_old  # noqa  # imported for side-effect of nice error
from hypothesis._settings import HealthCheck, Phase, Verbosity, settings
from hypothesis.control import (
    assume,
    currently_in_test_context,
    event,
    note,
    reject,
    target,
)
from hypothesis.core import example, find, given, reproduce_failure, seed
from hypothesis.entry_points import run
from hypothesis.internal.entropy import register_random
from hypothesis.utils.conventions import infer
from hypothesis.version import __version__, __version_info__

__all__ = [
    "HealthCheck",
    "Phase",
    "Verbosity",
    "assume",
    "currently_in_test_context",
    "event",
    "example",
    "find",
    "given",
    "infer",
    "note",
    "register_random",
    "reject",
    "reproduce_failure",
    "seed",
    "settings",
    "target",
    "__version__",
    "__version_info__",
]

run()
del run
