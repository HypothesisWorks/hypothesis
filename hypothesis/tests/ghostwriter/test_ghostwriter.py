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
import builtins
import enum
import inspect
import json
import re
import socket
import subprocess
import sys
import time
import unittest
import unittest.mock
from collections.abc import KeysView, Sequence, Sized, ValuesView
from decimal import Decimal
from pathlib import Path
from textwrap import dedent
from types import FunctionType, ModuleType
from typing import Any, ForwardRef, TypeVar

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


pytestmark = pytest.mark.skipif(
    settings.get_current_profile_name() == "threading",
    reason="ghostwriter is not thread safe",
)


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
    strat = from_type(int | Sequence[int])
    assert repr(strat).count("one_of(") == 2
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


def test_binary_op_with_numpy_arrays_includes_imports():
    # Regression test for issue #4576: binary_operation should include imports
    # for numpy strategies like arrays(), scalar_dtypes(), and array_shapes()
    pytest.importorskip("numpy")
    import numpy as np

    def numpy_add(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return a + b

    source_code = ghostwriter.binary_operation(
        numpy_add, associative=True, commutative=True, identity=None
    )
    # Check that the necessary imports are present
    assert "from hypothesis.extra.numpy import" in source_code
    assert "arrays" in source_code
    assert "scalar_dtypes" in source_code
    assert "array_shapes" in source_code
    # Most importantly: the code should execute without NameError
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
        (ghostwriter.magic, []),
        (ghostwriter.magic, [42]),
        (ghostwriter.binary_operation, [42]),
    ],
)
def test_invalid_func_inputs(gw, args):
    with pytest.raises(InvalidArgument):
        gw(*args)


class A:
    @classmethod
    def to_json(cls, obj: dict | list) -> str:
        return json.dumps(obj)

    @classmethod
    def from_json(cls, obj: str) -> dict | list:
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
        dedent("""
            def say_hello():
                print("Hello world!")
            """),
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
        dedent("""
            def py():
                print('A function named "py" has been called')
            """),
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
    # A dotted name whose leading module can't be imported, and which has no
    # further dots to split off a class name, gets a meaningful UsageError.
    with pytest.raises(click.exceptions.UsageError) as e:
        cli.obj_name("nonexistentmodulexyz123.foo")
    assert e.match(
        "Failed to import the nonexistentmodulexyz123 module for introspection."
    )


def test_gets_public_location_not_impl_location():
    assert ghostwriter._get_module(assume) == "hypothesis"  # not "hypothesis.control"


class ForwardRefA:
    pass


T = TypeVar("T")


@pytest.mark.parametrize(
    "parameter, type_name",
    [
        (ForwardRef("this_ref_does_not_exist"), None),
        # `Callable[[X], ...]` args are passed through as a list; if any member
        # is unresolvable the whole list annotation is dropped rather than
        # partially rendered.
        ([ForwardRef("NopeNopeNope")], None),
        # `get_origin(int | str)` is `types.UnionType` (== `typing.Union` as of
        # Python 3.14), which we render as `typing.Union[...]`.
        (type(int | str), ghostwriter._AnnotationData("typing.Union", {"typing"})),
        (
            int | str,
            ghostwriter._AnnotationData("typing.Union[int, str]", {"typing"}),
        ),
        # An unparametrized generic like `list[T]`, where `T` is an unbound
        # TypeVar, is treated the same as the bare `list` type.
        (list[T], ghostwriter._AnnotationData("list", set())),
        # ForwardRef.evaluate() logic is new in 3.14
        *(
            []
            if sys.version_info[:2] < (3, 14)
            else [
                (
                    ForwardRef("ForwardRefA", owner=A),
                    ghostwriter._AnnotationData(
                        "test_ghostwriter.ForwardRefA", {"test_ghostwriter"}
                    ),
                )
            ]
        ),
    ],
)
def test_parameter_to_annotation(parameter, type_name):
    assert ghostwriter._parameter_to_annotation(parameter) == type_name


@pytest.mark.parametrize(
    "origin_type_data, annotations, expected",
    [
        (None, [], None),
        (
            ("typing.Optional", {"typing"}),
            [
                ghostwriter._AnnotationData("int", set()),
                ghostwriter._AnnotationData("None", set()),
            ],
            ghostwriter._AnnotationData("typing.Optional[int]", {"typing"}),
        ),
    ],
)
def test_join_generics(origin_type_data, annotations, expected):
    assert ghostwriter._join_generics(origin_type_data, annotations) == expected


@pytest.mark.parametrize(
    "docstring, expected",
    [
        # An unrecognised exception name is skipped rather than included.
        (":raises FooBarBazNotAnException: never happens", ()),
        # A builtin name which isn't an Exception subclass is also skipped.
        (":raises object: not really an exception", ()),
        (
            ":raises FooBarBazNotAnException: never happens\n:raises ValueError: bad",
            (ValueError,),
        ),
    ],
)
def test_exceptions_from_docstring_skips_unrecognised_names(docstring, expected):
    assert ghostwriter._exceptions_from_docstring(docstring) == expected


@pytest.mark.parametrize(
    "token, expected",
    [
        # "list of str": since `str` resolves directly, we never try the
        # singular-of-plural fallback.
        ("list of str", list[str]),
        # "tuple of int": elements resolve fine, but "tuple" isn't one of the
        # special-cased collection names, so we fall back to the bare "tuple".
        ("tuple of int", tuple),
        # Dotted names fall back to a module lookup.
        ("re.Pattern", re.Pattern),
    ],
)
def test_type_from_doc_fragment(token, expected):
    assert ghostwriter._type_from_doc_fragment(token) == expected


@pytest.mark.parametrize(
    "param, docstring, expected_repr",
    [
        # A trailing comma produces an empty token (skipped), and "quux" is not
        # a recognised type name (also skipped) - leaving just the `int` token.
        (
            inspect.Parameter("b", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            "b (int, quux, ): a param",
            "one_of(nothing(), integers())",
        ),
        # The default isn't one of the doc-derived elements/types, so it's
        # added as an extra sampled element.
        (
            inspect.Parameter("b", inspect.Parameter.POSITIONAL_OR_KEYWORD, default=5),
            "b (str): a string param",
            "one_of(just(5), text())",
        ),
        # The RST-style pattern matches, but "quux" resolves to nothing useful,
        # so we fall through the (empty) Google- and Numpy-style attempts and
        # end up guessing from the argument name instead.
        (
            inspect.Parameter("x", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            ":type x: quux",
            "nothing()",
        ),
    ],
)
def test_strategy_for(param, docstring, expected_repr):
    assert repr(ghostwriter._strategy_for(param, docstring)) == expected_repr


@pytest.mark.parametrize(
    "name, expected_repr",
    [
        ("func", "functions()"),
        ("predicate", "functions(returns=booleans(), pure=True)"),
        ("lst", "lists(nothing())"),
        ("my_uuid", "uuids().map(str)"),
        ("is_active", "booleans()"),
        ("amount", "one_of(integers(), floats())"),
        ("offset", "integers()"),
        ("dropout", "floats(min_value=0, max_value=1)"),
        ("lat", "floats(min_value=-90, max_value=90)"),
        ("lon", "floats(min_value=-180, max_value=180)"),
        ("tolerance", "floats(min_value=0)"),
        ("alpha", "floats()"),
        ("email", "emails()"),
        ("slug", "from_regex('\\\\w+', fullmatch=True)"),
        ("char", "characters()"),
        ("path", "nothing()"),
        # plural fallback: no direct rule for "amounts", but "amount" resolves
        # to something non-empty, so we wrap it in a list.
        ("amounts", "lists(one_of(integers(), floats()))"),
    ],
)
def test_guess_strategy_by_argname(name, expected_repr):
    assert repr(ghostwriter._guess_strategy_by_argname(name)) == expected_repr


@pytest.mark.parametrize(
    "func, expected_names",
    [
        # `divmod`'s docstring doesn't start with "divmod(...)", so we can't
        # recover a signature from it at all.
        (divmod, []),
        # __build_class__'s docstring is "__build_class__(func, name, /,
        # *bases, [metaclass], **kwds)", exercising the "/" and "*" (and "**")
        # markers.
        (builtins.__build_class__, ["func", "name", "metaclass"]),
        # time.get_clock_info's docstring argument is "name: str", which is not
        # a valid Python identifier - so we stop parsing immediately.
        (time.get_clock_info, []),
    ],
)
def test_get_params_builtin_fn(func, expected_names):
    params = ghostwriter._get_params_builtin_fn(func)
    assert [p.name for p in params] == expected_names


def test_get_testable_functions_skips_callable_without_a_name():
    # A callable instance with no `__name__`/`__qualname__` can't be looked up
    # by qualified name, so it's silently dropped rather than raising.
    class Nameless:
        def __call__(self, x: int):
            pass

    assert ghostwriter._get_testable_functions(Nameless()) == {}


def test_magic_prefers_functions_defined_directly_in_a_package(tmp_path):
    pkg = tmp_path / "mypkg_for_magic_test"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(
        "from mypkg_for_magic_test.sub import sub_func\n\n"
        "def pkg_func(x: int) -> int:\n    return x\n",
        encoding="utf-8",
    )
    (pkg / "sub.py").write_text(
        "def sub_func(x: int) -> int:\n    return x\n", encoding="utf-8"
    )
    source_code = subprocess.check_output(
        [
            sys.executable,
            "-c",
            (
                "import mypkg_for_magic_test\n"
                "from hypothesis.extra import ghostwriter\n"
                "print(ghostwriter.magic(mypkg_for_magic_test))"
            ),
        ],
        cwd=tmp_path,
        encoding="utf-8",
    )
    assert "pkg_func" in source_code
    assert "sub_func" not in source_code


def test_magic_module_without_spec():
    # __spec__ is None for __main__ in scripts and the REPL, and for
    # dynamically created modules
    mod = ModuleType("my_script")
    mod.timsort = timsort
    assert "timsort" in ghostwriter.magic(mod)


def test_magic_does_not_merge_equivalent_functions_with_different_returns():
    # Two functions with the same (unqualified) name and parameters, but
    # different return-type annotations, aren't treated as equivalent - so we
    # get two separate fuzz tests rather than one equivalence test.
    ns_a: dict = {}
    exec("def foo(x: int) -> int:\n    return x\n", ns_a)
    foo_a = ns_a["foo"]
    foo_a.__module__ = "ghostwriter_test_mod_a"

    ns_b: dict = {}
    exec("def foo(x: int) -> str:\n    return str(x)\n", ns_b)
    foo_b = ns_b["foo"]
    foo_b.__module__ = "ghostwriter_test_mod_b"

    source_code = ghostwriter.magic(foo_a, foo_b)
    assert source_code.count("def test_fuzz_foo(") == 2
    assert "def test_equivalent_" not in source_code


@pytest.mark.parametrize("annotate", [True, False])
def test_idempotent_explicit_annotate(annotate):
    source_code = ghostwriter.idempotent(sorted, annotate=annotate)
    assert (" -> None" in source_code) == annotate


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"distributes_over": 42}, "must be an operation which"),
        (
            {
                "associative": False,
                "commutative": False,
                "identity": None,
                "distributes_over": None,
            },
            "at least one property",
        ),
    ],
)
def test_binary_operation_invalid_arguments(kwargs, match):
    with pytest.raises(InvalidArgument, match=match):
        ghostwriter.binary_operation(compose_types, **kwargs)


def test_binary_operation_merges_different_operand_strategies():
    def different_types_op(amount, text):
        return (amount, text)

    source_code = ghostwriter.binary_operation(different_types_op, identity=None)
    assert "one_of(" in source_code
    exec(source_code, {})


def test_ufunc_ghostwriter_function():
    numpy = pytest.importorskip("numpy")
    # numpy.isnan is a plain (non-generalized) ufunc none of whose type
    # signatures involve the object dtype.
    source_code = ghostwriter.ufunc(numpy.isnan)
    exec(source_code, {})
    # Also cover passing an explicit `annotate`, rather than the default None.
    source_code = ghostwriter.ufunc(numpy.isnan, annotate=True)
    exec(source_code, {})


def test_ufunc_ghostwriter_rejects_non_ufunc():
    with pytest.raises(InvalidArgument, match="does not seem to be a ufunc"):
        ghostwriter.ufunc(len)
