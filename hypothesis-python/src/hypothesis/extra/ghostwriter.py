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

You'll probably want to tweak or extend the template a little, but the
ghostwritten template will be a great place to start.  If you're pasting
several into a file, we recommend using :pypi:`autoflake` and :pypi:`isort`
- or :pypi:`shed` - to de-duplicate and sort your imports.

Legal questions?  While the ghostwriter fragments and logic is under the
MPL-2.0 license like the rest of Hypothesis, the *output* from the ghostwriter
is made available under the `Creative Commons Zero (CC0)
<https://creativecommons.org/share-your-work/public-domain/cc0/>`__
public domain dedication, so you can use it without any restrictions.

Otherwise, pick a function you'd like tested, and feed it to one of the
property-specific ghostwriter functions!  They follow imports, use but
do not require type annotations, and generally do their best to write you
a useful test.

.. note::

    The Ghostwriter module is a provisional API.  It may be changed in minor
    versions of Hypothesis, or even removed it entirely.  However, the output
    code uses only our public, supported API and will *not* break even if the
    ghostwriter which wrote it goes away.

    It requires Python 3.6+ and :pypi:`black` to run, while the generated code
    requires Python 3.5+ and no dependencies beyond Hypothesis itself.
"""

import builtins
import enum
import inspect
from collections import OrderedDict
from itertools import zip_longest
from textwrap import indent
from typing import Callable, Dict, Tuple, Type, Union

import black

from hypothesis import strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.strategies._internal.strategies import OneOfStrategy
from hypothesis.utils.conventions import InferType, infer

IMPORT_SECTION = """
# This test code was written by the `hypothesis.extra.ghostwriter` module
# and is provided under the Creative Commons Zero public domain dedication.
{imports}
"""

TEMPLATE = """
{nothing_hint}@given({given_args})
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
                    f" (type={type(e).__name__})"
                )
        return except_
    if not isinstance(except_, type) or not issubclass(except_, Exception):
        raise InvalidArgument(
            "Expected an Exception or tuple of exceptions, but got except_="
            f"{except_!r} (type={type(except_).__name__})"
        )
    return (except_,)


def _check_style(style: str) -> None:
    if style not in ("pytest", "unittest"):
        raise InvalidArgument(f"Valid styles are 'pytest' or 'unittest', got {style!r}")


def _strategy_for(param: inspect.Parameter) -> Union[st.SearchStrategy, InferType]:
    # We use `infer` and go via `builds()` instead of directly through
    # `from_type()` so that `get_type_hints()` can resolve any forward
    # references for us.
    if param.annotation is not inspect.Parameter.empty:
        return infer
    # If there's no annotation and no default value, the user will have to
    # fill this in later.  We use nothing() as a placeholder to this effect.
    if param.default is inspect.Parameter.empty:
        return st.nothing()
    # If our default value is an Enum or a boolean, we assume that any value
    # of that type is acceptable.  Otherwise, we only generate the default.
    if isinstance(param.default, bool):
        return st.booleans()
    if isinstance(param.default, enum.Enum):
        return st.sampled_from(type(param.default))
    return st.just(param.default)


def _get_params(func: Callable) -> Dict[str, inspect.Parameter]:
    """Get non-vararg parameters of `func` as an ordered dict."""
    var_param_kinds = (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    params = list(inspect.signature(func).parameters.values())
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
            if repr(given_strategies.get(k, v)) != repr(v):
                given_strategies[k] = given_strategies[k] | v
            else:
                given_strategies[k] = v

    # If there is only one function, we pass arguments to @given in the order of
    # that function's signature.  Otherwise, we use alphabetical order.
    if len(funcs) == 1:
        indexer = list(_get_params(f)).index
        return OrderedDict(
            sorted(given_strategies.items(), key=lambda kv: indexer(kv[0]))
        )
    return given_strategies


def _assert_eq(style, a, b):
    return {
        "pytest": f"assert {a} == {b}, ({a}, {b})",
        "unittest": f"self.assertEqual({a}, {b})",
    }[style]


def _valid_syntax_repr(strategy):
    # Return a syntactically-valid strategy repr, including fixing some
    # strategy reprs and replacing invalid syntax reprs with `"nothing()"`.
    # String-replace to hide the special case in from_type() for Decimal('snan')
    r = repr(strategy).replace(".filter(_can_hash)", "")
    try:
        compile(r, "<string>", "eval")
        return r
    except SyntaxError:
        return "nothing()"


def _get_qualname(obj):
    # Replacing angle-brackets for objects defined in `.<locals>.`
    qname = obj.__qualname__.replace("<", "_").replace(">", "_")
    if obj.__module__ not in qname:
        # to fix up e.g. `json.dumps.__qualname__ == "dumps"`
        return obj.__module__ + "." + obj.__name__
    return qname


def _write_call(func: Callable, *pass_variables: str) -> str:
    """Write a call to `func` with explicit and implicit arguments.

    >>> _write_call(sorted, "my_seq")
    "builtins.sorted(iterable=my_seq, key=key, reverse=reverse)"
    """
    pos_only = {
        p.name
        for p in inspect.signature(func).parameters.values()
        if p.kind is inspect.Parameter.POSITIONAL_ONLY
    }
    args = ", ".join(
        (v or p) if p in pos_only else f"{p}={v or p}"
        for v, p in zip_longest(pass_variables, _get_params(func))
    )
    return f"{_get_qualname(func)}({args})"


def _make_test(
    *funcs: Callable,
    ghost: str,
    test_body: str,
    except_: Tuple[Type[Exception], ...],
    style: str,
) -> str:
    # the common elements of each ghostwriter
    given_strategies = _get_strategies(
        *funcs, pass_result_to_next_func=ghost in ("idempotent", "roundtrip")
    )
    given_args = ", ".join(
        "{}={}".format(k, _valid_syntax_repr(v)) for k, v in given_strategies.items()
    )
    for name in st.__all__:
        given_args = given_args.replace(f"{name}(", f"st.{name}(")
    imports = {f.__module__ for f in funcs}
    # We discard "builtins." below - this is probably not particularly useful
    # for user code, but important for making a good impression in demos.
    imports.discard("builtins")
    imports.discard("__main__")

    if except_:
        exceptions = []
        for ex in except_:
            if ex.__name__ in dir(builtins):
                exceptions.append(ex.__name__)
            else:
                imports.add(ex.__module__)
                exceptions.append(_get_qualname(ex))
        test_body = SUPPRESS_BLOCK.format(
            test_body=indent(test_body, prefix="    "),
            exceptions="(" + ", ".join(exceptions) + ")"
            if len(exceptions) > 1
            else exceptions[0],
        )

    argnames = (["self"] if style == "unittest" else []) + list(given_strategies)
    body = TEMPLATE.format(
        nothing_hint=""
        if "=st.nothing()" not in given_args
        else "# TODO: replace st.nothing() with an appropriate strategy\n\n",
        given_args=given_args,
        test_kind=ghost,
        func_name="_".join(f.__name__ for f in funcs),
        arg_names=", ".join(argnames),
        test_body=indent(test_body, prefix="    "),
    )
    body = body.replace("builtins.", "").replace("__main__.", "")

    if style == "unittest":
        imports.add("unittest")
        body = "class Test{}{}(unittest.TestCase):\n".format(
            ghost.title(), "".join(f.__name__.title() for f in funcs)
        ) + indent(body, "    ")

    result = (
        IMPORT_SECTION.format(
            imports="\n".join("import " + imp for imp in sorted(imports))
        )
        + "\nfrom hypothesis import given, {}strategies as st\n\n".format(
            "reject, " if except_ else ""
        )
        + body
    )
    return black.format_str(result, mode=black.FileMode())


def fuzz(func: Callable, *, except_: Except = (), style: str = "pytest") -> str:
    """Write source code for a property-based test of ``func``.

    As for all ghostwriters, the ``except_`` argument should be an
    :class:`python:Exception` or tuple of exceptions, and ``style`` may be either
    ``"pytest"`` to write a test function or ``"unittest"`` to write a test method
    and :class:`~python:unittest.TestCase`.

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
    return _make_test(
        func, test_body=_write_call(func), except_=except_, ghost="fuzz", style=style
    )


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
    return _make_test(
        func, test_body=test_body, except_=except_, ghost="idempotent", style=style
    )


def roundtrip(*funcs: Callable, except_: Except = (), style: str = "pytest") -> str:
    """Write source code for a property-based test of ``funcs``.

    The resulting test checks that if you call the first function, pass the result
    to the second (and so on), the final result is equal to the first input argument.

    This is a *very* powerful property to test, especially when the config options
    are varied along with the object to round-trip.  For example, try ghostwriting
    a test for :func:`python:json.dumps` - would you have thought of all that?

    .. code-block:: shell

        hypothesis write roundtrip json.dumps json.loads
    """
    if not funcs:
        raise InvalidArgument("Round-trip of zero functions is meaningless.")
    for i, f in enumerate(funcs):
        if not callable(f):
            raise InvalidArgument(f"Got non-callable funcs[{i}]={f!r}")
    except_ = _check_except(except_)
    _check_style(style)

    first_param = next(iter(_get_params(funcs[0])))
    test_lines = [
        "value0 = " + _write_call(funcs[0]),
        *(
            f"value{i + 1} = " + _write_call(f, f"value{i}")
            for i, f in enumerate(funcs[1:])
        ),
        _assert_eq(style, first_param, f"value{len(funcs) - 1}"),
    ]

    return _make_test(
        *funcs,
        test_body="\n".join(test_lines),
        except_=except_,
        ghost="roundtrip",
        style=style,
    )


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

    var_names = ["result_" + f.__name__ for f in funcs]
    assert len(set(var_names)) == len(var_names), "variable name collision"
    test_lines = [
        vname + " = " + _write_call(f) for vname, f in zip(var_names, funcs)
    ] + [_assert_eq(style, var_names[0], vname) for vname in var_names[1:]]

    return _make_test(
        *funcs,
        test_body="\n".join(test_lines),
        except_=except_,
        ghost="equivalent",
        style=style,
    )
