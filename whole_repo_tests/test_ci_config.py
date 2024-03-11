# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from pathlib import Path

import pytest

from hypothesistooling.__main__ import PYTHONS

ci_checks = "    ".join(
    line.strip()
    for line in Path(".github/workflows/main.yml")
    .read_text(encoding="utf-8")
    .splitlines()
    if "- check-py" in line
)


@pytest.mark.parametrize("version", sorted(PYTHONS))
def test_python_versions_are_tested_in_ci(version):
    slug = version.replace("pypy", "py").replace(".", "")
    assert f"- check-py{slug}" in ci_checks, f"Add {version} to main.yml and tox.ini"
