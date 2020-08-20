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

"""Run all functions registered for the "hypothesis" entry point.

This can be used with `st.register_type_strategy` to register strategies for your
custom types, running the relevant code when *hypothesis* is imported instead of
your package.
"""

import pkg_resources


def run():
    for entry_point in pkg_resources.iter_entry_points("hypothesis"):
        entry_point.load()  # pragma: no cover
