# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import ast
import json
import operator
import re
import subprocess

import pytest

from hypothesis.errors import StopTest
from hypothesis.extra.ghostwriter import (
    binary_operation,
    equivalent,
    fuzz,
    idempotent,
    roundtrip,
)


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
        # Search for identity element does not print e.g. "You can use @seed ..."
        ("--binary-op operator.add", lambda: binary_operation(operator.add)),
    ],
)
def test_cli_python_equivalence(cli, code):
    result = subprocess.run(
        "hypothesis write " + cli,
        capture_output=True,
        shell=True,
        text=True,
    )
    result.check_returncode()
    cli_output = result.stdout.strip()
    assert not result.stderr
    code_output = code().strip()
    assert code_output == cli_output


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
        capture_output=True,
        shell=True,
        text=True,
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
        capture_output=True,
        shell=True,
        text=True,
        cwd=tmpdir,
    )
    assert result.returncode == 0
    assert "Error: " not in result.stderr


CLASS_CODE_TO_TEST = """
from typing import Sequence, List

def func_sorter(seq: Sequence[int]) -> List[int]:
    return sorted(seq)

class S:

    @staticmethod
    def static_sorter(seq: Sequence[int]) -> List[int]:
        return sorted(seq)

    @classmethod
    def class_sorter(seq: Sequence[int]) -> List[int]:
        return sorted(seq)
"""


@pytest.mark.parametrize("func", ["static_sorter", "class_sorter"])
def test_can_import_from_class(tmpdir, func):
    (tmpdir / "mycode_class.py").write(CLASS_CODE_TO_TEST)
    result = subprocess.run(
        f"hypothesis write mycode_class.S.{func}",
        capture_output=True,
        shell=True,
        text=True,
        cwd=tmpdir,
    )
    assert result.returncode == 0
    assert "Error: " not in result.stderr


@pytest.mark.parametrize(
    "classname,funcname,err_msg",
    [
        (
            "XX",
            "XX",
            "Found the 'mycode_class' module, but it doesn't have a 'XX' class.",
        ),
        (
            "S",
            "XX",
            "Found the 'mycode_class' module and 'S' class, but it doesn't have a 'XX' attribute.",
        ),
        (
            "func_sorter",
            "XX",
            "Found the 'mycode_class' module and 'func_sorter' attribute, but it doesn't have a 'XX' attribute.",
        ),
    ],
)
def test_error_import_from_class(tmpdir, classname, funcname, err_msg):
    (tmpdir / "mycode_class.py").write(CLASS_CODE_TO_TEST)
    result = subprocess.run(
        f"hypothesis write mycode_class.{classname}.{funcname}",
        capture_output=True,
        shell=True,
        text=True,
        cwd=tmpdir,
    )
    assert result.returncode == 2
    assert "Error: " + err_msg in result.stderr


def test_empty_module_is_not_error(tmpdir):
    (tmpdir / "mycode.py").write("# Nothing to see here\n")
    result = subprocess.run(
        "hypothesis write mycode",
        capture_output=True,
        shell=True,
        text=True,
        cwd=tmpdir,
    )
    assert result.returncode == 0
    assert "Error: " not in result.stderr
    assert "# Found no testable functions" in result.stdout
