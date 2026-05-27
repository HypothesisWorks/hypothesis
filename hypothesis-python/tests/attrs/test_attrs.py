# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import warnings

import attr

from hypothesis import given, strategies as st
from hypothesis.errors import SmallSearchSpaceWarning
from hypothesis.strategies._internal.utils import to_jsonable

from tests.common.debug import check_can_generate_examples


def a_converter(x) -> int:
    return int(x)


@attr.s
class Inferrables:
    annot_converter = attr.ib(converter=a_converter)


@given(st.builds(Inferrables))
def test_attrs_inference_builds(c):
    pass


def test_attrs_inference_from_type():
    s = st.from_type(Inferrables)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SmallSearchSpaceWarning)
        check_can_generate_examples(s)


@attr.s
class AttrsClass:
    n = attr.ib()


def test_jsonable_attrs():
    obj = AttrsClass(n=10)
    assert to_jsonable(obj, avoid_realization=False) == {"n": 10}


def test_hypothesis_is_not_the_first_to_import_attrs(testdir):
    # We only import attrs if the user did so first.

    test_path = testdir.makepyfile(
        """
        import os
        # don't load hypothesis plugins, which might transitively import attrs
        os.environ["HYPOTHESIS_NO_PLUGINS"] = "1"

        import sys
        assert "attrs" not in sys.modules

        from hypothesis import given, strategies as st
        assert "attrs" not in sys.modules

        @given(st.integers() | st.floats() | st.sampled_from(["a", "b"]))
        def test_no_attrs_import(x):
            assert "attrs" not in sys.modules
        """
    )
    # don't load pytest plugins, which might transitively import attrs
    result = testdir.runpytest(test_path, "--disable-plugin-autoload")
    result.assert_outcomes(passed=1, failed=0)
