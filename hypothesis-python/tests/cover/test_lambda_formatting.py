# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import runpy
import sys

import pytest

from hypothesis.internal import lambda_sources
from hypothesis.internal.conjecture.utils import identity
from hypothesis.internal.reflection import get_pretty_function_description

from tests.common.utils import skipif_threading


@pytest.fixture(autouse=True, params=[True, False])
def clear_lambda_caches(request, monkeypatch):
    # Run all tests in this file twice, once using cache and once forcing
    # from-scratch generation
    if request.param:
        monkeypatch.setattr(lambda_sources, "LAMBDA_DESCRIPTION_CACHE", {})
        monkeypatch.setattr(lambda_sources, "LAMBDA_DIGEST_DESCRIPTION_CACHE", {})
        monkeypatch.setattr(lambda_sources, "AST_LAMBDAS_CACHE", {})
    return request.param


def test_bracket_whitespace_is_stripped():
    # fmt: off
    t = lambda x: (x + 1 )
    # fmt: on
    assert get_pretty_function_description(t) == "lambda x: x + 1"


def test_can_have_unicode_in_lambda_sources():
    t = lambda x: "é" not in x
    assert get_pretty_function_description(t) == "lambda x: 'é' not in x"


@pytest.mark.skipif(
    sys.version_info < (3, 11), reason="nested lambdas fail compile-test"
)
def test_can_get_descriptions_of_nested_lambdas_with_different_names():
    # fmt: off
    ordered_pair = (
        lambda right: [].map(
            lambda length: ()))
    # fmt: on
    assert (
        get_pretty_function_description(ordered_pair)
        == "lambda right: [].map(lambda length: ())"
    )


def test_does_not_error_on_unparsable_source():
    # fmt: off
    t = [
        lambda x: \
        # This will break ast.parse, but the brackets are needed for the real
        # parser to accept this lambda
        x][0]
    # fmt: on
    assert get_pretty_function_description(t) == "lambda x: x"


@pytest.mark.skipif(
    sys.version_info < (3, 11), reason="nested lambdas fail compile-test"
)
def test_separate_line_map_filter():
    # this isn't intentionally testing nested lambdas, but hey, it's a nice bonus.
    # fmt: off
    f1 = (
        lambda x: x
        .map(lambda y: y)
    )
    f2 = (
        lambda x: x
        .filter(lambda y: y)
    )
    # fmt: on

    assert get_pretty_function_description(f1) == "lambda x: x.map(lambda y: y)"
    assert get_pretty_function_description(f2) == "lambda x: x.filter(lambda y: y)"


def test_source_of_lambda_is_pretty():
    assert get_pretty_function_description(lambda x: True) == "lambda x: True"


def test_variable_names_are_not_pretty():
    t = lambda x: True
    assert get_pretty_function_description(t) == "lambda x: True"


def test_does_not_error_on_dynamically_defined_functions():
    x = eval("lambda t: 1")
    assert get_pretty_function_description(x) == "lambda t: <unknown>"


def test_collapses_whitespace_nicely():
    # fmt: off
    t = (
        lambda x,       y:           1
    )
    # fmt: on
    assert get_pretty_function_description(t) == "lambda x, y: 1"


def test_is_not_confused_by_tuples():
    p = (lambda x: x > 1, 2)[0]

    assert get_pretty_function_description(p) == "lambda x: x > 1"


def test_strips_comments_from_the_end():
    t = lambda x: 1  # A lambda comment
    assert get_pretty_function_description(t) == "lambda x: 1"


def test_does_not_strip_hashes_within_a_string():
    t = lambda x: "#"
    assert get_pretty_function_description(t) == "lambda x: '#'"


def test_can_distinguish_between_two_lambdas_with_different_args():
    a, b = (lambda x: 1, lambda y: 2)
    assert get_pretty_function_description(a) == "lambda x: 1"
    assert get_pretty_function_description(b) == "lambda y: 2"


def test_can_distinguish_between_two_lambdas_with_different_constants():
    a, b = (lambda x: 1, lambda x: 2)
    assert get_pretty_function_description(a) == "lambda x: 1"
    assert get_pretty_function_description(b) == "lambda x: 2"


def test_can_distinguish_between_two_lambdas_with_different_signatures():
    a, b = (lambda x: x, lambda y: y)
    assert get_pretty_function_description(a) == "lambda x: x"
    assert get_pretty_function_description(b) == "lambda y: y"


def test_can_distinguish_between_two_lambdas_where_one_fails_localparse():
    # fmt: off
    a, b = (
        lambda x: x,
        lambda x: x
        or None,
    )
    # fmt: on
    assert get_pretty_function_description(a) == "lambda x: x"
    assert get_pretty_function_description(b) == "lambda x: x or None"


def test_does_not_get_confused_by_identical_lambdas():
    a, b = (lambda x: 1, lambda x: 1)
    assert get_pretty_function_description(a) == "lambda x: 1"
    assert get_pretty_function_description(b) == "lambda x: 1"


c = 1
lambda_capturing_globals = (lambda: c, lambda: 1)


def test_lambda_capturing_globals():
    assert get_pretty_function_description(lambda_capturing_globals[0]) == "lambda: c"
    assert get_pretty_function_description(lambda_capturing_globals[1]) == "lambda: 1"


def test_lambda_capturing_locals():
    const = 1
    a, b = (lambda: const, lambda: 1)
    assert get_pretty_function_description(a) == "lambda: const"
    assert get_pretty_function_description(b) == "lambda: 1"


def test_can_distinguish_between_two_lambdas_with_different_captures():
    # fmt: off
    a = 1; f1 = lambda x=a: x; a=2; f2=lambda x=a: x  # noqa: E702
    # fmt: on

    assert get_pretty_function_description(f1) == "lambda x=1: x"
    assert get_pretty_function_description(f2) == "lambda x=2: x"


def test_lambda_source_break_after_bracket():
    # Issue #4498 regression test, inspect.getsource only sees the first line
    # fmt: off
    f = (
        lambda x: x
        or None
    )
    # fmt: on

    source = get_pretty_function_description(f)
    assert source == "lambda x: x or None"


def test_lambda_source_break_after_def_with_brackets():
    # fmt: off
    f = (lambda n:
         'aaa')
    # fmt: on

    source = get_pretty_function_description(f)
    assert source == "lambda n: 'aaa'"


def test_lambda_source_break_after_def_with_line_continuation():
    # fmt: off
    f = lambda n:\
        'aaa'
    # fmt: on

    source = get_pretty_function_description(f)
    assert source == "lambda n: 'aaa'"


def arg_decorator(*s):
    def accept(f):
        return s

    return accept


@arg_decorator(lambda x: x + 1)
def plus_one():
    pass


@arg_decorator(lambda x: x + 1, lambda y: y * 2)
def two_decorators():
    pass


def test_can_extract_lambda_repr_in_a_decorator():
    assert get_pretty_function_description(plus_one[0]) == "lambda x: x + 1"


def test_can_extract_two_lambdas_from_a_decorator_if_args_differ():
    a, b = two_decorators
    assert get_pretty_function_description(a) == "lambda x: x + 1"
    assert get_pretty_function_description(b) == "lambda y: y * 2"


@arg_decorator(lambda: ())
def to_brackets():
    pass


def test_can_handle_brackets_in_decorator_argument():
    assert get_pretty_function_description(to_brackets[0]) == "lambda: ()"


@arg_decorator(identity(lambda x: x + 1))
def decorator_with_wrapper():
    pass


def test_can_handle_nested_lambda_in_decorator_argument():
    assert (
        get_pretty_function_description(decorator_with_wrapper[0]) == "lambda x: x + 1"
    )


@skipif_threading  # concurrent writes to the same file
def test_modifying_lambda_source_code_returns_unknown(tmp_path):
    # see https://github.com/HypothesisWorks/hypothesis/pull/4452
    test_module = tmp_path / "test_module.py"
    test_module.write_text(
        "# line one\n\ntest_lambda = lambda x: x * 2", encoding="utf-8"
    )

    module_globals = runpy.run_path(str(test_module))
    test_module.write_text("# line one\n\n# line two", encoding="utf-8")
    assert (
        get_pretty_function_description(module_globals["test_lambda"])
        == "lambda x: <unknown>"
    )


@skipif_threading  # concurrent writes to the same file
def test_adding_other_lambda_does_not_confuse(tmp_path):
    test_module = tmp_path / "test_module.py"
    test_module.write_text(
        "# line one\ntest_lambda = lambda x: x * 2", encoding="utf-8"
    )
    module_globals = runpy.run_path(str(test_module))

    test_module.write_text(
        "# line one\nlambda x: x\n\n\ntest_lambda = lambda x: x * 2", encoding="utf-8"
    )
    f1 = module_globals["test_lambda"]
    assert get_pretty_function_description(f1) == "lambda x: x * 2"


@skipif_threading  # concurrent writes to the same file
def test_changing_lambda_confuses(tmp_path, allow_unknown_lambdas, clear_lambda_caches):
    if not clear_lambda_caches:
        pytest.skip("requires clean cache")
    test_module = tmp_path / "test_module.py"
    test_module.write_text("test_lambda = lambda x: x * 2", encoding="utf-8")
    module_globals = runpy.run_path(str(test_module))

    test_module.write_text("lambda x: x", encoding="utf-8")
    f1 = module_globals["test_lambda"]
    assert get_pretty_function_description(f1) == "lambda x: <unknown>"


@skipif_threading  # concurrent writes to the same file
@pytest.mark.skipif(sys.version_info[:2] < (3, 11), reason="not checked before 3.11")
def test_that_test_harness_raises_on_unknown_lambda(tmp_path):
    test_module = tmp_path / "test_module.py"
    test_module.write_text("test_lambda = lambda x: x * 2", encoding="utf-8")
    module_globals = runpy.run_path(str(test_module))

    test_module.write_text("lambda x: x", encoding="utf-8")
    f1 = module_globals["test_lambda"]
    with pytest.raises(AssertionError):
        assert get_pretty_function_description(f1) == "lambda x: <unknown>"


@skipif_threading  # concurrent writes to the same file
def test_source_with_syntax_error(tmp_path, allow_unknown_lambdas, clear_lambda_caches):
    if not clear_lambda_caches:
        pytest.skip("requires clean cache")
    test_module = tmp_path / "test_module.py"
    test_module.write_text("test_lambda = lambda x: x * 2", encoding="utf-8")
    module_globals = runpy.run_path(str(test_module))
    f1 = module_globals["test_lambda"]

    test_module.write_text("line 1", encoding="utf-8")
    assert get_pretty_function_description(f1) == "lambda x: <unknown>"


@skipif_threading  # concurrent writes to the same file
def test_unknown_is_not_stuck(tmp_path, allow_unknown_lambdas, clear_lambda_caches):
    if not clear_lambda_caches:
        pytest.skip("requires clean cache")
    test_module = tmp_path / "test_module.py"
    test_module.write_text("test_lambda = lambda x: x * 2", encoding="utf-8")
    module_globals = runpy.run_path(str(test_module))
    f1 = module_globals["test_lambda"]

    test_module.write_text("line 1", encoding="utf-8")
    assert get_pretty_function_description(f1) == "lambda x: <unknown>"

    test_module2 = tmp_path / "test_module2.py"
    test_module2.write_text("test_lambda = lambda x: x * 2", encoding="utf-8")
    module_globals2 = runpy.run_path(str(test_module2))
    f2 = module_globals2["test_lambda"]

    # f2 matches f1 in the digest cache, ensure that it gets a proper description
    assert get_pretty_function_description(f1) == "lambda x: <unknown>"
    assert get_pretty_function_description(f2) == "lambda x: x * 2"
