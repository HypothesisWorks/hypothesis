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

import os
import subprocess

DOES_NOT_WRITE_CHARMAP = """
import hypothesis.core

assert hypothesis.core.running_under_pytest

def test():
    pass
"""
WRITES_CHARMAP = """
from hypothesis import given, strategies as st

@given(st.text())
def test_property(s):
    pass
"""


def names(path):
    return {p.name for p in path.iterdir()} - {"__pycache__", ".pytest_cache"}


def test_does_not_create_dir_unless_actually_using_hypothesis(tmp_path):
    pyfile = tmp_path / "test.py"
    env = {**os.environ, "HYPOTHESIS_STORAGE_DIRECTORY": ".hypothesis"}

    pyfile.write_text(DOES_NOT_WRITE_CHARMAP)
    subprocess.check_call(["pytest", "test.py"], env=env, cwd=tmp_path)
    assert names(tmp_path) == {"test.py"}

    pyfile.write_text(DOES_NOT_WRITE_CHARMAP + WRITES_CHARMAP)
    subprocess.check_call(["pytest", "test.py"], env=env, cwd=tmp_path)
    assert names(tmp_path) == {"test.py", ".hypothesis"}
