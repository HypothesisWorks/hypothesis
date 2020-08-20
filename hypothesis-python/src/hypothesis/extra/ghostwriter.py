# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

"""
Writing tests with Hypothesis frees you from the tedium of deciding on and
writing out specific inputs to test.  Now, the ``hypothesis.extra.ghostwriter``
module can write your test functions for you too!

The idea is to provide **an easy way to start** property-based testing,
**and a seamless transition** to more complex test code - because ghostwritten
tests are source code that you could have written for yourself.

So just pick a function you'd like tested, and feed it to one of the functions
below or :ref:`our command-line interface <hypothesis-cli>` :command:`hypothesis write -h`!
They follow imports, use but do not require type annotations, and generally
do their best to write you a useful test.

.. note::

    The ghostwriter requires Python 3.6+ and :pypi:`black`, but the generated
    code supports Python 3.5+ and has no dependencies beyond Hypothesis itself.

.. note::

    Legal questions?  While the ghostwriter fragments and logic is under the
    MPL-2.0 license like the rest of Hypothesis, the *output* from the ghostwriter
    is made available under the `Creative Commons Zero (CC0)
    <https://creativecommons.org/share-your-work/public-domain/cc0/>`__
    public domain dedication, so you can use it without any restrictions.
"""

import builtins
import enum
import inspect
import re
import sys
import types
from collections import OrderedDict
from itertools import permutations, zip_longest
from string import ascii_lowercase
from textwrap import dedent, indent
from typing import Callable, Dict, Mapping, Set, Tuple, Type, TypeVar, Union

import black

from hypothesis import find, strategies as st
from hypothesis.errors import InvalidArgument, Unsatisfiable
from hypothesis.internal.compat import get_type_hints
from hypothesis.internal.validation import check_type
from hypothesis.strategies._internal.strategies import OneOfStrategy
from hypothesis.utils.conventions import InferType, infer

IMPORT_SECTION = """
# This test code was written by the `hypothesis.extra.ghostwriter` module
# and is provided under the Creative Commons Zero public domain dedication.

{imports}from hypothesis import given, {reject}strategies as st
"""

TEMPLATE = """
@given({given_args})
def test_{test_kind}_{func_name}({arg_names}):
{test_body}
"""

SUPPRESS_BLOCK = """\
try:
{test_body}
except {exceptions}:
    reject()
"""

Except = Union[Type[Exception], Tuple[Type[Exception], ...]]


def _check_except(except_: Except) -> Tuple[Type[Exception], ...]:
    if isinstance(except_, tuple):
        for i, e in enumerate(except_):
            if not isinstance(e, type) or not issubclass(e, Exception):
                raise InvalidArgument(
                    f"Expected an Exception but got except_[{i}]={e!r}"
                    f" (type={_get_qualname(type(e))})"
                )
        return except_
    if not isinstance(except_, type) or not issubclass(except_, Exception):
        raise InvalidArgument(
            "Expected an Exception or tuple of exceptions, but got except_="
            f"{except_!r} (type={_get_qualname(type(except_))})"
        )
    return (except_,)


def _check_style(style: str) -> None:
    if style not in ("pytest", "unittest"):
        raise InvalidArgument(f"Valid styles are 'pytest' or 'unittest', got {style!r}")


# Simple strategies to guess for common argument names - we wouldn't do this in
# builds() where strict correctness is required, but we only use these guesses
# when the alternative is nothing() to force user edits anyway.
#
# This table was constructed manually after skimming through the documentation
# for the builtins and a few stdlib modules.  Future enhancements could be based
# on analysis of type-annotated code to detect arguments which almost always
# take values of a particular type.
_GUESS_STRATEGIES_BY_NAME = (
    (st.text(), ["name", "filename", "fname"]),
    (st.integers(min_value=0), ["index"]),
    (st.floats(), ["real", "imag"]),
    (st.functions(), ["function", "func", "f"]),
    (st.iterables(st.integers()) | st.iterables(st.text()), ["iterable"]),
)


def _strategy_for(param: inspect.Parameter) -> Union[st.SearchStrategy, InferType]:
    # We use `infer` and go via `builds()` instead of directly through
    # `from_type()` so that `get_type_hints()` can resolve any forward
    # references for us.
    if param.annotation is not inspect.Parameter.empty:
        return infer
    # If our default value is an Enum or a boolean, we assume that any value
    # of that type is acceptable.  Otherwise, we only generate the default.
    if isinstance(param.default, bool):
        return st.booleans()
    if isinstance(param.default, enum.Enum):
        return st.sampled_from(type(param.default))
    if param.default is not inspect.Parameter.empty:
        # Using `st.from_type(type(param.default))` would  introduce spurious
        # failures in cases like the `flags` argument to regex functions.
        # Better in to keep it simple, and let the user elaborate if desired.
        return st.just(param.default)
    # If there's no annotation and no default value, we check against a table
    # of guesses of simple strategies for common argument names.
    if "string" in param.name and "as" not in param.name:
        return st.text()
    for strategy, names in _GUESS_STRATEGIES_BY_NAME:
        if param.name in names:
            return strategy
    # And if all that failed, we'll return nothing() - the user will have to
    # fill this in by hand, and we'll leave a comment to that effect later.
    return st.nothing()


def _get_params(func: Callable) -> Dict[str, inspect.Parameter]:
    """Get non-vararg parameters of `func` as an ordered dict."""
    var_param_kinds = (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    try:
        params = list(inspect.signature(func).parameters.values())
    except Exception:
        if (
            isinstance(func, (types.BuiltinFunctionType, types.BuiltinMethodType))
            and hasattr(func, "__doc__")
            and isinstance(func.__doc__, str)
        ):
            # inspect.signature doesn't work on all builtin functions or methods.
            # In such cases, including the operator module on Python 3.6, we can try
            # to reconstruct simple signatures from the docstring.
            pattern = rf"^{func.__name__}\(([a-z]+(, [a-z]+)*)(, \\)?\)"
            args = re.match(pattern, func.__doc__)
            if args is None:
                raise
            params = [
                # Note that we assume that the args are positional-only regardless of
                # whether the signature shows a `/`, because this is often the case.
                inspect.Parameter(name=name, kind=inspect.Parameter.POSITIONAL_ONLY)
                for name in args.group(1).split(", ")
            ]
        elif _is_probably_ufunc(func):
            # `inspect.signature` doesn't work on ufunc objects, but we can work out
            # what the required parameters would look like if it did.
            # Note that we use args named a, b, c... to match the `operator` module,
            # rather than x1, x2, x3... like the Numpy docs.  Because they're pos-only
            # this doesn't make a runtime difference, and it's much nicer for use-cases
            # like `equivalent(numpy.add, operator.add)`.
            params = [
                inspect.Parameter(name=name, kind=inspect.Parameter.POSITIONAL_ONLY)
                for name in ascii_lowercase[: func.nin]  # type: ignore
            ]
        else:
            # If we haven't managed to recover a signature through the tricks above,
            # we're out of ideas and should just re-raise the exception.
            raise
    return OrderedDict((p.name, p) for p in params if p.kind not in var_param_kinds)


def _get_strategies(
    *funcs: Callable, pass_result_to_next_func: bool = False
) -> Dict[str, st.SearchStrategy]:
    """Return a dict of strategies for the union of arguments to `funcs`.

    If `pass_result_to_next_func` is True, assume that the result of each function
    is passed to the next, and therefore skip the first argument of all but the
    first function.

    This dict is used to construct our call to the `@given(...)` decorator.
    """
    given_strategies = {}  # type: Dict[str, st.SearchStrategy]
    for i, f in enumerate(funcs):
        params = _get_params(f)
        if pass_result_to_next_func and i >= 1:
            del params[next(iter(params))]
        builder_args = {k: _strategy_for(v) for k, v in params.items()}
        strat = st.builds(f, **builder_args).wrapped_strategy  # type: ignore

        args, kwargs = strat.mapped_strategy.wrapped_strategy.element_strategies
        if args.element_strategies:
            raise NotImplementedError("Expected to pass everything as kwargs")

        for k, v in zip(kwargs.keys, kwargs.mapped_strategy.element_strategies):
            if isinstance(v, OneOfStrategy):
                # repr nested one_of as flattened (their real behaviour)
                v = st.one_of(v.element_strategies)
            if repr(given_strategies.get(k, v)) != repr(v):
                # In this branch, we have two functions that take an argument of the
                # same name but different strategies - probably via the equivalent()
                # ghostwriter.  In general, we would expect the test to pass given
                # the *intersection* of the domains of these functions.  However:
                #   - we can't take the intersection of two strategies
                #   - this may indicate a problem which should be exposed to the user
                # and so we take the *union* instead - either it'll work, or the
                # user will be presented with a reasonable suite of options.
                given_strategies[k] = given_strategies[k] | v
            else:
                given_strategies[k] = v

    # If there is only one function, we pass arguments to @given in the order of
    # that function's signature.  Otherwise, we use alphabetical order.
    if len(funcs) == 1:
        return {name: given_strategies[name] for name in _get_params(f)}
    return dict(sorted(given_strategies.items()))


def _assert_eq(style, a, b):
    if style == "unittest":
        return f"self.assertEqual({a}, {b})"
    assert style == "pytest"
    if a.isidentifier() and b.isidentifier():
        return f"assert {a} == {b}, ({a}, {b})"
    return f"assert {a} == {b}"


def _valid_syntax_repr(strategy):
    if isinstance(strategy, str):
        return strategy
    if strategy == st.text().wrapped_strategy:
        return "text()"
    # Return a syntactically-valid strategy repr, including fixing some
    # strategy reprs and replacing invalid syntax reprs with `"nothing()"`.
    # String-replace to hide the special case in from_type() for Decimal('snan')
    r = repr(strategy).replace(".filter(_can_hash)", "")
    try:
        compile(r, "<string>", "eval")
        return r
    except SyntaxError:
        return "nothing()"


# (g)ufuncs do not have a __module__ attribute, so we simply look for them in
# any of the following modules which are found in sys.modules.  The order of
# these entries doesn't matter, because we check identity of the found object.
LOOK_FOR_UFUNCS_IN_MODULES = ("numpy", "astropy", "erfa", "dask", "numba")


def _get_module(obj):
    try:
        return obj.__module__
    except AttributeError:
        if not _is_probably_ufunc(obj):
            raise
    for module_name in LOOK_FOR_UFUNCS_IN_MODULES:
        if obj is getattr(sys.modules.get(module_name), obj.__name__, None):
            return module_name
    raise RuntimeError(f"Could not find module for ufunc {obj.__name__} ({obj!r}")


def _get_qualname(obj, include_module=False):
    # Replacing angle-brackets for objects defined in `.<locals>.`
    qname = getattr(obj, "__qualname__", obj.__name__)
    qname = qname.replace("<", "_").replace(">", "_")
    if include_module:
        return _get_module(obj) + "." + qname
    return qname


def _write_call(func: Callable, *pass_variables: str) -> str:
    """Write a call to `func` with explicit and implicit arguments.

    >>> _write_call(sorted, "my_seq", "func")
    "builtins.sorted(my_seq, key=func, reverse=reverse)"
    """
    args = ", ".join(
        (v or p.name)
        if p.kind is inspect.Parameter.POSITIONAL_ONLY
        else f"{p.name}={v or p.name}"
        for v, p in zip_longest(pass_variables, _get_params(func).values())
    )
    return f"{_get_qualname(func, include_module=True)}({args})"


def _make_test_body(
    *funcs: Callable,
    ghost: str,
    test_body: str,
    except_: Tuple[Type[Exception], ...],
    style: str,
    given_strategies: Mapping[str, Union[str, st.SearchStrategy]] = None,
) -> Tuple[Set[str], str]:
    # Get strategies for all the arguments to each function we're testing.
    given_strategies = given_strategies or _get_strategies(
        *funcs, pass_result_to_next_func=ghost in ("idempotent", "roundtrip")
    )
    given_args = ", ".join(
        "{}={}".format(k, _valid_syntax_repr(v)) for k, v in given_strategies.items()
    )
    for name in st.__all__:
        given_args = given_args.replace(f"{name}(", f"st.{name}(")

    # A set of modules to import - we might add to this later.  The import code
    # is written later, so we can have one import section for multiple magic()
    # test functions.
    imports = {_get_module(f) for f in funcs}

    if except_:
        # This is reminiscent of de-duplication logic I wrote for flake8-bugbear,
        # but with access to the actual objects we can just check for subclasses.
        # This lets us print e.g. `Exception` instead of `(Exception, OSError)`.
        uniques = list(except_)
        for a, b in permutations(except_, 2):
            if a in uniques and issubclass(a, b):
                uniques.remove(a)
        # Then convert to strings, either builtin names or qualified names.
        exceptions = []
        for ex in uniques:
            if ex.__qualname__ in dir(builtins):
                exceptions.append(ex.__qualname__)
            else:
                imports.add(ex.__module__)
                exceptions.append(_get_qualname(ex, include_module=True))
        # And finally indent the existing test body into a try-except block
        # which catches these exceptions and calls `hypothesis.reject()`.
        test_body = SUPPRESS_BLOCK.format(
            test_body=indent(test_body, prefix="    "),
            exceptions="(" + ", ".join(exceptions) + ")"
            if len(exceptions) > 1
            else exceptions[0],
        )

    # Indent our test code to form the body of a function or method.
    argnames = (["self"] if style == "unittest" else []) + list(given_strategies)
    body = TEMPLATE.format(
        given_args=given_args,
        test_kind=ghost,
        func_name="_".join(_get_qualname(f).replace(".", "_") for f in funcs),
        arg_names=", ".join(argnames),
        test_body=indent(test_body, prefix="    "),
    )

    # For unittest-style, indent method further into a class body
    if style == "unittest":
        imports.add("unittest")
        body = "class Test{}{}(unittest.TestCase):\n".format(
            ghost.title(),
            "".join(_get_qualname(f).replace(".", "").title() for f in funcs),
        ) + indent(body, "    ")

    return imports, body


def _make_test(imports: Set[str], body: str) -> str:
    # Discarding "builtins." and "__main__" probably isn't particularly useful
    # for user code, but important for making a good impression in demos.
    body = body.replace("builtins.", "").replace("__main__.", "")
    imports.discard("builtins")
    imports.discard("__main__")
    header = IMPORT_SECTION.format(
        imports="".join(f"import {imp}\n" for imp in sorted(imports)),
        reject="reject, " if "        reject()\n" in body else "",
    )
    nothings = body.count("st.nothing()")
    if nothings == 1:
        header += "# TODO: replace st.nothing() with an appropriate strategy\n\n"
    elif nothings >= 1:
        header += "# TODO: replace st.nothing() with appropriate strategies\n\n"
    return black.format_str(header + body, mode=black.FileMode())


def _is_probably_ufunc(obj):
    # See https://numpy.org/doc/stable/reference/ufuncs.html - there doesn't seem
    # to be an upstream function to detect this, so we just guess.
    has_attributes = "nin nout nargs ntypes types identity signature".split()
    return callable(obj) and all(hasattr(obj, name) for name in has_attributes)


# If we have a pair of functions where one name matches the regex and the second
# is the result of formatting the template with matched groups, our magic()
# ghostwriter will write a roundtrip test for them.  Additional patterns welcome.
ROUNDTRIP_PAIRS = (
    # Defined prefix, shared postfix.  The easy cases.
    (r"write(.+)", "read{}"),
    (r"save(.+)", "load{}"),
    (r"dump(.+)", "load{}"),
    (r"to(.+)", "from{}"),
    # Known stem, maybe matching prefixes, maybe matching postfixes.
    (r"(.*)encode(.*)", "{}decode{}"),
    # Shared postfix, prefix only on "inverse" function
    (r"(.+)", "de{}"),
    (r"(.+)", "un{}"),
    # a2b_postfix and b2a_postfix.  Not a fan of this pattern, but it's pretty
    # common in code imitating an C API - see e.g. the stdlib binascii module.
    (r"(.+)2(.+?)(_.+)?", "{1}2{0}{2}"),
)


def magic(
    *modules_or_functions: Union[Callable, types.ModuleType],
    except_: Except = (),
    style: str = "pytest",
) -> str:
    """Guess which ghostwriters to use, for a module or collection of functions.

    As for all ghostwriters, the ``except_`` argument should be an
    :class:`python:Exception` or tuple of exceptions, and ``style`` may be either
    ``"pytest"`` to write test functions or ``"unittest"`` to write test methods
    and :class:`~python:unittest.TestCase`.

    After finding the public functions attached to any modules, the ``magic``
    ghostwriter looks for pairs of functions to pass to :func:`~roundtrip`,
    then checks for :func:`~binary_operation` and :func:`~ufunc` functions,
    and any others are passed to :func:`~fuzz`.

    For example, try :command:`hypothesis write gzip` on the command line!
    """
    except_ = _check_except(except_)
    _check_style(style)
    if not modules_or_functions:
        raise InvalidArgument("Must pass at least one function or module to test.")
    functions = set()
    for thing in modules_or_functions:
        if callable(thing):
            functions.add(thing)
        elif isinstance(thing, types.ModuleType):
            if hasattr(thing, "__all__"):
                funcs = [getattr(thing, name) for name in thing.__all__]  # type: ignore
            else:
                funcs = [
                    v
                    for k, v in vars(thing).items()
                    if callable(v) and not k.startswith("_")
                ]
            for f in funcs:
                try:
                    if callable(f) and inspect.signature(f).parameters:
                        functions.add(f)
                except ValueError:
                    pass
        else:
            raise InvalidArgument(f"Can't test non-module non-callable {thing!r}")

    imports = set()
    parts = []
    by_name = {_get_qualname(f): f for f in functions}
    if len(by_name) < len(functions):
        raise InvalidArgument("Functions to magic() test must have unique names")

    # Look for pairs of functions that roundtrip, based on known naming patterns.
    for writename, readname in ROUNDTRIP_PAIRS:
        for name in sorted(by_name):
            match = re.fullmatch(writename, name)
            if match:
                other = readname.format(*match.groups())
                if other in by_name:
                    imp, body = _make_roundtrip_body(
                        (by_name.pop(name), by_name.pop(other)),
                        except_=except_,
                        style=style,
                    )
                    imports |= imp
                    parts.append(body)

    # Look for binary operators - functions with two identically-typed arguments,
    # and the same return type.  The latter restriction might be lifted later.
    for name, func in sorted(by_name.items()):
        hints = get_type_hints(func)
        hints.pop("return", None)
        if len(hints) == len(_get_params(func)) == 2:
            a, b = hints.values()
            if a == b:
                imp, body = _make_binop_body(func, except_=except_, style=style)
                imports |= imp
                parts.append(body)
                del by_name[name]

    # Look for Numpy ufuncs or gufuncs, and write array-oriented tests for them.
    if "numpy" in sys.modules:
        for name, func in sorted(by_name.items()):
            if _is_probably_ufunc(func):
                imp, body = _make_ufunc_body(func, except_=except_, style=style)
                imports |= imp
                parts.append(body)
                del by_name[name]

    # For all remaining callables, just write a fuzz-test.  In principle we could
    # guess at equivalence or idempotence; but it doesn't seem accurate enough to
    # be worth the trouble when it's so easy for the user to specify themselves.
    for _, f in sorted(by_name.items()):
        imp, body = _make_test_body(
            f, test_body=_write_call(f), except_=except_, ghost="fuzz", style=style,
        )
        imports |= imp
        parts.append(body)
    return _make_test(imports, "\n".join(parts))


def fuzz(func: Callable, *, except_: Except = (), style: str = "pytest") -> str:
    """Write source code for a property-based test of ``func``.

    The resulting test checks that valid input only leads to expected exceptions.
    For example:

    .. code-block:: python

        from re import compile, error
        from hypothesis.extra import ghostwriter

        ghostwriter.fuzz(compile, except_=error)

    Gives:

    .. code-block:: python

        # This test code was written by the `hypothesis.extra.ghostwriter` module
        # and is provided under the Creative Commons Zero public domain dedication.
        import re
        from hypothesis import given, reject, strategies as st

        # TODO: replace st.nothing() with an appropriate strategy

        @given(pattern=st.nothing(), flags=st.just(0))
        def test_fuzz_compile(pattern, flags):
            try:
                re.compile(pattern=pattern, flags=flags)
            except re.error:
                reject()

    Note that it includes all the required imports.
    Because the ``pattern`` parameter doesn't have annotations or a default argument,
    you'll need to specify a strategy - for example :func:`~hypothesis.strategies.text`
    or :func:`~hypothesis.strategies.binary`.  After that, you have a test!
    """
    if not callable(func):
        raise InvalidArgument(f"Got non-callable func={func!r}")
    except_ = _check_except(except_)
    _check_style(style)

    imports, body = _make_test_body(
        func, test_body=_write_call(func), except_=except_, ghost="fuzz", style=style
    )
    return _make_test(imports, body)


def idempotent(func: Callable, *, except_: Except = (), style: str = "pytest") -> str:
    """Write source code for a property-based test of ``func``.

    The resulting test checks that if you call ``func`` on it's own output,
    the result does not change.  For example:

    .. code-block:: python

        from typing import Sequence
        from hypothesis.extra import ghostwriter

        def timsort(seq: Sequence[int]) -> Sequence[int]:
            return sorted(seq)

        ghostwriter.idempotent(timsort)

    Gives:

    .. code-block:: python

        # This test code was written by the `hypothesis.extra.ghostwriter` module
        # and is provided under the Creative Commons Zero public domain dedication.

        from hypothesis import given, strategies as st

        @given(seq=st.one_of(st.binary(), st.binary().map(bytearray), st.lists(st.integers())))
        def test_idempotent_timsort(seq):
            result = timsort(seq=seq)
            repeat = timsort(seq=result)
            assert result == repeat, (result, repeat)
    """
    if not callable(func):
        raise InvalidArgument(f"Got non-callable func={func!r}")
    except_ = _check_except(except_)
    _check_style(style)

    test_body = "result = {}\nrepeat = {}\n{}".format(
        _write_call(func),
        _write_call(func, "result"),
        _assert_eq(style, "result", "repeat"),
    )

    imports, body = _make_test_body(
        func, test_body=test_body, except_=except_, ghost="idempotent", style=style
    )
    return _make_test(imports, body)


def _make_roundtrip_body(funcs, except_, style):
    first_param = next(iter(_get_params(funcs[0])))
    test_lines = [
        "value0 = " + _write_call(funcs[0]),
        *(
            f"value{i + 1} = " + _write_call(f, f"value{i}")
            for i, f in enumerate(funcs[1:])
        ),
        _assert_eq(style, first_param, f"value{len(funcs) - 1}"),
    ]
    return _make_test_body(
        *funcs,
        test_body="\n".join(test_lines),
        except_=except_,
        ghost="roundtrip",
        style=style,
    )


def roundtrip(*funcs: Callable, except_: Except = (), style: str = "pytest") -> str:
    """Write source code for a property-based test of ``funcs``.

    The resulting test checks that if you call the first function, pass the result
    to the second (and so on), the final result is equal to the first input argument.

    This is a *very* powerful property to test, especially when the config options
    are varied along with the object to round-trip.  For example, try ghostwriting
    a test for :func:`python:json.dumps` - would you have thought of all that?

    .. code-block:: shell

        hypothesis write --roundtrip json.dumps json.loads
    """
    if not funcs:
        raise InvalidArgument("Round-trip of zero functions is meaningless.")
    for i, f in enumerate(funcs):
        if not callable(f):
            raise InvalidArgument(f"Got non-callable funcs[{i}]={f!r}")
    except_ = _check_except(except_)
    _check_style(style)
    return _make_test(*_make_roundtrip_body(funcs, except_, style))


def equivalent(*funcs: Callable, except_: Except = (), style: str = "pytest") -> str:
    """Write source code for a property-based test of ``funcs``.

    The resulting test checks that calling each of the functions gives
    the same result.  This can be used as a classic 'oracle', such as testing
    a fast sorting algorithm against the :func:`python:sorted` builtin, or
    for differential testing where none of the compared functions are fully
    trusted but any difference indicates a bug (e.g. running a function on
    different numbers of threads, or simply multiple times).

    The functions should have reasonably similar signatures, as only the
    common parameters will be passed the same arguments - any other parameters
    will be allowed to vary.
    """
    if len(funcs) < 2:
        raise InvalidArgument("Need at least two functions to compare.")
    for i, f in enumerate(funcs):
        if not callable(f):
            raise InvalidArgument(f"Got non-callable funcs[{i}]={f!r}")
    except_ = _check_except(except_)
    _check_style(style)

    var_names = [f"result_{f.__name__}" for f in funcs]
    if len(set(var_names)) < len(var_names):
        var_names = [f"result_{i}_{ f.__name__}" for i, f in enumerate(funcs)]
    test_lines = [
        vname + " = " + _write_call(f) for vname, f in zip(var_names, funcs)
    ] + [_assert_eq(style, var_names[0], vname) for vname in var_names[1:]]

    imports, body = _make_test_body(
        *funcs,
        test_body="\n".join(test_lines),
        except_=except_,
        ghost="equivalent",
        style=style,
    )
    return _make_test(imports, body)


X = TypeVar("X")
Y = TypeVar("Y")


def binary_operation(
    func: Callable[[X, X], Y],
    *,
    associative: bool = True,
    commutative: bool = True,
    identity: Union[X, InferType, None] = infer,
    distributes_over: Callable[[X, X], X] = None,
    except_: Except = (),
    style: str = "pytest",
) -> str:
    """Write property tests for the binary operation ``func``.

    While :wikipedia:`binary operations <Binary_operation>` are not particularly
    common, they have such nice properties to test that it seems a shame not to
    demonstrate them with a ghostwriter.  For an operator `f`, test that:

    - if :wikipedia:`associative <Associative_property>`,
      ``f(a, f(b, c)) == f(f(a, b), c)``
    - if :wikipedia:`commutative <Commutative_property>`, ``f(a, b) == f(b, a)``
    - if :wikipedia:`identity <Identity_element>` is not None, ``f(a, identity) == a``
    - if :wikipedia:`distributes_over <Distributive_property>` is ``+``,
      ``f(a, b) + f(a, c) == f(a, b+c)``

    For example:

    .. code-block:: python

        ghostwriter.binary_operation(
            operator.mul,
            identity=1,
            inverse=operator.div,
            distributes_over=operator.add,
            style="unittest",
        )
    """
    if not callable(func):
        raise InvalidArgument(f"Got non-callable func={func!r}")
    except_ = _check_except(except_)
    _check_style(style)
    check_type(bool, associative, "associative")
    check_type(bool, commutative, "commutative")
    if distributes_over is not None and not callable(distributes_over):
        raise InvalidArgument(
            f"distributes_over={distributes_over!r} must be an operation which "
            f"distributes over {func.__name__}"
        )
    if not any([associative, commutative, identity, distributes_over]):
        raise InvalidArgument(
            "You must select at least one property of the binary operation to test."
        )
    imports, body = _make_binop_body(
        func,
        associative=associative,
        commutative=commutative,
        identity=identity,
        distributes_over=distributes_over,
        except_=except_,
        style=style,
    )
    return _make_test(imports, body)


def _make_binop_body(
    func: Callable[[X, X], Y],
    *,
    associative: bool = True,
    commutative: bool = True,
    identity: Union[X, InferType, None] = infer,
    distributes_over: Callable[[X, X], X] = None,
    except_: Tuple[Type[Exception], ...],
    style: str,
) -> Tuple[Set[str], str]:
    # TODO: collapse togther first two strategies, keep any others (for flags etc.)
    # assign this as a global variable, which will be prepended to the test bodies
    strategies = _get_strategies(func)
    operands, b = [strategies.pop(p) for p in list(_get_params(func))[:2]]
    if repr(operands) != repr(b):
        operands |= b
    operands_name = func.__name__ + "_operands"

    all_imports = set()
    parts = []

    def maker(sub_property: str, args: str, body: str, right: str = None) -> None:
        if right is not None:
            body = f"left={body}\nright={right}\n" + _assert_eq(style, "left", "right")
        imports, body = _make_test_body(
            func,
            test_body=body,
            ghost=sub_property + "_binary_operation",
            except_=except_,
            style=style,
            given_strategies={**strategies, **{n: operands_name for n in args}},
        )
        all_imports.update(imports)
        if style == "unittest":
            endline = "(unittest.TestCase):\n"
            body = body[body.index(endline) + len(endline) + 1 :]
        parts.append(body)

    if associative:
        maker(
            "associative",
            "abc",
            _write_call(func, "a", _write_call(func, "b", "c")),
            _write_call(func, _write_call(func, "a", "b"), "c"),
        )
    if commutative:
        maker(
            "commutative",
            "ab",
            _write_call(func, "a", "b"),
            _write_call(func, "b", "a"),
        )
    if identity is not None:
        # Guess that the identity element is the minimal example from our operands
        # strategy.  This is correct often enough to be worthwhile, and close enough
        # that it's a good starting point to edit much of the rest.
        if identity is infer:
            try:
                identity = find(operands, lambda x: True)
            except Unsatisfiable:
                identity = "identity element here"  # type: ignore
        maker(
            "identity",
            "a",
            _assert_eq(style, "a", _write_call(func, "a", repr(identity))),
        )
    if distributes_over:
        maker(
            distributes_over.__name__ + "_distributes_over",
            "abc",
            _write_call(
                distributes_over,
                _write_call(func, "a", "b"),
                _write_call(func, "a", "c"),
            ),
            _write_call(func, "a", _write_call(distributes_over, "b", "c")),
        )

    operands_repr = repr(operands)
    for name in st.__all__:
        operands_repr = operands_repr.replace(f"{name}(", f"st.{name}(")
    classdef = ""
    if style == "unittest":
        classdef = f"class TestBinaryOperation{func.__name__}(unittest.TestCase):\n    "
    return (
        all_imports,
        classdef + f"{operands_name} = {operands_repr}\n" + "\n".join(parts),
    )


def ufunc(func: Callable, *, except_: Except = (), style: str = "pytest") -> str:
    """Write a property-based test for the :np-ref:`array unfunc <ufuncs.html>` ``func``.

    The resulting test checks that your ufunc or :np-ref:`gufunc
    <c-api/generalized-ufuncs.html>` has the expected broadcasting and dtype casting
    behaviour.  You will probably want to add extra assertions, but as with the other
    ghostwriters this gives you a great place to start.

    .. code-block:: shell

        hypothesis write numpy.matmul
    """
    if not _is_probably_ufunc(func):
        raise InvalidArgument(f"func={func!r} does not seem to be a ufunc")
    except_ = _check_except(except_)
    _check_style(style)
    return _make_test(*_make_ufunc_body(func, except_=except_, style=style))


def _make_ufunc_body(func, *, except_, style):

    import hypothesis.extra.numpy as npst

    if func.signature is None:
        shapes = npst.mutually_broadcastable_shapes(num_shapes=func.nin)
    else:
        shapes = npst.mutually_broadcastable_shapes(signature=func.signature)

    body = """
    input_shapes, expected_shape = shapes
    input_dtypes, expected_dtype = types.split("->")
    array_st = [npst.arrays(d, s) for d, s in zip(input_dtypes, input_shapes)]

    {array_names} = data.draw(st.tuples(*array_st))
    result = {call}

    {shape_assert}
    {type_assert}
    """.format(
        array_names=", ".join(ascii_lowercase[: func.nin]),
        call=_write_call(func, *ascii_lowercase[: func.nin]),
        shape_assert=_assert_eq(style, "result.shape", "expected_shape"),
        type_assert=_assert_eq(style, "result.dtype.char", "expected_dtype"),
    )

    imports, body = _make_test_body(
        func,
        test_body=dedent(body).strip(),
        except_=except_,
        ghost="ufunc" if func.signature is None else "gufunc",
        style=style,
        given_strategies={
            "data": st.data(),
            "shapes": shapes,
            "types": f"sampled_from({_get_qualname(func, include_module=True)}.types)"
            ".filter(lambda sig: 'O' not in sig)",
        },
    )
    imports.add("hypothesis.extra.numpy as npst")
    body = body.replace("mutually_broadcastable", "npst.mutually_broadcastable")
    return imports, body
