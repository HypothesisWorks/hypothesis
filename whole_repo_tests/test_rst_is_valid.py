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

import hypothesistooling as tools
from hypothesistooling.projects import hypothesispython as hp
from hypothesistooling.scripts import pip_tool


def is_sphinx(f):
    f = os.path.abspath(f)
    return f.startswith(os.path.join(hp.HYPOTHESIS_PYTHON, "docs"))


ALL_RST = [
    f
    for f in tools.all_files()
    if os.path.basename(f) not in ["RELEASE.rst", "RELEASE-sample.rst"]
    and f.endswith(".rst")
]


def test_passes_rst_lint():
    pip_tool("rst-lint", *(f for f in ALL_RST if not is_sphinx(f)))


def disabled_test_passes_flake8():
    # TODO: get these whitespace checks without flake8?
    pip_tool("flake8", "--select=W191,W291,W292,W293,W391", *ALL_RST)
