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
import itertools
import json
import operator
import re
import subprocess
import sys

import pytest

from hypothesis import strategies as st
from hypothesis.errors import StopTest
from hypothesis.extra.ghostwriter import (
    binary_operation,
    equivalent,
    fuzz,
    idempotent,
    magic,
    roundtrip,
)
from hypothesis.internal.reflection import get_pretty_function_description


def run(cmd, *, cwd=None):
    return subprocess.run(
        cmd, capture_output=True, shell=True, text=True, cwd=cwd, encoding="utf-8"
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
        pytest.param(
            "hypothesis.strategies",
            lambda: magic(st),
            marks=pytest.mark.skipif(sys.version_info[:2] != (3, 10), reason="varies"),
        ),
        # We can write tests for classes even without classmethods or staticmethods
        ("hypothesis.errors.StopTest", lambda: fuzz(StopTest)),
        # Search for identity element does not print e.g. "You can use @seed ..."
        ("--binary-op operator.add", lambda: binary_operation(operator.add)),
        # Annotations are passed correctly
        ("sorted --annotate", lambda: fuzz(sorted, annotate=True)),
        ("sorted --no-annotate", lambda: fuzz(sorted, annotate=False)),
    ],
    ids=get_pretty_function_description,
)
def test_cli_python_equivalence(cli, code):
    result = run("hypothesis write " + cli)
    result.check_returncode()
    cli_output = result.stdout.strip()
    assert cli == "hypothesis.strategies" or not result.stderr
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
    result = run("hypothesis write " + cli)
    assert result.returncode == 2
    assert "Error: " + err_msg in result.stderr
    assert ("Closest matches" in err_msg) == ("Closest matches" in result.stderr)


CODE_TO_TEST = """
from typing import Sequence, List

def sorter(seq: Sequence[int]) -> List[int]:
    return sorted(seq)
"""


def test_can_import_from_scripts_in_working_dir(tmp_path):
    (tmp_path / "mycode.py").write_text(CODE_TO_TEST, encoding="utf-8")
    result = run("hypothesis write mycode.sorter", cwd=tmp_path)
    assert result.returncode == 0
    assert "Error: " not in result.stderr


CLASS_CODE_TO_TEST = """
from typing import Sequence, List

def my_func(seq: Sequence[int]) -> List[int]:
    return sorted(seq)

class MyClass:

    @staticmethod
    def my_staticmethod(seq: Sequence[int]) -> List[int]:
        return sorted(seq)

    @classmethod
    def my_classmethod(cls, seq: Sequence[int]) -> List[int]:
        return sorted(seq)
"""


@pytest.mark.parametrize("func", ["my_staticmethod", "my_classmethod"])
def test_can_import_from_class(tmp_path, func):
    (tmp_path / "mycode.py").write_text(CLASS_CODE_TO_TEST, encoding="utf-8")
    result = run(f"hypothesis write mycode.MyClass.{func}", cwd=tmp_path)
    assert result.returncode == 0
    assert "Error: " not in result.stderr


@pytest.mark.parametrize(
    "classname,thing,kind",
    [
        ("XX", "", "class"),
        ("MyClass", " and 'MyClass' class", "attribute"),
        ("my_func", " and 'my_func' attribute", "attribute"),
    ],
)
def test_error_import_from_class(tmp_path, classname, thing, kind):
    (tmp_path / "mycode.py").write_text(CLASS_CODE_TO_TEST, encoding="utf-8")
    result = run(f"hypothesis write mycode.{classname}.XX", cwd=tmp_path)
    msg = f"Error: Found the 'mycode' module{thing}, but it doesn't have a 'XX' {kind}."
    assert result.returncode == 2
    assert msg in result.stderr


def test_magic_discovery_from_module(tmp_path):
    (tmp_path / "mycode.py").write_text(CLASS_CODE_TO_TEST, encoding="utf-8")
    result = run("hypothesis write mycode", cwd=tmp_path)
    assert result.returncode == 0
    assert "my_func" in result.stdout
    assert "MyClass.my_staticmethod" in result.stdout
    assert "MyClass.my_classmethod" in result.stdout


ROUNDTRIP_CODE_TO_TEST = """
from typing import Union
import json

def to_json(json: Union[dict,list]) -> str:
    return json.dumps(json)

def from_json(json: str) -> Union[dict,list]:
    return json.loads(json)

class MyClass:

    @staticmethod
    def to_json(json: Union[dict,list]) -> str:
        return json.dumps(json)

    @staticmethod
    def from_json(json: str) -> Union[dict,list]:
        return json.loads(json)

class OtherClass:

    @classmethod
    def to_json(cls, json: Union[dict,list]) -> str:
        return json.dumps(json)

    @classmethod
    def from_json(cls, json: str) -> Union[dict,list]:
        return json.loads(json)
"""


def test_roundtrip_correct_pairs(tmp_path):
    (tmp_path / "mycode.py").write_text(ROUNDTRIP_CODE_TO_TEST, encoding="utf-8")
    result = run("hypothesis write mycode", cwd=tmp_path)
    assert result.returncode == 0
    for scope1, scope2 in itertools.product(
        ["mycode.MyClass", "mycode.OtherClass", "mycode"], repeat=2
    ):
        round_trip_code = f"""value0 = {scope1}.to_json(json=json)
    value1 = {scope2}.from_json(json=value0)"""
        if scope1 == scope2:
            assert round_trip_code in result.stdout
        else:
            assert round_trip_code not in result.stdout


def test_empty_module_is_not_error(tmp_path):
    (tmp_path / "mycode.py").write_text("# Nothing to see here\n", encoding="utf-8")
    result = run("hypothesis write mycode", cwd=tmp_path)
    assert result.returncode == 0
    assert "Error: " not in result.stderr
    assert "# Found no testable functions" in result.stdout
