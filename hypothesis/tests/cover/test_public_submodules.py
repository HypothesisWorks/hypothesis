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

import hypothesis
from hypothesis import _LAZY_SUBMODULES

from tests.common.utils import skipif_emscripten

PUBLIC_SUBMODULES_EAGER = ["database", "errors", "strategies"]


def run_python(code):
    subprocess.check_call([sys.executable, "-c", code])


@skipif_emscripten
@pytest.mark.parametrize("name", PUBLIC_SUBMODULES_EAGER + _LAZY_SUBMODULES)
def test_public_submodule_available_after_import_hypothesis(name):
    run_python(
        "import sys, hypothesis\n"
        f"assert hypothesis.{name} is sys.modules['hypothesis.{name}']"
    )
    run_python(
        "import sys\n"
        "from hypothesis import *\n"
        f"assert {name} is sys.modules['hypothesis.{name}']"
    )


@skipif_emscripten
@pytest.mark.parametrize("name", _LAZY_SUBMODULES)
def test_lazy_submodule_is_not_imported_by_import_hypothesis(name):
    run_python(
        f"import sys, hypothesis\nassert 'hypothesis.{name}' not in sys.modules"
    )


def test_unknown_attribute_raises_attribute_error():
    with pytest.raises(AttributeError, match="no attribute 'nonexistent'"):
        hypothesis.nonexistent
