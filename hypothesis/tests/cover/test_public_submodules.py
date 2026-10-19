# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import subprocess
import sys

import pytest

from tests.common.utils import skipif_emscripten

PUBLIC_SUBMODULES = [
    "database",
    "errors",
    "extra",
    "provisional",
    "stateful",
    "strategies",
]


@skipif_emscripten
@pytest.mark.parametrize("name", PUBLIC_SUBMODULES)
def test_public_submodule_available_after_import_hypothesis(name):
    subprocess.check_call(
        [
            sys.executable,
            "-c",
            f"import hypothesis; hypothesis.{name}.__name__",
        ]
    )

    namespace = {}
    exec("from hypothesis import *", namespace)
    assert namespace[name] is sys.modules[f"hypothesis.{name}"]
