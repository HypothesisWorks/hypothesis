# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import xml.etree.ElementTree as ET
from pathlib import Path

pytest_plugins = "pytester"


TESTSUITE = """
from hypothesis import given
from hypothesis.strategies import integers

@given(integers())
def test_valid(x):
    assert x == x

@given(integers())
def test_invalid(x):
    assert x != x
"""


def _run_and_get_junit(testdir, *args):
    script = testdir.makepyfile(TESTSUITE)
    testdir.runpytest(script, "--junit-xml=out.xml", *args)
    return ET.parse(Path(testdir.tmpdir) / "out.xml").getroot()


def _findall_from_root(junit_xml, path):
    if junit_xml.tag == "testsuites":
        return junit_xml.findall(f"./testsuite/{path}")
    else:
        # < pytest 5.1.0
        # https://github.com/pytest-dev/pytest/commit/a43ba78d3bde1630a42aaa95776687d3886891e6
        return junit_xml.findall(f"./{path}")


def test_outputs_valid_xunit2(testdir):
    junit_xml = _run_and_get_junit(testdir)

    testsuite_props = _findall_from_root(junit_xml, "properties")
    assert len(testsuite_props) == 1
    assert {prop.get("name") for prop in testsuite_props[0].findall("property")} == {
        "hypothesis-statistics-test_outputs_valid_xunit2.py::test_valid",
        "hypothesis-statistics-test_outputs_valid_xunit2.py::test_invalid",
    }

    testcase_props = _findall_from_root(junit_xml, "testcase/properties")
    assert len(testcase_props) == 0


def test_outputs_valid_xunit2_with_xdist(testdir):
    junit_xml = _run_and_get_junit(testdir, "-n2")

    testcase_props = _findall_from_root(junit_xml, "testcase/properties")
    assert len(testcase_props) == 0
