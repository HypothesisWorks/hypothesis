# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import base64
import re
import zlib

import pytest

from hypothesis import (
    Verbosity,
    __version__,
    example,
    given,
    reject,
    reproduce_failure,
    settings,
    strategies as st,
)
from hypothesis.core import decode_failure, encode_failure
from hypothesis.errors import DidNotReproduce, InvalidArgument, UnsatisfiedAssumption
from hypothesis.internal.conjecture.choice import choice_equal

from tests.common.utils import Why, capture_out, no_shrink, xfail_on_crosshair
from tests.conjecture.common import nodes, nodes_inline


@example(nodes_inline("0" * 100))  # shorter compressed than not
@given(st.lists(nodes()))
def test_encoding_loop(nodes):
    choices = [n.value for n in nodes]
    looped = decode_failure(encode_failure(choices))
    assert len(choices) == len(looped)
    for pre, post in zip(choices, looped):
        assert choice_equal(pre, post)


@example(base64.b64encode(b"\2\3\4"))
@example(b"\t")
@example(base64.b64encode(b"\1\0"))  # zlib error
@example(base64.b64encode(b"\1" + zlib.compress(b"\xff")))  # choices_from_bytes error
@given(st.binary())
def test_decoding_may_fail(t):
    try:
        decode_failure(t)
        reject()
    except UnsatisfiedAssumption:
        raise  # don't silence the reject()
    except InvalidArgument:
        pass
    except Exception as e:
        raise AssertionError("Expected an InvalidArgument exception") from e


def test_invalid_base_64_gives_invalid_argument():
    with pytest.raises(InvalidArgument) as exc_info:
        decode_failure(b"/")
    assert "Invalid base64 encoded" in exc_info.value.args[0]


def test_reproduces_the_failure():
    b = b"hello world"
    n = len(b)

    @reproduce_failure(__version__, encode_failure([b]))
    @given(st.binary(min_size=n, max_size=n))
    def test_outer(x):
        assert x != b

    @given(st.binary(min_size=n, max_size=n))
    @reproduce_failure(__version__, encode_failure([b]))
    def test_inner(x):
        assert x != b

    with pytest.raises(AssertionError):
        test_outer()
    with pytest.raises(AssertionError):
        test_inner()


def test_errors_if_provided_example_does_not_reproduce_failure():
    b = b"hello world"
    n = len(b)

    @reproduce_failure(__version__, encode_failure([b]))
    @given(st.binary(min_size=n, max_size=n))
    def test(x):
        assert x == b

    with pytest.raises(DidNotReproduce):
        test()


def test_errors_with_did_not_reproduce_if_the_shape_changes():
    b = b"hello world"
    n = len(b)

    @reproduce_failure(__version__, encode_failure([b]))
    @given(st.binary(min_size=n, max_size=n) | st.integers())
    def test(v):
        assert v == b

    with pytest.raises(DidNotReproduce):
        test()


def test_errors_with_did_not_reproduce_if_rejected():
    b = b"hello world"
    n = len(b)

    @reproduce_failure(__version__, encode_failure([b]))
    @given(st.binary(min_size=n, max_size=n))
    def test(x):
        reject()

    with pytest.raises(DidNotReproduce):
        test()


@xfail_on_crosshair(Why.symbolic_outside_context)
def test_prints_reproduction_if_requested():
    failing_example = None

    @settings(print_blob=True, database=None, max_examples=100)
    @given(st.integers())
    def test(i):
        nonlocal failing_example
        if failing_example is None and i != 0:
            failing_example = i
        assert i != failing_example

    with pytest.raises(AssertionError) as err:
        test()
    notes = "\n".join(err.value.__notes__)
    assert "@reproduce_failure" in notes

    exp = re.compile(r"reproduce_failure\(([^)]+)\)", re.MULTILINE)
    extract = exp.search(notes)
    reproduction = eval(extract.group(0))
    test = reproduction(test)

    with pytest.raises(AssertionError):
        test()


def test_does_not_print_reproduction_for_simple_examples_by_default():
    @settings(print_blob=False)
    @given(st.integers())
    def test(i):
        raise AssertionError

    with capture_out() as o:
        with pytest.raises(AssertionError):
            test()
    assert "@reproduce_failure" not in o.getvalue()


def test_does_not_print_reproduction_for_simple_data_examples_by_default():
    @settings(print_blob=False)
    @given(st.data())
    def test(data):
        data.draw(st.integers())
        raise AssertionError

    with capture_out() as o:
        with pytest.raises(AssertionError):
            test()
    assert "@reproduce_failure" not in o.getvalue()


def test_does_not_print_reproduction_for_large_data_examples_by_default():
    @settings(phases=no_shrink, print_blob=False)
    @given(st.data())
    def test(data):
        b = data.draw(st.binary(min_size=1000, max_size=1000))
        if len(zlib.compress(b)) > 1000:
            raise ValueError

    with capture_out() as o:
        with pytest.raises(ValueError):
            test()
    assert "@reproduce_failure" not in o.getvalue()


class Foo:
    def __repr__(self):
        return "not a valid python expression"


def test_does_not_print_reproduction_if_told_not_to():
    @settings(print_blob=False)
    @given(st.integers().map(lambda x: Foo()))
    def test(i):
        raise ValueError

    with capture_out() as o:
        with pytest.raises(ValueError):
            test()

    assert "@reproduce_failure" not in o.getvalue()


def test_raises_invalid_if_wrong_version():
    b = b"hello world"
    n = len(b)

    @reproduce_failure("1.0.0", encode_failure([b]))
    @given(st.binary(min_size=n, max_size=n))
    def test(x):
        pass

    with pytest.raises(InvalidArgument):
        test()


def test_does_not_print_reproduction_if_verbosity_set_to_quiet():
    @given(st.data())
    @settings(verbosity=Verbosity.quiet, print_blob=False)
    def test_always_fails(data):
        assert data.draw(st.just(False))

    with capture_out() as out:
        with pytest.raises(AssertionError):
            test_always_fails()

    assert "@reproduce_failure" not in out.getvalue()
