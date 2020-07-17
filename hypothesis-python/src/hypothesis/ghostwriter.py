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
WARNING: this module is under development and should not be used... yet.
See https://github.com/HypothesisWorks/hypothesis/pull/2344 for progress.
"""

import builtins
import enum
import inspect
from collections import OrderedDict
from textwrap import indent
from typing import Callable, Dict, Tuple, Type, Union

from hypothesis import strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.utils.conventions import InferType, infer

IMPORT_SECTION = """
# This test template was produced by the `hypothesis.ghostwriter` module.
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
                    "Expected an Exception but got except_[%s]=%r (type=%s)"
                    % (i, e, type(e).__name__)
                )
        return except_
    if not isinstance(except_, type) or not issubclass(except_, Exception):
        raise InvalidArgument(
            "Expected an Exception or tuple of exceptions, but got except_=%r (type=%s)"
            % (except_, type(except_).__name__)
        )
    return (except_,)


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
    var_param_kinds = (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    params = list(inspect.signature(func).parameters.values())
    return OrderedDict((p.name, p) for p in params if p.kind not in var_param_kinds)


def _get_strategies(*funcs: Callable) -> Dict[str, st.SearchStrategy]:
    given_strategies = {}  # type: Dict[str, st.SearchStrategy]
    for _, f in enumerate(funcs):
        params = _get_params(f)
        builder_args = {k: _strategy_for(v) for k, v in params.items()}
        strat = st.builds(f, **builder_args).wrapped_strategy  # type: ignore

        args, kwargs = strat.mapped_strategy.wrapped_strategy.element_strategies
        if args.element_strategies:
            raise NotImplementedError("Expected to pass everything as kwargs")

        for k, v in zip(kwargs.keys, kwargs.mapped_strategy.element_strategies):
            given_strategies[k] = v

    indexer = list(_get_params(f)).index
    return OrderedDict(sorted(given_strategies.items(), key=lambda kv: indexer(kv[0])))


def _make_test(
    *funcs: Callable, ghost: str, test_body: str, except_: Tuple[Type[Exception], ...]
) -> str:
    # the common elements of each ghostwriter
    given_strategies = _get_strategies(*funcs)
    given_args = ", ".join(
        "{}={!r}".format(k, v)
        .replace("sampled_from([False, True])", "booleans()")
        .replace("just(None)", "none()")
        .replace(".filter(_can_hash)", "")  # hide the special case for Decimal('snan')
        for k, v in given_strategies.items()
    )
    for name in st.__all__:
        given_args = given_args.replace("{}(".format(name), "st.{}(".format(name))
    imports = {f.__module__ for f in funcs}
    # We discard "builtins." below - this is probably not particularly useful
    # for user code, but important for making a good impression in demos.
    imports.discard("builtins")

    if except_:
        exceptions = []
        for ex in except_:
            if ex.__name__ in dir(builtins):
                exceptions.append(ex.__name__)
            else:
                imports.add(ex.__module__)
                exceptions.append(ex.__module__ + "." + ex.__name__)
        test_body = SUPPRESS_BLOCK.format(
            test_body=indent(test_body, prefix="    "),
            exceptions="(" + ", ".join(exceptions) + ")"
            if len(exceptions) > 1
            else exceptions[0],
        )

    argnames = list(given_strategies)
    body = TEMPLATE.format(
        nothing_hint=""
        if "=st.nothing()" not in given_args
        else "# TODO: replace st.nothing() with an appropriate strategy\n\n",
        given_args=given_args,
        test_kind=ghost,
        func_name="_".join(f.__name__ for f in funcs),
        arg_names=", ".join(argnames),
        test_body=indent(test_body, prefix="    "),
    ).replace("builtins.", "")

    result = (
        IMPORT_SECTION.format(
            imports=("import " + "\nimport ".join(sorted(imports)) if imports else "")
        )
        + "\nfrom hypothesis import given, {}strategies as st\n\n".format(
            "reject, " if except_ else ""
        )
        + body
    )
    try:
        import black
    except ImportError:
        return result
    else:
        return black.format_str(result, mode=black.FileMode())  # pragma: no cover


def fuzz(func: Callable, *, except_: Except = ()) -> str:
    """Write source code for a property-based test of ``func``."""
    if not callable(func):
        raise InvalidArgument("Got non-callable func=%r" % (func,))
    except_ = _check_except(except_)

    params = _get_params(func)
    test_body = "{}.{}({})".format(
        func.__module__, func.__name__, ", ".join("{0}={0}".format(p) for p in params)
    )
    return _make_test(func, test_body=test_body, except_=except_, ghost="fuzz")
