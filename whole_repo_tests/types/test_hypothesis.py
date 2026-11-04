# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import sys

from hypothesistooling.release import HYPOTHESIS, PYTHON_SRC
from hypothesistooling.scripts import pip_tool


def test_mypy_passes_on_hypothesis():
    pip_tool("mypy", str(PYTHON_SRC))


def test_pyrefly_passes_on_hypothesis():
    pip_tool(
        "pyrefly",
        "check",
        "--python-interpreter-path",
        sys.executable,
        cwd=HYPOTHESIS,
    )
