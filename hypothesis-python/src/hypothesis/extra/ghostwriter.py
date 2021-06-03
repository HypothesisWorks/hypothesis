# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
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
below.  They follow imports, use but do not require type annotations, and
generally do their best to write you a useful test.  You can also use
:ref:`our command-line interface <hypothesis-cli>`::

    $ hypothesis write --help
    Usage: hypothesis write [OPTIONS] FUNC...

      `hypothesis write` writes property-based tests for you!

      Type annotations are helpful but not required for our advanced
      introspection and templating logic.  Try running the examples below to see
      how it works:

          hypothesis write gzip
          hypothesis write numpy.matmul
          hypothesis write re.compile --except re.error
          hypothesis write --equivalent ast.literal_eval eval
          hypothesis write --roundtrip json.dumps json.loads
          hypothesis write --style=unittest --idempotent sorted
          hypothesis write --binary-op operator.add

    Options:
      --roundtrip                start by testing write/read or encode/decode!
      --equivalent               very useful when optimising or refactoring code
      --idempotent
      --binary-op
      --style [pytest|unittest]  pytest-style function, or unittest-style method?
      -e, --except OBJ_NAME      dotted name of exception(s) to ignore
      -h, --help                 Show this message and exit.

.. note::

    The ghostwriter requires :pypi:`black`, but the generated code only
    requires Hypothesis itself.

.. note::

    Legal questions?  While the ghostwriter fragments and logic is under the
    MPL-2.0 license like the rest of Hypothesis, the *output* from the ghostwriter
    is made available under the `Creative Commons Zero (CC0)
    <https://creativecommons.org/share-your-work/public-domain/cc0/>`__
    public domain dedication, so you can use it without any restrictions.
"""

import ast
import builtins
import contextlib
import enum
import inspect
import os
import re
import sys
import types
from collections import OrderedDict, defaultdict
from itertools import permutations, zip_longest
from string import ascii_lowercase
from textwrap import dedent, indent
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import black

from hypothesis import Verbosity, find, settings, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.internal.compat import get_type_hints
from hypothesis.internal.reflection import is_mock
from hypothesis.internal.validation import check_type
from hypothesis.strategies._internal.core import BuildsStrategy
from hypothesis.strategies._internal.flatmapped import FlatMapStrategy
from hypothesis.strategies._internal.lazy import LazyStrategy, unwrap_strategies
from hypothesis.strategies._internal.strategies import (
    FilteredStrategy,
    MappedSearchStrategy,
    OneOfStrategy,
    SampledFromStrategy,
)
from hypothesis.strategies._internal.types import _global_type_lookup, is_generic_type
from hypothesis.utils.conventions import InferType, infer

IMPORT_SECTION = """
# This test code was written by the `hypothesis.extra.ghostwriter` module
# and is provided under the Creative Commons Zero public domain dedication.

{imports}
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
""".rstrip()

Except = Union[Type[Exception], Tuple[Type[Exception], ...]]
RE_TYPES = (type(re.compile(".")), type(re.match(".", "abc")))
_quietly_settings = settings(
    database=None,
    deadline=None,
    derandomize=True,
    verbosity=Verbosity.quiet,
)


def _dedupe_exceptions(exc: Tuple[Type[Exception], ...]) -> Tuple[Type[Exception], ...]:
    # This is reminiscent of de-duplication logic I wrote for flake8-bugbear,
    # but with access to the actual objects we can just check for subclasses.
    # This lets us print e.g. `Exception` instead of `(Exception, OSError)`.
    uniques = list(exc)
    for a, b in permutations(exc, 2):
        if a in uniques and issubclass(a, b):
            uniques.remove(a)
    return tuple(sorted(uniques, key=lambda e: e.__name__))


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


def _exceptions_from_docstring(doc: str) -> Tuple[Type[Exception], ...]:
    """Return a tuple of exceptions that the docstring says may be raised.

    Note that we ignore non-builtin exception types for simplicity, as this is
    used directly in _write_call() and passing import sets around would be really
    really annoying.
    """
    # TODO: it would be great to handle Google- and Numpy-style docstrings
    #       (e.g. by using the Napoleon Sphinx extension)
    assert isinstance(doc, str), doc
    raises = []
    for excname in re.compile(r"\:raises\s+(\w+)\:", re.MULTILINE).findall(doc):
        exc_type = getattr(builtins, excname, None)
        if isinstance(exc_type, type) and issubclass(exc_type, Exception):
            raises.append(exc_type)
    return tuple(_dedupe_exceptions(tuple(raises)))


# Simple strategies to guess for common argument names - we wouldn't do this in
# builds() where strict correctness is required, but we only use these guesses
# when the alternative is nothing() to force user edits anyway.
#
# This table was constructed manually after skimming through the documentation
# for the builtins and a few stdlib modules.  Future enhancements could be based
# on analysis of type-annotated code to detect arguments which almost always
# take values of a particular type.
_GUESS_STRATEGIES_BY_NAME = (
    (st.integers(0, 32), ["ndims"]),
    (st.booleans(), ["keepdims"]),
    (st.text(), ["name", "filename", "fname"]),
    (st.floats(), ["real", "imag"]),
    (st.functions(), ["function", "func", "f"]),
    (st.functions(returns=st.booleans(), pure=True), ["pred", "predicate"]),
    (st.iterables(st.integers()) | st.iterables(st.text()), ["iterable"]),
)


def _type_from_doc_fragment(token: str) -> Optional[type]:
    # Special cases for "integer" and for numpy array-like and dtype
    if token == "integer":
        return int
    if "numpy" in sys.modules:
        if re.fullmatch(r"[Aa]rray[-_ ]?like", token):
            return sys.modules["numpy"].ndarray  # type: ignore
        elif token == "dtype":
            return sys.modules["numpy"].dtype  # type: ignore
    # Natural-language syntax, e.g. "sequence of integers"
    coll_match = re.fullmatch(r"(\w+) of (\w+)", token)
    if coll_match is not None:
        coll_token, elem_token = coll_match.groups()
        elems = _type_from_doc_fragment(elem_token)
        if elems is None and elem_token.endswith("s"):
            elems = _type_from_doc_fragment(elem_token[:-1])
        if elems is not None and coll_token in ("list", "sequence", "collection"):
            return List[elems]  # type: ignore
        # This might be e.g. "array-like of float"; arrays is better than nothing
        # even if we can't conveniently pass a generic type around.
        return _type_from_doc_fragment(coll_token)
    # Check either builtins, or the module for a dotted name
    if "." not in token:
        return getattr(builtins, token, None)
    mod, name = token.rsplit(".", maxsplit=1)
    return getattr(sys.modules.get(mod, None), name, None)


def _strategy_for(
    param: inspect.Parameter,
    docstring: str,
) -> Union[st.SearchStrategy, InferType]:
    # Example types in docstrings:
    # - `:type a: sequence of integers`
    # - `b (list, tuple, or None): ...`
    # - `c : {"foo", "bar", or None}`
    for pattern in (
        fr"^\s*\:type\s+{param.name}\:\s+(.+)",  # RST-style
        fr"^\s*{param.name} \((.+)\):",  # Google-style
        fr"^\s*{param.name} \: (.+)",  # Numpy-style
    ):
        match = re.search(pattern, docstring, flags=re.MULTILINE)
        if match is None:
            continue
        doc_type = match.group(1)
        if doc_type.endswith(", optional"):
            # Convention to describe "argument may be omitted"
            doc_type = doc_type[: -len(", optional")]
        doc_type = doc_type.strip("}{")
        elements = []
        types = []
        for token in re.split(r",? +or +| *, *", doc_type):
            for prefix in ("default ", "python "):
                # `str or None, default "auto"`; `python int or numpy.int64`
                if token.startswith(prefix):
                    token = token[len(prefix) :]
            if not token:
                continue
            try:
                # Elements of `{"inner", "outer"}` etc.
                elements.append(ast.literal_eval(token))
                continue
            except (ValueError, SyntaxError):
                t = _type_from_doc_fragment(token)
                if isinstance(t, type) or is_generic_type(t):
                    assert t is not None
                    types.append(t)
        if (
            param.default is not inspect.Parameter.empty
            and param.default not in elements
            and not isinstance(
                param.default, tuple(t for t in types if isinstance(t, type))
            )
        ):
            with contextlib.suppress(SyntaxError):
                compile(repr(st.just(param.default)), "<string>", "eval")
                elements.insert(0, param.default)
        if elements or types:
            return (st.sampled_from(elements) if elements else st.nothing()) | (
                st.one_of(*map(st.from_type, types)) if types else st.nothing()
            )

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
            assert isinstance(strategy, st.SearchStrategy)
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


@contextlib.contextmanager
def _with_any_registered():
    # If the user has registered their own strategy for Any, leave it alone
    if Any in _global_type_lookup:
        yield
    # We usually want to force from_type(Any) to raise an error because we don't
    # have enough information to accurately resolve user intent, but in this case
    # we can treat it as a synonym for object - this is probably wrong, but you'll
    # get at least _some_ output to edit later.  We then reset everything in order
    # to avoid polluting the resolution logic in case you run tests later.
    else:
        try:
            _global_type_lookup[Any] = st.builds(object)
            yield
        finally:
            del _global_type_lookup[Any]
            st.from_type.__clear_cache()


def _get_strategies(
    *funcs: Callable, pass_result_to_next_func: bool = False
) -> Dict[str, st.SearchStrategy]:
    """Return a dict of strategies for the union of arguments to `funcs`.

    If `pass_result_to_next_func` is True, assume that the result of each function
    is passed to the next, and therefore skip the first argument of all but the
    first function.

    This dict is used to construct our call to the `@given(...)` decorator.
    """
    assert funcs, "Must pass at least one function"
    given_strategies: Dict[str, st.SearchStrategy] = {}
    for i, f in enumerate(funcs):
        params = _get_params(f)
        if pass_result_to_next_func and i >= 1:
            del params[next(iter(params))]
        hints = get_type_hints(f)
        docstring = getattr(f, "__doc__", None) or ""
        builder_args = {
            k: infer if k in hints else _strategy_for(v, docstring)
            for k, v in params.items()
        }
        with _with_any_registered():
            strat = st.builds(f, **builder_args).wrapped_strategy  # type: ignore

        if strat.args:
            raise NotImplementedError("Expected to pass everything as kwargs")

        for k, v in strat.kwargs.items():
            if _valid_syntax_repr(v)[1] == "nothing()" and k in hints:
                # e.g. from_type(Hashable) is OK but the unwrapped repr is not
                v = LazyStrategy(st.from_type, (hints[k],), {})
            if k in given_strategies:
                given_strategies[k] |= v
            else:
                given_strategies[k] = v

    # If there is only one function, we pass arguments to @given in the order of
    # that function's signature.  Otherwise, we use alphabetical order.
    if len(funcs) == 1:
        return {name: given_strategies[name] for name in _get_params(f)}
    return dict(sorted(given_strategies.items()))


def _assert_eq(style: str, a: str, b: str) -> str:
    if style == "unittest":
        return f"self.assertEqual({a}, {b})"
    assert style == "pytest"
    if a.isidentifier() and b.isidentifier():
        return f"assert {a} == {b}, ({a}, {b})"
    return f"assert {a} == {b}"


def _imports_for_object(obj):
    """Return the imports for `obj`, which may be empty for e.g. lambdas"""
    if isinstance(obj, RE_TYPES):
        return {"re"}
    try:
        if is_generic_type(obj):
            if isinstance(obj, TypeVar):
                return {(obj.__module__, obj.__name__)}
            with contextlib.suppress(Exception):
                return set().union(*map(_imports_for_object, obj.__args__))
        if (not callable(obj)) or obj.__name__ == "<lambda>":
            return set()
        name = _get_qualname(obj).split(".")[0]
        return {(_get_module(obj), name)}
    except Exception:
        with contextlib.suppress(AttributeError):
            if obj.__module__ == "typing":  # only on CPython 3.6
                return {("typing", getattr(obj, "__name__", obj.name))}
        return set()


def _imports_for_strategy(strategy):
    # If we have a lazy from_type strategy, because unwrapping it gives us an
    # error or invalid syntax, import that type and we're done.
    if isinstance(strategy, LazyStrategy):
        if strategy.function is st.from_type:
            return _imports_for_object(strategy._LazyStrategy__args[0])
        elif _get_module(strategy.function).startswith("hypothesis.extra."):
            return {(_get_module(strategy.function), strategy.function.__name__)}

    imports = set()
    strategy = unwrap_strategies(strategy)

    # Get imports for s.map(f), s.filter(f), s.flatmap(f), including both s and f
    if isinstance(strategy, MappedSearchStrategy):
        imports |= _imports_for_strategy(strategy.mapped_strategy)
        imports |= _imports_for_object(strategy.pack)
    if isinstance(strategy, FilteredStrategy):
        imports |= _imports_for_strategy(strategy.filtered_strategy)
        for f in strategy.flat_conditions:
            imports |= _imports_for_object(f)
    if isinstance(strategy, FlatMapStrategy):
        imports |= _imports_for_strategy(strategy.flatmapped_strategy)
        imports |= _imports_for_object(strategy.expand)

    # recurse through one_of to handle e.g. from_type(Optional[Foo])
    if isinstance(strategy, OneOfStrategy):
        for s in strategy.element_strategies:
            imports |= _imports_for_strategy(s)

    # get imports for the target of builds(), and recurse into the argument strategies
    if isinstance(strategy, BuildsStrategy):
        imports |= _imports_for_object(strategy.target)
        for s in strategy.args:
            imports |= _imports_for_strategy(s)
        for s in strategy.kwargs.values():
            imports |= _imports_for_strategy(s)

    if isinstance(strategy, SampledFromStrategy):
        for obj in strategy.elements:
            imports |= _imports_for_object(obj)

    return imports


def _valid_syntax_repr(strategy):
    # For binary_op, we pass a variable name - so pass it right back again.
    if isinstance(strategy, str):
        return set(), strategy
    # Flatten and de-duplicate any one_of strategies, whether that's from resolving
    # a Union type or combining inputs to multiple functions.
    try:
        if isinstance(strategy, OneOfStrategy):
            seen = set()
            elems = []
            for s in strategy.element_strategies:
                if isinstance(s, SampledFromStrategy) and s.elements == (os.environ,):
                    continue
                if repr(s) not in seen:
                    elems.append(s)
                    seen.add(repr(s))
            strategy = st.one_of(elems or st.nothing())
        # Trivial special case because the wrapped repr for text() is terrible.
        if strategy == st.text().wrapped_strategy:
            return set(), "text()"
        # Return a syntactically-valid strategy repr, including fixing some
        # strategy reprs and replacing invalid syntax reprs with `"nothing()"`.
        # String-replace to hide the special case in from_type() for Decimal('snan')
        r = repr(strategy).replace(".filter(_can_hash)", "")
        # Replace <unknown> with ... in confusing lambdas
        r = re.sub(r"(lambda.*?: )(<unknown>)([,)])", r"\1...\3", r)
        compile(r, "<string>", "eval")
        # Finally, try to work out the imports we need for builds(), .map(),
        # .filter(), and .flatmap() to work without NameError
        imports = {i for i in _imports_for_strategy(strategy) if i[1] in r}
        return imports, r
    except (SyntaxError, RecursionError, InvalidArgument):
        return set(), "nothing()"


# When we ghostwrite for a module, we want to treat that as the __module__ for
# each function, rather than whichever internal file it was actually defined in.
KNOWN_FUNCTION_LOCATIONS: Dict[object, str] = {}


def _get_module(obj):
    if obj in KNOWN_FUNCTION_LOCATIONS:
        return KNOWN_FUNCTION_LOCATIONS[obj]
    try:
        return obj.__module__
    except AttributeError:
        if not _is_probably_ufunc(obj):
            raise
    for module_name in sorted(sys.modules, key=lambda n: tuple(n.split("."))):
        if obj is getattr(sys.modules[module_name], obj.__name__, None):
            KNOWN_FUNCTION_LOCATIONS[obj] = module_name
            return module_name
    raise RuntimeError(f"Could not find module for ufunc {obj.__name__} ({obj!r}")


def _get_qualname(obj, include_module=False):
    # Replacing angle-brackets for objects defined in `.<locals>.`
    qname = getattr(obj, "__qualname__", obj.__name__)
    qname = qname.replace("<", "_").replace(">", "_").replace(" ", "")
    if include_module:
        return _get_module(obj) + "." + qname
    return qname


def _write_call(
    func: Callable, *pass_variables: str, except_: Except, assign: str = ""
) -> str:
    """Write a call to `func` with explicit and implicit arguments.

    >>> _write_call(sorted, "my_seq", "func")
    "builtins.sorted(my_seq, key=func, reverse=reverse)"

    >>> write_call(f, assign="var1")
    "var1 = f()"

    The fancy part is that we'll check the docstring for any known exceptions
    which `func` might raise, and catch-and-reject on them... *unless* they're
    subtypes of `except_`, which will be handled in an outer try-except block.
    """
    args = ", ".join(
        (v or p.name)
        if p.kind is inspect.Parameter.POSITIONAL_ONLY
        else f"{p.name}={v or p.name}"
        for v, p in zip_longest(pass_variables, _get_params(func).values())
    )
    call = f"{_get_qualname(func, include_module=True)}({args})"
    if assign:
        call = f"{assign} = {call}"
    raises = _exceptions_from_docstring(getattr(func, "__doc__", "") or "")
    exnames = [ex.__name__ for ex in raises if not issubclass(ex, except_)]
    if not exnames:
        return call
    return SUPPRESS_BLOCK.format(
        test_body=indent(call, prefix="    "),
        exceptions="(" + ", ".join(exnames) + ")" if len(exnames) > 1 else exnames[0],
    )


def _st_strategy_names(s: str) -> str:
    """Replace strategy name() with st.name().

    Uses a tricky re.sub() to avoid problems with frozensets() matching
    sets() too.
    """
    names = "|".join(sorted(st.__all__, key=len, reverse=True))
    return re.sub(pattern=rf"\b(?:{names})\(", repl=r"st.\g<0>", string=s)


def _make_test_body(
    *funcs: Callable,
    ghost: str,
    test_body: str,
    except_: Tuple[Type[Exception], ...],
    assertions: str = "",
    style: str,
    given_strategies: Optional[Mapping[str, Union[str, st.SearchStrategy]]] = None,
) -> Tuple[Set[Union[str, Tuple[str, str]]], str]:
    # A set of modules to import - we might add to this later.  The import code
    # is written later, so we can have one import section for multiple magic()
    # test functions.
    imports = {_get_module(f) for f in funcs}

    # Get strategies for all the arguments to each function we're testing.
    with _with_any_registered():
        given_strategies = given_strategies or _get_strategies(
            *funcs, pass_result_to_next_func=ghost in ("idempotent", "roundtrip")
        )
        reprs = [((k,) + _valid_syntax_repr(v)) for k, v in given_strategies.items()]
        imports = imports.union(*(imp for _, imp, _ in reprs))
        given_args = ", ".join(f"{k}={v}" for k, _, v in reprs)
    given_args = _st_strategy_names(given_args)

    if except_:
        # Convert to strings, either builtin names or qualified names.
        exceptions = []
        for ex in _dedupe_exceptions(except_):
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

    if assertions:
        test_body = f"{test_body}\n{assertions}"

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
        body = "class Test{}{}(unittest.TestCase):\n{}".format(
            ghost.title(),
            "".join(_get_qualname(f).replace(".", "").title() for f in funcs),
            indent(body, "    "),
        )

    return imports, body


def _make_test(imports: Set[Union[str, Tuple[str, str]]], body: str) -> str:
    # Discarding "builtins." and "__main__" probably isn't particularly useful
    # for user code, but important for making a good impression in demos.
    body = body.replace("builtins.", "").replace("__main__.", "")
    if "st.from_type(typing." in body:
        imports.add("typing")
    imports |= {("hypothesis", "given"), ("hypothesis", "strategies as st")}
    if "        reject()\n" in body:
        imports.add(("hypothesis", "reject"))

    do_not_import = {"builtins", "__main__"}
    direct = {f"import {i}" for i in imports - do_not_import if isinstance(i, str)}
    from_imports = defaultdict(set)
    for module, name in {i for i in imports if isinstance(i, tuple)}:
        from_imports[module].add(name)
    from_ = {
        "from {} import {}".format(module, ", ".join(sorted(names)))
        for module, names in from_imports.items()
        if isinstance(module, str) and module not in do_not_import
    }
    header = IMPORT_SECTION.format(imports="\n".join(sorted(direct) + sorted(from_)))
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
    (r"(.*)en(.+)", "{}de{}"),
    # Shared postfix, prefix only on "inverse" function
    (r"(.+)", "de{}"),
    (r"(?!safe)(.+)", "un{}"),  # safe_load / unsafe_load isn't a roundtrip
    # a2b_postfix and b2a_postfix.  Not a fan of this pattern, but it's pretty
    # common in code imitating an C API - see e.g. the stdlib binascii module.
    (r"(.+)2(.+?)(_.+)?", "{1}2{0}{2}"),
    # Common in e.g. the colorsys module
    (r"(.+)_to_(.+)", "{1}_to_{0}"),
    # Sockets patterns
    (r"(inet|if)_(.+)to(.+)", "{0}_{2}to{1}"),
    (r"(\w)to(\w)(.+)", "{1}to{0}{2}"),
    (r"send(.+)", "recv{}"),
    (r"send(.+)", "receive{}"),
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
                funcs = [getattr(thing, name, None) for name in thing.__all__]  # type: ignore
            else:
                pkg = thing.__package__
                funcs = [
                    v
                    for k, v in vars(thing).items()
                    if callable(v)
                    and not is_mock(v)
                    and ((not pkg) or getattr(v, "__module__", pkg).startswith(pkg))
                    and not k.startswith("_")
                ]
                if pkg and any(getattr(f, "__module__", pkg) == pkg for f in funcs):
                    funcs = [f for f in funcs if getattr(f, "__module__", pkg) == pkg]
            for f in funcs:
                try:
                    if (
                        (not is_mock(f))
                        and callable(f)
                        and _get_params(f)
                        and not isinstance(f, enum.EnumMeta)
                    ):
                        functions.add(f)
                        if getattr(thing, "__name__", None):
                            KNOWN_FUNCTION_LOCATIONS[f] = thing.__name__
                except (TypeError, ValueError):
                    pass
        else:
            raise InvalidArgument(f"Can't test non-module non-callable {thing!r}")

    imports = set()
    parts = []

    def make_(how, *args, **kwargs):
        imp, body = how(*args, **kwargs, except_=except_, style=style)
        imports.update(imp)
        parts.append(body)

    by_name = {}
    for f in functions:
        try:
            _get_params(f)
            by_name[_get_qualname(f, include_module=True)] = f
        except Exception:
            # usually inspect.signature on C code such as socket.inet_aton, sometimes
            # e.g. Pandas 'CallableDynamicDoc' object has no attribute '__name__'
            pass
    if not by_name:
        return (
            f"# Found no testable functions in\n"
            f"# {functions!r} from {modules_or_functions}\n"
        )

    # Look for pairs of functions that roundtrip, based on known naming patterns.
    for writename, readname in ROUNDTRIP_PAIRS:
        for name in sorted(by_name):
            match = re.fullmatch(writename, name.split(".")[-1])
            if match:
                inverse_name = readname.format(*match.groups())
                for other in sorted(
                    n for n in by_name if n.split(".")[-1] == inverse_name
                ):
                    make_(_make_roundtrip_body, (by_name.pop(name), by_name.pop(other)))
                    break
                else:
                    try:
                        other_func = getattr(
                            sys.modules[_get_module(by_name[name])],
                            inverse_name,
                        )
                        _get_params(other_func)  # we want to skip if this fails
                    except Exception:
                        pass
                    else:
                        make_(_make_roundtrip_body, (by_name.pop(name), other_func))

    # Look for equivalent functions: same name, all required arguments of any can
    # be found in all signatures, and if all have return-type annotations they match.
    names = defaultdict(list)
    for _, f in sorted(by_name.items()):
        names[_get_qualname(f)].append(f)
    for group in names.values():
        if len(group) >= 2 and len({frozenset(_get_params(f)) for f in group}) == 1:
            sentinel = object()
            returns = {get_type_hints(f).get("return", sentinel) for f in group}
            if len(returns - {sentinel}) <= 1:
                make_(_make_equiv_body, group)
                for f in group:
                    by_name.pop(_get_qualname(f, include_module=True))

    # Look for binary operators - functions with two identically-typed arguments,
    # and the same return type.  The latter restriction might be lifted later.
    for name, func in sorted(by_name.items()):
        hints = get_type_hints(func)
        hints.pop("return", None)
        params = _get_params(func)
        if len(hints) == len(params) == 2:
            a, b = hints.values()
            arg1, arg2 = params
            if a == b and len(arg1) == len(arg2) <= 3:
                make_(_make_binop_body, func)
                del by_name[name]

    # Look for Numpy ufuncs or gufuncs, and write array-oriented tests for them.
    if "numpy" in sys.modules:
        for name, func in sorted(by_name.items()):
            if _is_probably_ufunc(func):
                make_(_make_ufunc_body, func)
                del by_name[name]

    # For all remaining callables, just write a fuzz-test.  In principle we could
    # guess at equivalence or idempotence; but it doesn't seem accurate enough to
    # be worth the trouble when it's so easy for the user to specify themselves.
    for _, f in sorted(by_name.items()):
        make_(
            _make_test_body, f, test_body=_write_call(f, except_=except_), ghost="fuzz"
        )
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
        func,
        test_body=_write_call(func, except_=except_),
        except_=except_,
        ghost="fuzz",
        style=style,
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

    imports, body = _make_test_body(
        func,
        test_body="result = {}\nrepeat = {}".format(
            _write_call(func, except_=except_),
            _write_call(func, "result", except_=except_),
        ),
        except_=except_,
        assertions=_assert_eq(style, "result", "repeat"),
        ghost="idempotent",
        style=style,
    )
    return _make_test(imports, body)


def _make_roundtrip_body(funcs, except_, style):
    first_param = next(iter(_get_params(funcs[0])))
    test_lines = [
        _write_call(funcs[0], assign="value0", except_=except_),
        *(
            _write_call(f, f"value{i}", assign=f"value{i + 1}", except_=except_)
            for i, f in enumerate(funcs[1:])
        ),
    ]
    return _make_test_body(
        *funcs,
        test_body="\n".join(test_lines),
        except_=except_,
        assertions=_assert_eq(style, first_param, f"value{len(funcs) - 1}"),
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


def _make_equiv_body(funcs, except_, style):
    var_names = [f"result_{f.__name__}" for f in funcs]
    if len(set(var_names)) < len(var_names):
        var_names = [f"result_{i}_{ f.__name__}" for i, f in enumerate(funcs)]
    test_lines = [
        _write_call(f, assign=vname, except_=except_)
        for vname, f in zip(var_names, funcs)
    ]
    assertions = "\n".join(
        _assert_eq(style, var_names[0], vname) for vname in var_names[1:]
    )

    return _make_test_body(
        *funcs,
        test_body="\n".join(test_lines),
        except_=except_,
        assertions=assertions,
        ghost="equivalent",
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
    return _make_test(*_make_equiv_body(funcs, except_, style))


X = TypeVar("X")
Y = TypeVar("Y")


def binary_operation(
    func: Callable[[X, X], Y],
    *,
    associative: bool = True,
    commutative: bool = True,
    identity: Union[X, InferType, None] = infer,
    distributes_over: Optional[Callable[[X, X], X]] = None,
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
    distributes_over: Optional[Callable[[X, X], X]] = None,
    except_: Tuple[Type[Exception], ...],
    style: str,
) -> Tuple[Set[Union[str, Tuple[str, str]]], str]:
    strategies = _get_strategies(func)
    operands, b = (strategies.pop(p) for p in list(_get_params(func))[:2])
    if repr(operands) != repr(b):
        operands |= b
    operands_name = func.__name__ + "_operands"

    all_imports = set()
    parts = []

    def maker(
        sub_property: str,
        args: str,
        body: str,
        right: Optional[str] = None,
    ) -> None:
        if right is None:
            assertions = ""
        else:
            body = f"{body}\n{right}"
            assertions = _assert_eq(style, "left", "right")
        imports, body = _make_test_body(
            func,
            test_body=body,
            ghost=sub_property + "_binary_operation",
            except_=except_,
            assertions=assertions,
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
            _write_call(
                func,
                "a",
                _write_call(func, "b", "c", except_=Exception),
                except_=Exception,
                assign="left",
            ),
            _write_call(
                func,
                _write_call(func, "a", "b", except_=Exception),
                "c",
                except_=Exception,
                assign="right",
            ),
        )
    if commutative:
        maker(
            "commutative",
            "ab",
            _write_call(func, "a", "b", except_=Exception, assign="left"),
            _write_call(func, "b", "a", except_=Exception, assign="right"),
        )
    if identity is not None:
        # Guess that the identity element is the minimal example from our operands
        # strategy.  This is correct often enough to be worthwhile, and close enough
        # that it's a good starting point to edit much of the rest.
        if identity is infer:
            try:
                identity = find(operands, lambda x: True, settings=_quietly_settings)
            except Exception:
                identity = "identity element here"  # type: ignore
        # If the repr of this element is invalid Python, stringify it - this
        # can't be executed as-is, but at least makes it clear what should
        # happen.  E.g. type(None) -> <class 'NoneType'> -> quoted.
        try:
            # We don't actually execute this code object; we're just compiling
            # to check that the repr is syntatically valid.  HOWEVER, we're
            # going to output that code string into test code which will be
            # executed; so you still shouldn't ghostwrite for hostile code.
            compile(repr(identity), "<string>", "exec")
        except SyntaxError:
            identity = repr(identity)  # type: ignore
        maker(
            "identity",
            "a",
            _assert_eq(
                style,
                "a",
                _write_call(func, "a", repr(identity), except_=Exception),
            ),
        )
    if distributes_over:
        maker(
            distributes_over.__name__ + "_distributes_over",
            "abc",
            _write_call(
                distributes_over,
                _write_call(func, "a", "b", except_=Exception),
                _write_call(func, "a", "c", except_=Exception),
                except_=Exception,
                assign="left",
            ),
            _write_call(
                func,
                "a",
                _write_call(distributes_over, "b", "c", except_=Exception),
                except_=Exception,
                assign="right",
            ),
        )

    _, operands_repr = _valid_syntax_repr(operands)
    operands_repr = _st_strategy_names(operands_repr)
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
    """.format(
        array_names=", ".join(ascii_lowercase[: func.nin]),
        call=_write_call(func, *ascii_lowercase[: func.nin], except_=except_),
    )
    assertions = "\n{shape_assert}\n{type_assert}".format(
        shape_assert=_assert_eq(style, "result.shape", "expected_shape"),
        type_assert=_assert_eq(style, "result.dtype.char", "expected_dtype"),
    )

    qname = _get_qualname(func, include_module=True)
    obj_sigs = ["O" in sig for sig in func.types]
    if all(obj_sigs) or not any(obj_sigs):
        types = f"sampled_from({qname}.types)"
    else:
        types = f"sampled_from([sig for sig in {qname}.types if 'O' not in sig])"

    return _make_test_body(
        func,
        test_body=dedent(body).strip(),
        except_=except_,
        assertions=assertions,
        ghost="ufunc" if func.signature is None else "gufunc",
        style=style,
        given_strategies={"data": st.data(), "shapes": shapes, "types": types},
    )
