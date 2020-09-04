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

import ast
import json
import re
import subprocess

import pytest

from hypothesis.errors import StopTest
from hypothesis.extra.ghostwriter import equivalent, fuzz, idempotent, roundtrip


@pytest.mark.parametrize(
    "cli,code",
    [
        # Passing one argument falls back to one-argument tests
        ("--equivalent re.compile", lambda: fuzz(re.compile)),
        ("--roundtrip sorted", lambda: idempotent(sorted)),
        # For multiple arguments, they're equivalent to the function call
        (
            "--equivalent eval ast.literal_eval",
            lambda: equivalent(eval, ast.literal_eval),
        ),
        (
            "--roundtrip json.loads json.dumps --except ValueError",
            lambda: roundtrip(json.loads, json.dumps, except_=ValueError),
        ),
        # Imports submodule (importlib.import_module passes; __import__ fails)
        ("hypothesis.errors.StopTest", lambda: fuzz(StopTest)),
    ],
)
def test_cli_python_equivalence(cli, code):
    result = subprocess.run(
        "hypothesis write " + cli,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        shell=True,
        universal_newlines=True,
    )
    cli_output = result.stdout.strip()
    assert not result.stderr
    code_output = code().strip()
    assert code_output == cli_output
    result.check_returncode()


@pytest.mark.parametrize(
    "cli,err_msg",
    [
        ("--idempotent sorted sorted", "Test functions for idempotence one at a time."),
        (
            "xxxx",
            "Found the 'builtins' module, but it doesn't have a 'xxxx' attribute.",
        ),
        (
            "re.srch",
            "Found the 're' module, but it doesn't have a 'srch' attribute.  "
            "Closest matches: ['search']",
        ),
        (
            "re.fmatch",
            "Found the 're' module, but it doesn't have a 'fmatch' attribute.  "
            "Closest matches: ['match', 'fullmatch'",
            # Python >= 3.7 has 'Match' objects too
        ),
    ],
)
def test_cli_too_many_functions(cli, err_msg):
    # Supplying multiple functions to writers that only cope with one
    result = subprocess.run(
        "hypothesis write " + cli,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        shell=True,
        universal_newlines=True,
    )
    assert result.returncode == 2
    assert "Error: " + err_msg in result.stderr
    assert ("Closest matches" in err_msg) == ("Closest matches" in result.stderr)


CODE_TO_TEST = """
from typing import Sequence, List

def sorter(seq: Sequence[int]) -> List[int]:
    return sorted(seq)
"""


def test_can_import_from_scripts_in_working_dir(tmpdir):
    (tmpdir / "mycode.py").write(CODE_TO_TEST)
    result = subprocess.run(
        "hypothesis write mycode.sorter",
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        shell=True,
        universal_newlines=True,
        cwd=tmpdir,
    )
    assert result.returncode == 0
    assert "Error: " not in result.stderr


def test_empty_module_is_not_error(tmpdir):
    (tmpdir / "mycode.py").write("# Nothing to see here\n")
    result = subprocess.run(
        "hypothesis write mycode",
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        shell=True,
        universal_newlines=True,
        cwd=tmpdir,
    )
    assert result.returncode == 0
    assert "Error: " not in result.stderr
    assert "# Found no testable functions" in result.stdout
