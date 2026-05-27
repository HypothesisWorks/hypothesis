# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import json
import os
import subprocess
import sys

from hypothesistooling.projects.hypothesispython import BASE_DIR

BRANCH_CHECK = "branch-check"
VALIDATE_BRANCH_CHECK = os.path.join(BASE_DIR, "scripts", "validate_branch_check.py")


def write_entries(tmp_path, entries):
    with open(tmp_path / BRANCH_CHECK, "w", encoding="utf-8") as f:
        f.writelines([json.dumps(entry) + "\n" for entry in entries])


def run_validate_branch_check(tmp_path, *, check, **kwargs):
    return subprocess.run(
        [sys.executable, VALIDATE_BRANCH_CHECK],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=check,
        **kwargs,
    )


def test_validates_branches(tmp_path):
    write_entries(
        tmp_path,
        [
            {"name": name, "value": value}
            for name in ("first", "second", "third")
            for value in (False, True)
        ],
    )

    output = run_validate_branch_check(tmp_path, check=True)
    assert output.stdout == "Successfully validated 3 branches.\n"


def test_validates_one_branch(tmp_path):
    write_entries(
        tmp_path, [{"name": "sole", "value": value} for value in (False, True)]
    )

    output = run_validate_branch_check(tmp_path, check=True)
    assert output.stdout == "Successfully validated 1 branch.\n"


def test_fails_on_zero_branches(tmp_path):
    write_entries(tmp_path, [])

    output = run_validate_branch_check(tmp_path, check=False)
    assert output.returncode == 1
    assert output.stdout == "No branches found in the branch-check file?\n"


def test_reports_uncovered_branches(tmp_path):
    write_entries(
        tmp_path,
        [
            {"name": "branch that is always taken", "value": True},
            {"name": "some other branch that is never taken", "value": False},
            {"name": "covered branch", "value": True},
            {"name": "covered branch", "value": False},
        ],
    )

    output = run_validate_branch_check(tmp_path, check=False)
    assert output.returncode == 1
    expected = """\
Some branches were not properly covered.

The following were always True:
  * branch that is always taken

The following were always False:
  * some other branch that is never taken
"""
    assert output.stdout == expected
