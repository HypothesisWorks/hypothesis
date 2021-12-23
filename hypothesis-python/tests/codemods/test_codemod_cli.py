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

BEFORE = """
from hypothesis.strategies import complex_numbers, complex_numbers as cn

complex_numbers(min_magnitude=None)  # simple call to fix
complex_numbers(min_magnitude=None, max_magnitude=1)  # plus arg after
complex_numbers(allow_infinity=False, min_magnitude=None)  # plus arg before
cn(min_magnitude=None)  # imported as alias
"""
AFTER = BEFORE.replace("None", "0")
_unchanged = """
complex_numbers(min_magnitude=1)  # value OK

class Foo:
    def complex_numbers(self, **kw): pass

    complex_numbers(min_magnitude=None)  # defined in a different scope
"""
BEFORE += _unchanged
AFTER += _unchanged
del _unchanged


def run(command, tmpdir=None, input=None):
    return subprocess.run(
        command,
        input=input,
        capture_output=True,
        shell=True,
        text=True,
        cwd=tmpdir,
    )


def test_codemod_single_file(tmpdir):
    fname = tmpdir / "mycode.py"
    fname.write(BEFORE)
    result = run("hypothesis codemod mycode.py", tmpdir)
    assert result.returncode == 0
    assert fname.read() == AFTER


def test_codemod_multiple_files(tmpdir):
    # LibCST had some trouble with multiprocessing on Windows
    files = [tmpdir / "mycode1.py", tmpdir / "mycode2.py"]
    for f in files:
        f.write(BEFORE)
    result = run("hypothesis codemod mycode1.py mycode2.py", tmpdir)
    assert result.returncode == 0
    for f in files:
        assert f.read() == AFTER


def test_codemod_from_stdin():
    result = run("hypothesis codemod -", input=BEFORE)
    assert result.returncode == 0
    assert result.stdout.rstrip() == AFTER.rstrip()
