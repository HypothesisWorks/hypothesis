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
import enum
import json
import re
import socket
import unittest
import unittest.mock
from collections.abc import KeysView, Sequence, Sized, ValuesView
from decimal import Decimal
from pathlib import Path
from textwrap import dedent
from types import FunctionType, ModuleType
from typing import Any, Union

import attr
import click
import pytest

from hypothesis import HealthCheck, assume, settings
from hypothesis.errors import InvalidArgument, Unsatisfiable
from hypothesis.extra import cli, ghostwriter
from hypothesis.internal.compat import BaseExceptionGroup
from hypothesis.strategies import builds, from_type, just, lists
from hypothesis.strategies._internal.core import from_regex
from hypothesis.strategies._internal.lazy import LazyStrategy

varied_excepts = pytest.mark.parametrize("ex", [(), ValueError, (TypeError, re.error)])


def get_test_function(source_code, settings_decorator=lambda fn: fn):
    # A helper function to get the dynamically-defined test function.
    # Note that this also tests that the module is syntatically-valid,
    # AND free from undefined names, import problems, and so on.
    namespace = {}
    try:
        exec(source_code, namespace)
    except Exception:
        print(f"************\n{source_code}\n************")
        raise
    tests = [
        v
        for k, v in namespace.items()
        if k.startswith(("test_", "Test")) and not isinstance(v, ModuleType)
    ]
    assert len(tests) == 1, tests
    return settings_decorator(tests[0])


@pytest.mark.parametrize(
    "badness", ["not an exception", BaseException, [ValueError], (Exception, "bad")]
)
def test_invalid_exceptions(badness):
    with pytest.raises(InvalidArgument):
        ghostwriter._check_except(badness)


def test_style_validation():
    ghostwriter._check_style("pytest")
    ghostwriter._check_style("unittest")
    with pytest.raises(InvalidArgument):
        ghostwriter._check_style("not a valid style")


def test_strategies_with_invalid_syntax_repr_as_nothing():
    msg = "$$ this repr is not Python syntax $$"

    class NoRepr:
        def __repr__(self):
            return msg

    s = just(NoRepr())
    assert repr(s) == f"just({msg})"
    assert ghostwriter._valid_syntax_repr(s)[1] == "nothing()"


class AnEnum(enum.Enum):
    a = "value of AnEnum.a"
    b = "value of AnEnum.b"


def takes_enum(foo=AnEnum.a):
    # This can only fail if we use the default argument to guess
    # that any instance of that enum type should be allowed.
    assert foo != AnEnum.b


def test_ghostwriter_exploits_arguments_with_enum_defaults():
    source_code = ghostwriter.fuzz(takes_enum)
    test = get_test_function(source_code)
    with pytest.raises(AssertionError):
        test()


def timsort(seq: Sequence[int]) -> list[int]:
    return sorted(seq)


def non_type_annotation(x: 3):  # type: ignore
    pass


def annotated_any(x: Any):
    pass


space_in_name = type("a name", (type,), {"__init__": lambda self: None})


class NotResolvable:
    def __init__(self, unannotated_required):
        pass


def non_resolvable_arg(x: NotResolvable):
    pass


def test_flattens_one_of_repr():
    strat = from_type(Union[int, Sequence[int]])
    assert repr(strat).count("one_of(") > 1
    assert ghostwriter._valid_syntax_repr(strat)[1].count("one_of(") == 1


def takes_keys(x: KeysView[int]) -> None:
    pass


def takes_values(x: ValuesView[int]) -> None:
    pass


def takes_match(x: re.Match[bytes]) -> None:
    pass


def takes_pattern(x: re.Pattern[str]) -> None:
    pass


def takes_sized(x: Sized) -> None:
    pass


def takes_frozensets(a: frozenset[int], b: frozenset[int]) -> None:
    pass


@attr.s()
class Foo:
    foo: str = attr.ib()


def takes_attrs_class(x: Foo) -> None:
    pass


@varied_excepts
@pytest.mark.parametrize(
    "func",
    [
        re.compile,
        json.loads,
        json.dump,
        timsort,
        ast.literal_eval,
        non_type_annotation,
        annotated_any,
        space_in_name,
        non_resolvable_arg,
        takes_keys,
        takes_values,
        takes_match,
        takes_pattern,
        takes_sized,
        takes_frozensets,
        takes_attrs_class,
    ],
)
def test_ghostwriter_fuzz(func, ex):
    source_code = ghostwriter.fuzz(func, except_=ex)
    get_test_function(source_code)


def test_socket_module():
    source_code = ghostwriter.magic(socket)
    exec(source_code, {})


def test_binary_op_also_handles_frozensets():
    # Using str.replace in a loop would convert `frozensets()` into
    # `st.frozenst.sets()` instead of `st.frozensets()`; fixed with re.sub.
    source_code = ghostwriter.binary_operation(takes_frozensets)
    exec(source_code, {})


@varied_excepts
@pytest.mark.parametrize(
    "func", [re.compile, json.loads, json.dump, timsort, ast.literal_eval]
)
def test_ghostwriter_unittest_style(func, ex):
    source_code = ghostwriter.fuzz(func, except_=ex, style="unittest")
    assert issubclass(get_test_function(source_code), unittest.TestCase)


def no_annotations(foo=None, *, bar=False):
    pass


def test_inference_from_defaults_and_none_booleans_reprs_not_just_and_sampled_from():
    source_code = ghostwriter.fuzz(no_annotations)
    assert "@given(foo=st.none(), bar=st.booleans())" in source_code


def hopefully_hashable(foo: set[Decimal]):
    pass


def test_no_hashability_filter():
    # In from_type, we ordinarily protect users from really weird cases like
    # `Decimal('snan')` - a unhashable value of a hashable type - but in the
    # ghostwriter we instead want to present this to the user for an explicit
    # decision.  They can pass `allow_nan=False`, fix their custom type's
    # hashing logic, or whatever else; simply doing nothing will usually work.
    source_code = ghostwriter.fuzz(hopefully_hashable)
    assert "@given(foo=st.sets(st.decimals()))" in source_code
    assert "_can_hash" not in source_code


@pytest.mark.parametrize(
    "gw,args",
    [
        (ghostwriter.fuzz, ["not callable"]),
        (ghostwriter.idempotent, ["not callable"]),
        (ghostwriter.roundtrip, []),
        (ghostwriter.roundtrip, ["not callable"]),
        (ghostwriter.equivalent, [sorted]),
        (ghostwriter.equivalent, [sorted, "not callable"]),
    ],
)
def test_invalid_func_inputs(gw, args):
    with pytest.raises(InvalidArgument):
        gw(*args)


class A:
    @classmethod
    def to_json(cls, obj: Union[dict, list]) -> str:
        return json.dumps(obj)

    @classmethod
    def from_json(cls, obj: str) -> Union[dict, list]:
        return json.loads(obj)

    @staticmethod
    def static_sorter(seq: Sequence[int]) -> list[int]:
        return sorted(seq)


@pytest.mark.parametrize(
    "gw,args",
    [
        (ghostwriter.fuzz, [A.static_sorter]),
        (ghostwriter.idempotent, [A.static_sorter]),
        (ghostwriter.roundtrip, [A.to_json, A.from_json]),
        (ghostwriter.equivalent, [A.to_json, json.dumps]),
    ],
)
def test_class_methods_inputs(gw, args):
    source_code = gw(*args)
    get_test_function(source_code)()


def test_run_ghostwriter_fuzz():
    # Our strategy-guessing code works for all the arguments to sorted,
    # and we handle positional-only arguments in calls correctly too.
    source_code = ghostwriter.fuzz(sorted)
    assert "st.nothing()" not in source_code
    get_test_function(source_code)()


class MyError(UnicodeDecodeError):
    pass


@pytest.mark.parametrize(
    "exceptions,output",
    [
        # Discard subclasses of other exceptions to catch, including non-builtins,
        # and replace OSError aliases with OSError.
        ((Exception, UnicodeError), "Exception"),
        ((UnicodeError, MyError), "UnicodeError"),
        ((IOError,), "OSError"),
        ((IOError, UnicodeError), "(OSError, UnicodeError)"),
    ],
)
def test_exception_deduplication(exceptions, output):
    _, body = ghostwriter._make_test_body(
        lambda: None,
        ghost="",
        test_body="pass",
        except_=exceptions,
        style="pytest",
        annotate=False,
    )
    assert f"except {output}:" in body


def test_run_ghostwriter_roundtrip():
    # This test covers the whole lifecycle: first, we get the default code.
    # The first argument is unknown, so we fail to draw from st.nothing()
    source_code = ghostwriter.roundtrip(json.dumps, json.loads)
    with pytest.raises(Unsatisfiable):
        get_test_function(source_code)()

    # Replacing that nothing() with a strategy for JSON allows us to discover
    # two possible failures: `nan` is not equal to itself, and if dumps is
    # passed allow_nan=False it is a ValueError to pass a non-finite float.
    source_code = source_code.replace(
        "st.nothing()",
        "st.recursive(st.one_of(st.none(), st.booleans(), st.floats(), st.text()), "
        "lambda v: st.lists(v, max_size=2) | st.dictionaries(st.text(), v, max_size=2)"
        ", max_leaves=2)",
    )
    s = settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    try:
        get_test_function(source_code, settings_decorator=s)()
    except (AssertionError, ValueError, BaseExceptionGroup):
        pass

    # Finally, restricting ourselves to finite floats makes the test pass!
    source_code = source_code.replace(
        "st.floats()", "st.floats(allow_nan=False, allow_infinity=False)"
    )
    get_test_function(source_code, settings_decorator=s)()


@varied_excepts
@pytest.mark.parametrize("func", [sorted, timsort])
def test_ghostwriter_idempotent(func, ex):
    source_code = ghostwriter.idempotent(func, except_=ex)
    test = get_test_function(source_code)
    if "=st.nothing()" in source_code:
        with pytest.raises(Unsatisfiable):
            test()
    else:
        test()


def test_overlapping_args_use_union_of_strategies():
    def f(arg: int) -> None:
        pass

    def g(arg: float) -> None:
        pass

    source_code = ghostwriter.equivalent(f, g)
    assert "arg=st.one_of(st.integers(), st.floats())" in source_code


def test_module_with_mock_does_not_break():
    # Before we added an explicit check for unspec'd mocks, they would pass
    # through the initial validation and then fail when used in more detailed
    # logic in the ghostwriter machinery.
    ghostwriter.magic(unittest.mock)


def compose_types(x: type, y: type):
    pass


def test_unrepr_identity_elem():
    # Works with inferred identity element
    source_code = ghostwriter.binary_operation(compose_types)
    exec(source_code, {})
    # and also works with explicit identity element
    source_code = ghostwriter.binary_operation(compose_types, identity=type)
    exec(source_code, {})


@pytest.mark.parametrize(
    "strategy, imports",
    # The specifics don't matter much here; we're just demonstrating that
    # we can walk the strategy and collect all the objects to import.
    [
        # Lazy from_type() is handled without being unwrapped
        (LazyStrategy(from_type, (enum.Enum,), {}), {("enum", "Enum")}),
        # Mapped, filtered, and flatmapped check both sides of the method
        (
            builds(enum.Enum).map(Decimal),
            {("enum", "Enum"), ("decimal", "Decimal")},
        ),
        (
            builds(enum.Enum).flatmap(Decimal),
            {("enum", "Enum"), ("decimal", "Decimal")},
        ),
        (
            builds(enum.Enum).filter(Decimal).filter(re.compile),
            {("enum", "Enum"), ("decimal", "Decimal"), ("re", "compile")},
        ),
        # one_of() strategies recurse into all the branches
        (
            builds(enum.Enum) | builds(Decimal) | builds(re.compile),
            {("enum", "Enum"), ("decimal", "Decimal"), ("re", "compile")},
        ),
        # and builds() checks the arguments as well as the target
        (
            builds(enum.Enum, builds(Decimal), kw=builds(re.compile)),
            {("enum", "Enum"), ("decimal", "Decimal"), ("re", "compile")},
        ),
        # lists recurse on imports
        (
            lists(builds(Decimal)),
            {("decimal", "Decimal")},
        ),
        # find the needed import for from_regex if needed
        (
            from_regex(re.compile(".+")),
            {"re"},
        ),
        # but don't add superfluous imports
        (
            from_regex(".+"),
            set(),
        ),
    ],
)
def test_get_imports_for_strategy(strategy, imports):
    assert ghostwriter._imports_for_strategy(strategy) == imports


@pytest.fixture
def temp_script_file():
    """Fixture to yield a Path to a temporary file in the local directory. File name will end
    in .py and will include an importable function.
    """
    p = Path("my_temp_script.py")
    if p.exists():
        raise FileExistsError(f"Did not expect {p} to exist during testing")
    p.write_text(
        dedent(
            """
            def say_hello():
                print("Hello world!")
            """
        ),
        encoding="utf-8",
    )
    yield p
    p.unlink()


@pytest.fixture
def temp_script_file_with_py_function():
    """Fixture to yield a Path to a temporary file in the local directory. File name will end
    in .py and will include an importable function named "py"
    """
    p = Path("my_temp_script_with_py_function.py")
    if p.exists():
        raise FileExistsError(f"Did not expect {p} to exist during testing")
    p.write_text(
        dedent(
            """
            def py():
                print('A function named "py" has been called')
            """
        ),
        encoding="utf-8",
    )
    yield p
    p.unlink()


def test_obj_name(temp_script_file, temp_script_file_with_py_function):
    # Module paths (strings including a "/") should raise a meaningful UsageError
    with pytest.raises(click.exceptions.UsageError) as e:
        cli.obj_name("mydirectory/myscript.py")
    assert e.match(
        "Remember that the ghostwriter should be passed the name of a module, not a path."
    )
    # Windows paths (strings including a "\") should also raise a meaningful UsageError
    with pytest.raises(click.exceptions.UsageError) as e:
        cli.obj_name(R"mydirectory\myscript.py")
    assert e.match(
        "Remember that the ghostwriter should be passed the name of a module, not a path."
    )
    # File names of modules (strings ending in ".py") should raise a meaningful UsageError
    with pytest.raises(click.exceptions.UsageError) as e:
        cli.obj_name("myscript.py")
    assert e.match(
        "Remember that the ghostwriter should be passed the name of a module, not a file."
    )
    # File names of modules (strings ending in ".py") that exist should get a suggestion
    with pytest.raises(click.exceptions.UsageError) as e:
        cli.obj_name(str(temp_script_file))
    assert e.match(
        "Remember that the ghostwriter should be passed the name of a module, not a file."
        f"\n\tTry: hypothesis write {temp_script_file.stem}"
    )
    # File names of modules (strings ending in ".py") that define a py function should succeed
    assert isinstance(
        cli.obj_name(str(temp_script_file_with_py_function)), FunctionType
    )


def test_gets_public_location_not_impl_location():
    assert ghostwriter._get_module(assume) == "hypothesis"  # not "hypothesis.control"
