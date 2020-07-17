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

import subprocess
import sys

from hypothesis import core as core


def test_is_running_under_pytest():
    assert core.running_under_pytest


FILE_TO_RUN = """
import hypothesis.core as core
assert not core.running_under_pytest
"""


def test_is_not_running_under_pytest(tmpdir):
    pyfile = tmpdir.join("test.py")
    pyfile.write(FILE_TO_RUN)
    subprocess.check_call([sys.executable, str(pyfile)])
