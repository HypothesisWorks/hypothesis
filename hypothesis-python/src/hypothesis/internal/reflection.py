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

"""This file can approximately be considered the collection of hypothesis going
to really unreasonable lengths to produce pretty output."""

import ast
import hashlib
import inspect
import os
import re
import sys
import types
from functools import wraps
from tokenize import detect_encoding
from types import ModuleType
from typing import Callable, TypeVar

from hypothesis.internal.compat import is_typed_named_tuple, update_code_location
from hypothesis.vendor.pretty import pretty

C = TypeVar("C", bound=Callable)
READTHEDOCS = os.environ.get("READTHEDOCS", None) == "True"


def is_mock(obj):
    """Determine if the given argument is a mock type."""

    # We want to be able to detect these when dealing with various test
    # args. As they are sneaky and can look like almost anything else,
    # we'll check this by looking for an attribute with a name that it's really
    # unlikely to implement accidentally, and that anyone who implements it
    # deliberately should know what they're doing. This is more robust than
    # looking for types.
    return hasattr(obj, "hypothesis_internal_is_this_a_mock_check")


def getfullargspec_except_self(target):
    spec = inspect.getfullargspec(target)
    if inspect.ismethod(target):
        del spec.args[0]
    return spec


def function_digest(function):
    """Returns a string that is stable across multiple invocations across
    multiple processes and is prone to changing significantly in response to
    minor changes to the function.

    No guarantee of uniqueness though it usually will be.
    """
    hasher = hashlib.sha384()
    try:
        hasher.update(inspect.getsource(function).encode())
    except (OSError, TypeError):
        pass
    try:
        hasher.update(function.__name__.encode())
    except AttributeError:
        pass
    try:
        hasher.update(function.__module__.__name__.encode())
    except AttributeError:
        pass
    try:
        hasher.update(repr(getfullargspec_except_self(function)).encode())
    except TypeError:
        pass
    try:
        hasher.update(function._hypothesis_internal_add_digest)
    except AttributeError:
        pass
    return hasher.digest()


def get_signature(target):
    if isinstance(getattr(target, "__signature__", None), inspect.Signature):
        # This special case covers unusual codegen like Pydantic models
        sig = target.__signature__
        # And *this* much more complicated block ignores the `self` argument
        # if that's been (incorrectly) included in the custom signature.
        if sig.parameters and (inspect.isclass(target) or inspect.ismethod(target)):
            selfy = next(iter(sig.parameters.values()))
            if (
                selfy.name == "self"
                and selfy.default is inspect.Parameter.empty
                and selfy.kind.name.startswith("POSITIONAL_")
            ):
                return sig.replace(
                    parameters=[v for k, v in sig.parameters.items() if k != "self"]
                )
        return sig
    if sys.version_info[:2] <= (3, 8) and inspect.isclass(target):
        # Workaround for subclasses of typing.Generic on Python <= 3.8
        from hypothesis.strategies._internal.types import is_generic_type

        if is_generic_type(target):
            sig = inspect.signature(target.__init__)
            return sig.replace(
                parameters=[v for k, v in sig.parameters.items() if k != "self"]
            )
    return inspect.signature(target)


def arg_is_required(param):
    return param.default is inspect.Parameter.empty and param.kind in (
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    )


def required_args(target, args=(), kwargs=()):
    """Return a set of names of required args to target that were not supplied
    in args or kwargs.

    This is used in builds() to determine which arguments to attempt to
    fill from type hints.  target may be any callable (including classes
    and bound methods).  args and kwargs should be as they are passed to
    builds() - that is, a tuple of values and a dict of names: values.
    """
    # We start with a workaround for NamedTuples, which don't have nice inits
    if inspect.isclass(target) and is_typed_named_tuple(target):
        provided = set(kwargs) | set(target._fields[: len(args)])
        return set(target._fields) - provided
    # Then we try to do the right thing with inspect.signature
    try:
        sig = get_signature(target)
    except (ValueError, TypeError):
        return set()
    return {
        name
        for name, param in list(sig.parameters.items())[len(args) :]
        if arg_is_required(param) and name not in kwargs
    }


def convert_keyword_arguments(function, args, kwargs):
    """Returns a pair of a tuple and a dictionary which would be equivalent
    passed as positional and keyword args to the function. Unless function has
    kwonlyargs or **kwargs the dictionary will always be empty.
    """
    argspec = getfullargspec_except_self(function)
    new_args = []
    kwargs = dict(kwargs)

    defaults = dict(argspec.kwonlydefaults or {})

    if argspec.defaults:
        for name, value in zip(
            argspec.args[-len(argspec.defaults) :], argspec.defaults
        ):
            defaults[name] = value

    n = max(len(args), len(argspec.args))

    for i in range(n):
        if i < len(args):
            new_args.append(args[i])
        else:
            arg_name = argspec.args[i]
            if arg_name in kwargs:
                new_args.append(kwargs.pop(arg_name))
            elif arg_name in defaults:
                new_args.append(defaults[arg_name])
            else:
                raise TypeError(f"No value provided for argument {arg_name!r}")

    if kwargs and not (argspec.varkw or argspec.kwonlyargs):
        if len(kwargs) > 1:
            raise TypeError(
                "%s() got unexpected keyword arguments %s"
                % (function.__name__, ", ".join(map(repr, kwargs)))
            )
        else:
            bad_kwarg = next(iter(kwargs))
            raise TypeError(
                f"{function.__name__}() got an unexpected keyword argument {bad_kwarg!r}"
            )
    return tuple(new_args), kwargs


def convert_positional_arguments(function, args, kwargs):
    """Return a tuple (new_args, new_kwargs) where all possible arguments have
    been moved to kwargs.

    new_args will only be non-empty if function has a variadic argument.
    """
    argspec = getfullargspec_except_self(function)
    new_kwargs = dict(argspec.kwonlydefaults or {})
    new_kwargs.update(kwargs)
    if not argspec.varkw:
        for k in new_kwargs.keys():
            if k not in argspec.args and k not in argspec.kwonlyargs:
                raise TypeError(
                    f"{function.__name__}() got an unexpected keyword argument {k!r}"
                )
    if len(args) < len(argspec.args):
        for i in range(len(args), len(argspec.args) - len(argspec.defaults or ())):
            if argspec.args[i] not in kwargs:
                raise TypeError(f"No value provided for argument {argspec.args[i]}")
    for kw in argspec.kwonlyargs:
        if kw not in new_kwargs:
            raise TypeError(f"No value provided for argument {kw}")

    if len(args) > len(argspec.args) and not argspec.varargs:
        raise TypeError(
            f"{function.__name__}() takes at most {len(argspec.args)} "
            f"positional arguments ({len(args)} given)"
        )

    for arg, name in zip(args, argspec.args):
        if name in new_kwargs:
            raise TypeError(
                f"{function.__name__}() got multiple values for keyword argument {name!r}"
            )
        else:
            new_kwargs[name] = arg

    return (tuple(args[len(argspec.args) :]), new_kwargs)


def ast_arguments_matches_signature(args, sig):
    assert isinstance(args, ast.arguments)
    assert isinstance(sig, inspect.Signature)
    expected = []
    for node in getattr(args, "posonlyargs", ()):  # New in Python 3.8
        expected.append((node.arg, inspect.Parameter.POSITIONAL_ONLY))
    for node in args.args:
        expected.append((node.arg, inspect.Parameter.POSITIONAL_OR_KEYWORD))
    if args.vararg is not None:
        expected.append((args.vararg.arg, inspect.Parameter.VAR_POSITIONAL))
    for node in args.kwonlyargs:
        expected.append((node.arg, inspect.Parameter.KEYWORD_ONLY))
    if args.kwarg is not None:
        expected.append((args.kwarg.arg, inspect.Parameter.VAR_KEYWORD))
    return expected == [(p.name, p.kind) for p in sig.parameters.values()]


def extract_all_lambdas(tree, matching_signature):
    lambdas = []

    class Visitor(ast.NodeVisitor):
        def visit_Lambda(self, node):
            if ast_arguments_matches_signature(node.args, matching_signature):
                lambdas.append(node)

    Visitor().visit(tree)

    return lambdas


LINE_CONTINUATION = re.compile(r"\\\n")
WHITESPACE = re.compile(r"\s+")
PROBABLY_A_COMMENT = re.compile("""#[^'"]*$""")
SPACE_FOLLOWS_OPEN_BRACKET = re.compile(r"\( ")
SPACE_PRECEDES_CLOSE_BRACKET = re.compile(r" \)")


def extract_lambda_source(f):
    """Extracts a single lambda expression from the string source. Returns a
    string indicating an unknown body if it gets confused in any way.

    This is not a good function and I am sorry for it. Forgive me my
    sins, oh lord
    """
    sig = inspect.signature(f)
    assert sig.return_annotation is inspect.Parameter.empty
    if sig.parameters:
        if_confused = f"lambda {str(sig)[1:-1]}: <unknown>"
    else:
        if_confused = "lambda: <unknown>"
    try:
        source = inspect.getsource(f)
    except OSError:
        return if_confused

    source = LINE_CONTINUATION.sub(" ", source)
    source = WHITESPACE.sub(" ", source)
    source = source.strip()
    assert "lambda" in source

    tree = None

    try:
        tree = ast.parse(source)
    except SyntaxError:
        for i in range(len(source) - 1, len("lambda"), -1):
            prefix = source[:i]
            if "lambda" not in prefix:
                break
            try:
                tree = ast.parse(prefix)
                source = prefix
                break
            except SyntaxError:
                continue
    if tree is None and source.startswith("@"):
        # This will always eventually find a valid expression because
        # the decorator must be a valid Python function call, so will
        # eventually be syntactically valid and break out of the loop.
        # Thus, this loop can never terminate normally.
        for i in range(len(source) + 1):
            p = source[1:i]
            if "lambda" in p:
                try:
                    tree = ast.parse(p)
                    source = p
                    break
                except SyntaxError:
                    pass
        else:
            raise NotImplementedError("expected to be unreachable")

    if tree is None:
        return if_confused

    aligned_lambdas = extract_all_lambdas(tree, matching_signature=sig)
    if len(aligned_lambdas) != 1:
        return if_confused
    lambda_ast = aligned_lambdas[0]
    assert lambda_ast.lineno == 1

    # If the source code contains Unicode characters, the bytes of the original
    # file don't line up with the string indexes, and `col_offset` doesn't match
    # the string we're using.  We need to convert the source code into bytes
    # before slicing.
    #
    # Under the hood, the inspect module is using `tokenize.detect_encoding` to
    # detect the encoding of the original source file.  We'll use the same
    # approach to get the source code as bytes.
    #
    # See https://github.com/HypothesisWorks/hypothesis/issues/1700 for an
    # example of what happens if you don't correct for this.
    #
    # Note: if the code doesn't come from a file (but, for example, a doctest),
    # `getsourcefile` will return `None` and the `open()` call will fail with
    # an OSError.  Or if `f` is a built-in function, in which case we get a
    # TypeError.  In both cases, fall back to splitting the Unicode string.
    # It's not perfect, but it's the best we can do.
    try:
        with open(inspect.getsourcefile(f), "rb") as src_f:
            encoding, _ = detect_encoding(src_f.readline)

        source_bytes = source.encode(encoding)
        source_bytes = source_bytes[lambda_ast.col_offset :].strip()
        source = source_bytes.decode(encoding)
    except (OSError, TypeError):
        source = source[lambda_ast.col_offset :].strip()

    # This ValueError can be thrown in Python 3 if:
    #
    #  - There's a Unicode character in the line before the Lambda, and
    #  - For some reason we can't detect the source encoding of the file
    #
    # because slicing on `lambda_ast.col_offset` will account for bytes, but
    # the slice will be on Unicode characters.
    #
    # In practice this seems relatively rare, so we just give up rather than
    # trying to recover.
    try:
        source = source[source.index("lambda") :]
    except ValueError:
        return if_confused

    for i in range(len(source), len("lambda"), -1):  # pragma: no branch
        try:
            parsed = ast.parse(source[:i])
            assert len(parsed.body) == 1
            assert parsed.body
            if isinstance(parsed.body[0].value, ast.Lambda):
                source = source[:i]
                break
        except SyntaxError:
            pass
    lines = source.split("\n")
    lines = [PROBABLY_A_COMMENT.sub("", l) for l in lines]
    source = "\n".join(lines)

    source = WHITESPACE.sub(" ", source)
    source = SPACE_FOLLOWS_OPEN_BRACKET.sub("(", source)
    source = SPACE_PRECEDES_CLOSE_BRACKET.sub(")", source)
    source = source.strip()
    return source


def get_pretty_function_description(f):
    if not hasattr(f, "__name__"):
        return repr(f)
    name = f.__name__
    if name == "<lambda>":
        return extract_lambda_source(f)
    elif isinstance(f, (types.MethodType, types.BuiltinMethodType)):
        self = f.__self__
        # Some objects, like `builtins.abs` are of BuiltinMethodType but have
        # their module as __self__.  This might include c-extensions generally?
        if not (self is None or inspect.isclass(self) or inspect.ismodule(self)):
            return f"{self!r}.{name}"
    elif isinstance(name, str) and getattr(dict, name, object()) is f:
        # special case for keys/values views in from_type() / ghostwriter output
        return f"dict.{name}"
    return name


def nicerepr(v):
    if inspect.isfunction(v):
        return get_pretty_function_description(v)
    elif isinstance(v, type):
        return v.__name__
    else:
        # With TypeVar T, show List[T] instead of TypeError on List[~T]
        return re.sub(r"(\[)~([A-Z][a-z]*\])", r"\g<1>\g<2>", pretty(v))


def arg_string(f, args, kwargs, reorder=True):
    if reorder:
        args, kwargs = convert_positional_arguments(f, args, kwargs)

    bits = [nicerepr(x) for x in args]

    for p in get_signature(f).parameters.values():
        if p.name in kwargs and not p.kind.name.startswith("VAR_"):
            bits.append(f"{p.name}={nicerepr(kwargs.pop(p.name))}")
    if kwargs:
        for a in sorted(kwargs):
            bits.append(f"{a}={nicerepr(kwargs[a])}")

    return ", ".join(bits)


def check_valid_identifier(identifier):
    if not identifier.isidentifier():
        raise ValueError(f"{identifier!r} is not a valid python identifier")


eval_cache: dict = {}


def source_exec_as_module(source):
    try:
        return eval_cache[source]
    except KeyError:
        pass

    hexdigest = hashlib.sha384(source.encode()).hexdigest()
    result = ModuleType("hypothesis_temporary_module_" + hexdigest)
    assert isinstance(source, str)
    exec(source, result.__dict__)
    eval_cache[source] = result
    return result


COPY_ARGSPEC_SCRIPT = """
from hypothesis.utils.conventions import not_set

def accept({funcname}):
    def {name}({argspec}):
        return {funcname}({invocation})
    return {name}
""".lstrip()


def define_function_signature(name, docstring, argspec):
    """A decorator which sets the name, argspec and docstring of the function
    passed into it."""
    check_valid_identifier(name)
    for a in argspec.args:
        check_valid_identifier(a)
    if argspec.varargs is not None:
        check_valid_identifier(argspec.varargs)
    if argspec.varkw is not None:
        check_valid_identifier(argspec.varkw)
    n_defaults = len(argspec.defaults or ())
    if n_defaults:
        parts = []
        for a in argspec.args[:-n_defaults]:
            parts.append(a)
        for a in argspec.args[-n_defaults:]:
            parts.append(f"{a}=not_set")
    else:
        parts = list(argspec.args)
    used_names = list(argspec.args) + list(argspec.kwonlyargs)
    used_names.append(name)

    for a in argspec.kwonlyargs:
        check_valid_identifier(a)

    def accept(f):
        fargspec = getfullargspec_except_self(f)
        must_pass_as_kwargs = []
        invocation_parts = []
        for a in argspec.args:
            if a not in fargspec.args and not fargspec.varargs:
                must_pass_as_kwargs.append(a)
            else:
                invocation_parts.append(a)
        if argspec.varargs:
            used_names.append(argspec.varargs)
            parts.append("*" + argspec.varargs)
            invocation_parts.append("*" + argspec.varargs)
        elif argspec.kwonlyargs:
            parts.append("*")
        for k in must_pass_as_kwargs:
            invocation_parts.append(f"{k}={k}")

        for k in argspec.kwonlyargs:
            invocation_parts.append(f"{k}={k}")
            if k in (argspec.kwonlydefaults or []):
                parts.append(f"{k}=not_set")
            else:
                parts.append(k)
        if argspec.varkw:
            used_names.append(argspec.varkw)
            parts.append("**" + argspec.varkw)
            invocation_parts.append("**" + argspec.varkw)

        candidate_names = ["f"] + [f"f_{i}" for i in range(1, len(used_names) + 2)]

        for funcname in candidate_names:  # pragma: no branch
            if funcname not in used_names:
                break

        source = COPY_ARGSPEC_SCRIPT.format(
            name=name,
            funcname=funcname,
            argspec=", ".join(parts),
            invocation=", ".join(invocation_parts),
        )
        result = source_exec_as_module(source).accept(f)
        result.__doc__ = docstring
        result.__defaults__ = argspec.defaults
        if argspec.kwonlydefaults:
            result.__kwdefaults__ = argspec.kwonlydefaults
        if argspec.annotations:
            result.__annotations__ = argspec.annotations
        return result

    return accept


def impersonate(target):
    """Decorator to update the attributes of a function so that to external
    introspectors it will appear to be the target function.

    Note that this updates the function in place, it doesn't return a
    new one.
    """

    def accept(f):
        f.__code__ = update_code_location(
            f.__code__, target.__code__.co_filename, target.__code__.co_firstlineno
        )
        f.__name__ = target.__name__
        f.__module__ = target.__module__
        f.__doc__ = target.__doc__
        f.__globals__["__hypothesistracebackhide__"] = True
        return f

    return accept


def proxies(target):
    replace_sig = define_function_signature(
        target.__name__.replace("<lambda>", "_lambda_"),
        target.__doc__,
        getfullargspec_except_self(target),
    )

    def accept(proxy):
        return impersonate(target)(wraps(target)(replace_sig(proxy)))

    return accept


def is_identity_function(f):
    # TODO: pattern-match the AST to handle `def ...` identity functions too
    return bool(re.fullmatch(r"lambda (\w+): \1", get_pretty_function_description(f)))
