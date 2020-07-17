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
    if os.path.basename(f) != "RELEASE.rst" and f.endswith(".rst")
]


def test_passes_rst_lint():
    pip_tool("rst-lint", *[f for f in ALL_RST if not is_sphinx(f)])


def test_passes_flake8():
    pip_tool("flake8", "--select=W191,W291,W292,W293,W391", *ALL_RST)
