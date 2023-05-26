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
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest

from hypothesis.extra._patching import HEADER, get_patch_for, indent, make_patch

from .callables import WHERE, Cases, fn

SIMPLE = (
    fn,
    "fn(\n    x=1,\n)",
    indent('@example(x=1).via("discovered failure")', prefix="+"),
)
CASES = (
    Cases.mth,
    'mth(\n    n=100,\n    label="a long label which forces a newline",\n)',
    indent(
        '@example(n=100, label="a long label which forces a newline")'
        '.via(\n    "discovered failure"\n)',
        prefix="+    ",
    ),
)


def strip_trailing_whitespace(s):
    """Patches have whitespace-only lines; strip that out."""
    return re.sub(r" +$", "", s, flags=re.MULTILINE)


@pytest.mark.parametrize(
    "tst, example, expected",
    [
        pytest.param(*SIMPLE, id="simple"),
        pytest.param(*CASES, id="cases"),
    ],
)
def test_adds_simple_patch(tst, example, expected):
    where, before, after = get_patch_for(tst, [example])
    assert Path(where) == WHERE
    added = set(after.splitlines()) - set(before.splitlines())
    assert added == {line.lstrip("+") for line in expected.splitlines()}


SIMPLE_PATCH_BODY = f'''\
--- {WHERE}
+++ {WHERE}
@@ -18,6 +18,7 @@


 @given(st.integers())
{{0}}
 def fn(x):
     """A trivial test function."""

'''
CASES_PATCH_BODY = f'''\
--- {WHERE}
+++ {WHERE}
@@ -25,6 +25,9 @@
 class Cases:
     @example(n=0, label="whatever")
     @given(st.integers(), st.text())
{{0}}
     def mth(self, n, label):
         """Indented method with existing example decorator."""

'''


@pytest.mark.parametrize(
    "tst, example, expected, body",
    [
        pytest.param(*SIMPLE, SIMPLE_PATCH_BODY, id="simple"),
        pytest.param(*CASES, CASES_PATCH_BODY, id="cases"),
    ],
)
def test_make_full_patch(tst, example, expected, body):
    when = datetime.now()
    msg = "a message from the test"
    expected = HEADER.format(when=when, msg=msg) + body.format(expected)

    triple = get_patch_for(tst, [example])
    got = make_patch([triple], when=when, msg=msg)
    stripped = strip_trailing_whitespace(got)

    assert stripped.splitlines() == expected.splitlines()


@pytest.mark.parametrize("n", [0, 1, 2])
def test_invalid_syntax_cases_dropped(n):
    tst, example, expected = SIMPLE
    example_ls = [example] * n
    example_ls.insert(-1, "fn(\n    x=<__main__.Cls object at 0x>,\n)")

    got = get_patch_for(tst, example_ls)
    if n == 0:
        assert got is None, "no valid examples, and hence no patch"
        return
    where, _, after = got

    assert Path(where) == WHERE
    assert after.count(expected.lstrip("+")) == n


def test_irretrievable_callable():
    # Check that we return None instead of raising an exception
    tst = deepcopy(fn)
    tst.__module__ = "this.does.not.exist"
    triple = get_patch_for(tst, [SIMPLE[1]])
    assert triple is None
