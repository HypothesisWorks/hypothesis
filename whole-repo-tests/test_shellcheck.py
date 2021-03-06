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

import subprocess

import hypothesistooling as tools
from hypothesistooling import installers as install

SCRIPTS = [f for f in tools.all_files() if f.endswith(".sh")]


def test_all_shell_scripts_are_valid():
    subprocess.check_call(
        [install.SHELLCHECK, "--exclude=SC1073,SC1072", *SCRIPTS], cwd=tools.ROOT
    )
