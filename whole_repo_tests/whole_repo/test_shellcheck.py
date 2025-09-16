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

import hypothesistooling as tools
from hypothesistooling import installers as install

SCRIPTS = [f for f in tools.all_files() if f.endswith(".sh")]


def test_all_shell_scripts_are_valid():
    subprocess.check_call(
        [install.SHELLCHECK, "--exclude=SC1073,SC1072", *SCRIPTS], cwd=tools.ROOT
    )
