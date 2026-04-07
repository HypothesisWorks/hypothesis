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
    # This case only exists for tests against Pytest before 5.1.0;
    # see https://github.com/pytest-dev/pytest/commit/a43ba78d3bde
    return junit_xml.findall(f"./{path}")


def suite_properties_ok(junit_xml):
    # Check whether <properties> is included in <testsuite>.  This is currently not
    # the case when using pytest-xdist, which is a shame, but we can live with it.
    testsuite_props = _findall_from_root(junit_xml, "properties")
    return len(testsuite_props) == 1 and {
        prop.get("name") for prop in testsuite_props[0].findall("property")
    } == {
        "hypothesis-statistics-test_outputs_valid_xunit2.py::test_valid",
        "hypothesis-statistics-test_outputs_valid_xunit2.py::test_invalid",
    }


def test_outputs_valid_xunit2(testdir):
    # The thing we really care about with pytest-xdist + junitxml is that we don't
    # break xunit2 compatibility by putting <properties> inside <testcase>.
    junit_xml = _run_and_get_junit(testdir)
    testcase_props = _findall_from_root(junit_xml, "testcase/properties")
    assert len(testcase_props) == 0
    # Check whether <properties> is included in <testsuite>
    assert suite_properties_ok(junit_xml)


def test_outputs_valid_xunit2_with_xdist(testdir):
    junit_xml = _run_and_get_junit(testdir, "-n2")
    testcase_props = _findall_from_root(junit_xml, "testcase/properties")
    assert len(testcase_props) == 0
    # If <properties> is included in <testsuite>, this assertion will fail.
    # That would be a GOOD THING, and we would remove the `not` to prevent regressions.
    assert not suite_properties_ok(junit_xml)
