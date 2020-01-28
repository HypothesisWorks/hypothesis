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

import sys

from hypothesis.version import __version__

message = """
Hypothesis {} requires Python 3.5.2 or later.

This can only happen if your packaging toolchain is older than python_requires.
See https://packaging.python.org/guides/distributing-packages-using-setuptools/
"""

if sys.version_info[:3] < (3, 5, 2):  # pragma: no cover
    raise Exception(message.format(__version__))
