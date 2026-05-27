# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import re
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
    print(ci_checks)
    assert f"- check-py{slug}" in ci_checks, f"Add {version} to main.yml and tox.ini"


def test_python_versions_are_in_trove_classifiers():
    got_classifiers = {
        line.strip(' ",\n')
        for line in Path("hypothesis-python/pyproject.toml")
        .read_text(encoding="utf-8")
        .splitlines()
        if "Programming Language :: Python :: 3." in line
    }
    expected_classifiers = {
        f"Programming Language :: Python :: 3.{v.split('.')[1]}"
        for v in PYTHONS.values()
        if re.fullmatch(r"3\.\d+\.\d+", v)
    }
    assert got_classifiers == expected_classifiers
