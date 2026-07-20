# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis import Phase, example, given, settings, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.internal.compat import BaseExceptionGroup

from tests.common.utils import capture_out

pytestmark = pytest.mark.skipif(
    settings().backend == "crosshair", reason="cannot _invert symbolic values"
)


def output_from_failure(test):
    with capture_out() as out, pytest.raises(AssertionError) as exc_info:
        test()
    notes = "\n".join(getattr(exc_info.value, "__notes__", []))
    return out.getvalue() + str(exc_info.value) + "\n" + notes


def test_shrinks_failing_explicit_example():
    @example(x=[1, 2, 3, 4, 5, 6, 7, 8, 9]).shrink()
    @given(st.lists(st.integers()))
    @settings(phases=[Phase.explicit, Phase.shrink], database=None)
    def test(x):
        assert 7 not in x

    out = output_from_failure(test)
    assert "Falsifying example: test(\n    x=[7],\n)" in out
    assert "Falsifying explicit example" not in out


def test_shrinks_multiple_arguments():
    @example(x=[10, 20, 30], y="irrelevant").shrink()
    @given(x=st.lists(st.integers()), y=st.text())
    @settings(phases=[Phase.explicit, Phase.shrink], database=None)
    def test(x, y):
        assert sum(x) < 25

    out = output_from_failure(test)
    assert "x=[25]" in out
    assert "y=''" in out


def test_shrinks_json_like_recursive_example():
    # A JSON-ish strategy (minus dicts: st.dictionaries builds unique lists of
    # key-value pairs via tuple_suffixes and .map(dict), which inversion
    # cannot re-encode).
    json_ish = st.recursive(
        st.none() | st.booleans() | st.floats(allow_nan=False) | st.text(),
        st.lists,
    )

    def contains_needle(v):
        if isinstance(v, str):
            return "needle" in v
        if isinstance(v, list):
            return any(map(contains_needle, v))
        return False

    blob = [
        "ignore me",
        [[3.5, None, ["hello needle world", 0.0]], True],
        ["deep", [["needle in a haystack"], False]],
    ]

    @example(value=blob).shrink()
    @given(json_ish)
    @settings(phases=[Phase.explicit, Phase.shrink], database=None, deadline=None)
    def test(value):
        assert not contains_needle(value)

    out = output_from_failure(test)
    assert "value='needle'" in out


def test_falls_back_to_unshrunk_report_for_uninvertible_arguments():
    @example(x=10).shrink()
    @given(st.integers().map(lambda x: x * 2))
    @settings(phases=[Phase.explicit, Phase.shrink], database=None)
    def test(x):
        assert x != 10

    out = output_from_failure(test)
    assert "Falsifying explicit example: test(\n    x=10,\n)" in out


def test_reports_other_failures_surfaced_while_shrinking():
    # Shrinking x=1200 towards zero tries x=0, hitting the second assertion:
    # a genuinely different bug, which is reported alongside the expected one.
    @example(x=1200).shrink()
    @given(st.integers())
    @settings(phases=[Phase.explicit, Phase.shrink], database=None)
    def test(x):
        assert x <= 1000
        assert x != 0

    with pytest.raises(BaseExceptionGroup) as exc_info:
        test()
    assert len(exc_info.value.exceptions) == 2
    notes = "\n".join(
        "\n".join(getattr(e, "__notes__", [])) for e in exc_info.value.exceptions
    )
    assert "x=1001" in notes
    assert "x=0" in notes


def test_falls_back_when_replay_does_not_reproduce():
    calls = []

    @example(x=0).shrink()
    @given(st.integers())
    @settings(phases=[Phase.explicit, Phase.shrink], database=None)
    def test(x):
        calls.append(x)
        # fails only on the very first call, so the re-encoded replay passes
        assert len(calls) > 1

    out = output_from_failure(test)
    assert "Falsifying explicit example: test(\n    x=0,\n)" in out


def test_falls_back_when_shrink_phase_is_disabled():
    @example(x=[1, 2, 3, 4, 5, 6, 7, 8, 9]).shrink()
    @given(st.lists(st.integers()))
    @settings(phases=[Phase.explicit], database=None)
    def test(x):
        assert 7 not in x

    out = output_from_failure(test)
    assert "Falsifying explicit example" in out


def test_shrink_does_nothing_for_passing_examples():
    @example(x=[1]).shrink()
    @given(st.lists(st.integers()))
    @settings(phases=[Phase.explicit], database=None)
    def test(x):
        pass

    test()


def test_shrunk_example_reports_reproduce_failure_blob():
    @example(x=[1, 2, 3, 4, 5, 6, 7, 8, 9]).shrink()
    @given(st.lists(st.integers()))
    @settings(phases=[Phase.explicit, Phase.shrink], database=None, print_blob=True)
    def test(x):
        assert 7 not in x

    out = output_from_failure(test)
    assert "@reproduce_failure" in out
    assert "x=[7]" in out


def test_shrink_cannot_be_combined_with_xfail():
    with pytest.raises(InvalidArgument, match="Cannot combine"):
        example(x=1).xfail().shrink()
    with pytest.raises(InvalidArgument, match="Cannot combine"):
        example(x=1).shrink().xfail()
    # ...but an xfail whose condition is False is inert, and allowed
    example(x=1).xfail(condition=False).shrink()
    example(x=1).shrink().xfail(condition=False)


def test_shrink_is_idempotent():
    @example(x=[7, 8, 9]).shrink().shrink()
    @given(st.lists(st.integers()))
    @settings(phases=[Phase.explicit, Phase.shrink], database=None)
    def test(x):
        assert 7 not in x

    out = output_from_failure(test)
    assert "x=[7]" in out
