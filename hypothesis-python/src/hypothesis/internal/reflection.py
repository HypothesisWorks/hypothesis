# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""This file can approximately be considered the collection of hypothesis going
to really unreasonable lengths to produce pretty output."""

import ast
import hashlib
import inspect
import linecache
import re
import sys
import textwrap
import types
import warnings
from collections.abc import MutableMapping, Sequence
from functools import partial, wraps
from inspect import Parameter, Signature
from io import StringIO
from keyword import iskeyword
from random import _inst as global_random_instance
from tokenize import COMMENT, generate_tokens, untokenize
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable, Optional, TypeVar, Union
from unittest.mock import _patch as PatchType
from weakref import WeakKeyDictionary

from hypothesis.errors import HypothesisWarning
from hypothesis.internal.cache import LRUCache
from hypothesis.internal.compat import EllipsisType, is_typed_named_tuple
from hypothesis.utils.conventions import not_set
from hypothesis.vendor.pretty import pretty

if TYPE_CHECKING:
    from hypothesis.strategies._internal.strategies import SearchStrategy

T = TypeVar("T")

# we have several levels of caching for lambda descriptions.
# * LAMBDA_DESCRIPTION_CACHE maps a lambda f to its description _lambda_description(f).
#   Note that _lambda_description(f) may not be identical to f as it appears in the
#   source code file.
# * LAMBDA_DIGEST_DESCRIPTION_CACHE maps _function_key(f) to _lambda_description(f).
#   _function_key implements something close to "ast equality":
#   two syntactically identical (minus whitespace etc) lambdas appearing in
#   different files have the same key. Cache hits here provide a fast path which
#   avoids ast-parsing syntactic lambdas we've seen before. Two lambdas with the
#   same _function_key will not have different _lambda_descriptions - if
#   they do, that's a bug here.
# * AST_LAMBDAS_CACHE maps source code lines to a list of the lambdas found in
#   that source code. A cache hit here avoids reparsing the ast.
LAMBDA_DESCRIPTION_CACHE: MutableMapping[Callable, str] = WeakKeyDictionary()
LAMBDA_DIGEST_DESCRIPTION_CACHE: LRUCache[tuple[Any], str] = LRUCache(max_size=1000)
AST_LAMBDAS_CACHE: LRUCache[tuple[str], list[ast.Lambda]] = LRUCache(max_size=100)


def is_mock(obj: object) -> bool:
    """Determine if the given argument is a mock type."""

    # We want to be able to detect these when dealing with various test
    # args. As they are sneaky and can look like almost anything else,
    # we'll check this by looking for an attribute with a name that it's really
    # unlikely to implement accidentally, and that anyone who implements it
    # deliberately should know what they're doing. This is more robust than
    # looking for types.
    return hasattr(obj, "hypothesis_internal_is_this_a_mock_check")


def _clean_source(src: str) -> bytes:
    """Return the source code as bytes, without decorators or comments.

    Because this is part of our database key, we reduce the cache invalidation
    rate by ignoring decorators, comments, trailing whitespace, and empty lines.
    We can't just use the (dumped) AST directly because it changes between Python
    versions (e.g. ast.Constant)
    """
    # Get the (one-indexed) line number of the function definition, and drop preceding
    # lines - i.e. any decorators, so that adding `@example()`s keeps the same key.
    try:
        funcdef = ast.parse(src).body[0]
        src = "".join(src.splitlines(keepends=True)[funcdef.lineno - 1 :])
    except Exception:
        pass
    # Remove blank lines and use the tokenize module to strip out comments,
    # so that those can be changed without changing the database key.
    try:
        src = untokenize(
            t for t in generate_tokens(StringIO(src).readline) if t.type != COMMENT
        )
    except Exception:
        pass
    # Finally, remove any trailing whitespace and empty lines as a last cleanup.
    return "\n".join(x.rstrip() for x in src.splitlines() if x.rstrip()).encode()


def function_digest(function: Any) -> bytes:
    """Returns a string that is stable across multiple invocations across
    multiple processes and is prone to changing significantly in response to
    minor changes to the function.

    No guarantee of uniqueness though it usually will be. Digest collisions
    lead to unfortunate but not fatal problems during database replay.
    """
    hasher = hashlib.sha384()
    try:
        src = inspect.getsource(function)
    except (OSError, TypeError):
        # If we can't actually get the source code, try for the name as a fallback.
        # NOTE: We might want to change this to always adding function.__qualname__,
        # to differentiate f.x. two classes having the same function implementation
        # with class-dependent behaviour.
        try:
            hasher.update(function.__name__.encode())
        except AttributeError:
            pass
    else:
        hasher.update(_clean_source(src))
    try:
        # This is additional to the source code because it can include the effects
        # of decorators, or of post-hoc assignment to the .__signature__ attribute.
        hasher.update(repr(get_signature(function)).encode())
    except Exception:
        pass
    try:
        # We set this in order to distinguish e.g. @pytest.mark.parametrize cases.
        hasher.update(function._hypothesis_internal_add_digest)
    except AttributeError:
        pass
    return hasher.digest()


def check_signature(sig: Signature) -> None:
    # Backport from Python 3.11; see https://github.com/python/cpython/pull/92065
    for p in sig.parameters.values():
        if iskeyword(p.name) and p.kind is not p.POSITIONAL_ONLY:
            raise ValueError(
                f"Signature {sig!r} contains a parameter named {p.name!r}, "
                f"but this is a SyntaxError because `{p.name}` is a keyword. "
                "You, or a library you use, must have manually created an "
                "invalid signature - this will be an error in Python 3.11+"
            )


def get_signature(
    target: Any, *, follow_wrapped: bool = True, eval_str: bool = False
) -> Signature:
    # Special case for use of `@unittest.mock.patch` decorator, mimicking the
    # behaviour of getfullargspec instead of reporting unusable arguments.
    patches = getattr(target, "patchings", None)
    if isinstance(patches, list) and all(isinstance(p, PatchType) for p in patches):
        return Signature(
            [
                Parameter("args", Parameter.VAR_POSITIONAL),
                Parameter("keywargs", Parameter.VAR_KEYWORD),
            ]
        )

    if isinstance(getattr(target, "__signature__", None), Signature):
        # This special case covers unusual codegen like Pydantic models
        sig = target.__signature__
        check_signature(sig)
        # And *this* much more complicated block ignores the `self` argument
        # if that's been (incorrectly) included in the custom signature.
        if sig.parameters and (inspect.isclass(target) or inspect.ismethod(target)):
            selfy = next(iter(sig.parameters.values()))
            if (
                selfy.name == "self"
                and selfy.default is Parameter.empty
                and selfy.kind.name.startswith("POSITIONAL_")
            ):
                return sig.replace(
                    parameters=[v for k, v in sig.parameters.items() if k != "self"]
                )
        return sig
    # eval_str is only supported by Python 3.10 and newer
    if sys.version_info[:2] >= (3, 10):
        sig = inspect.signature(
            target, follow_wrapped=follow_wrapped, eval_str=eval_str
        )
    else:
        sig = inspect.signature(
            target, follow_wrapped=follow_wrapped
        )  # pragma: no cover
    check_signature(sig)
    return sig


def arg_is_required(param: Parameter) -> bool:
    return param.default is Parameter.empty and param.kind in (
        Parameter.POSITIONAL_OR_KEYWORD,
        Parameter.KEYWORD_ONLY,
    )


def required_args(
    target: Callable[..., Any],
    args: tuple["SearchStrategy[Any]", ...] = (),
    kwargs: Optional[dict[str, Union["SearchStrategy[Any]", EllipsisType]]] = None,
) -> set[str]:
    """Return a set of names of required args to target that were not supplied
    in args or kwargs.

    This is used in builds() to determine which arguments to attempt to
    fill from type hints.  target may be any callable (including classes
    and bound methods).  args and kwargs should be as they are passed to
    builds() - that is, a tuple of values and a dict of names: values.
    """
    kwargs = {} if kwargs is None else kwargs
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


def convert_keyword_arguments(
    function: Any, args: Sequence[object], kwargs: dict[str, object]
) -> tuple[tuple[object, ...], dict[str, object]]:
    """Returns a pair of a tuple and a dictionary which would be equivalent
    passed as positional and keyword args to the function. Unless function has
    kwonlyargs or **kwargs the dictionary will always be empty.
    """
    sig = inspect.signature(function, follow_wrapped=False)
    bound = sig.bind(*args, **kwargs)
    return bound.args, bound.kwargs


def convert_positional_arguments(
    function: Any, args: Sequence[object], kwargs: dict[str, object]
) -> tuple[tuple[object, ...], dict[str, object]]:
    """Return a tuple (new_args, new_kwargs) where all possible arguments have
    been moved to kwargs.

    new_args will only be non-empty if function has pos-only args or *args.
    """
    sig = inspect.signature(function, follow_wrapped=False)
    bound = sig.bind(*args, **kwargs)
    new_args = []
    new_kwargs = dict(bound.arguments)
    for p in sig.parameters.values():
        if p.name in new_kwargs:
            if p.kind is p.POSITIONAL_ONLY:
                new_args.append(new_kwargs.pop(p.name))
            elif p.kind is p.VAR_POSITIONAL:
                new_args.extend(new_kwargs.pop(p.name))
            elif p.kind is p.VAR_KEYWORD:
                assert set(new_kwargs[p.name]).isdisjoint(set(new_kwargs) - {p.name})
                new_kwargs.update(new_kwargs.pop(p.name))
    return tuple(new_args), new_kwargs


def ast_arguments_matches_signature(args: ast.arguments, sig: Signature) -> bool:
    expected: list[tuple[str, int]] = []
    for node in args.posonlyargs:
        expected.append((node.arg, Parameter.POSITIONAL_ONLY))
    for node in args.args:
        expected.append((node.arg, Parameter.POSITIONAL_OR_KEYWORD))
    if args.vararg is not None:
        expected.append((args.vararg.arg, Parameter.VAR_POSITIONAL))
    for node in args.kwonlyargs:
        expected.append((node.arg, Parameter.KEYWORD_ONLY))
    if args.kwarg is not None:
        expected.append((args.kwarg.arg, Parameter.VAR_KEYWORD))
    return expected == [(p.name, p.kind) for p in sig.parameters.values()]


def is_first_param_referenced_in_function(f: Any) -> bool:
    """Is the given name referenced within f?"""
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(f)))
    except Exception:
        return True  # Assume it's OK unless we know otherwise
    name = next(iter(get_signature(f).parameters))
    return any(
        isinstance(node, ast.Name)
        and node.id == name
        and isinstance(node.ctx, ast.Load)
        for node in ast.walk(tree)
    )


def extract_all_lambdas(tree, *, extract_nested=True):
    lambdas = []

    class Visitor(ast.NodeVisitor):

        def visit_Lambda(self, node):
            lambdas.append(node)
            if extract_nested:  # pragma: no branch
                self.visit(node.body)

    Visitor().visit(tree)
    return lambdas


def extract_all_attributes(tree, *, extract_nested=True):
    attributes = []

    class Visitor(ast.NodeVisitor):
        def visit_Attribute(self, node):
            attributes.append(node)
            if extract_nested:  # pragma: no branch
                self.visit(node.value)

    Visitor().visit(tree)
    return attributes


def _normalize_code(f, l):
    # Opcodes, from dis.opmap (as of 3.13)
    NOP = 9
    LOAD_FAST = 85
    LOAD_FAST_LOAD_FAST = 88
    LOAD_FAST_BORROW = 86
    LOAD_FAST_BORROW_LOAD_FAST_BORROW = 87

    # A small selection of possible keyhole code transformations, based on what
    # is actually seen to differ between compilations in our test suite. Each
    # entry contains two equivalent opcode sequences, plus an optional check
    # function called with their respective oparg sequences.
    Checker = Callable[[list[int], list[int]], bool]
    transforms: tuple[list[int], list[int], Optional[Checker]] = [
        ([NOP], [], None),
        (
            [LOAD_FAST, LOAD_FAST],
            [LOAD_FAST_LOAD_FAST],
            lambda a, b: a == [b[0] >> 4, b[0] & 15],
        ),
        (
            [LOAD_FAST_BORROW, LOAD_FAST_BORROW],
            [LOAD_FAST_BORROW_LOAD_FAST_BORROW],
            lambda a, b: a == [b[0] >> 4, b[0] & 15],
        ),
    ]
    # augment with inverse
    transforms += [
        (ops_b, ops_a, checker and (lambda a, b, checker=checker: checker(b, a)))
        for ops_a, ops_b, checker in transforms
    ]

    # Normalize equivalent code. We assume that each bytecode op is 2 bytes,
    # which is the case since Python 3.6. Since the opcodes values may change
    # between version, there is a risk that a transform may not be equivalent
    # -- even so, the risk of a bad transform producing a false positive is
    # minuscule.
    co_code = list(l.__code__.co_code)
    f_code = list(f.__code__.co_code)

    def alternating(code, i, n):
        return code[i : i + 2 * n : 2]

    i = 2
    while i < max(len(co_code), len(f_code)):
        # note that co_code is mutated in loop
        if i < min(len(co_code), len(f_code)) and f_code[i] == co_code[i]:
            i += 2
        else:
            for op1, op2, checker in transforms:
                if (
                    op1 == alternating(f_code, i, len(op1))
                    and op2 == alternating(co_code, i, len(op2))
                    and (
                        checker is None
                        or checker(
                            alternating(f_code, i + 1, len(op1)),
                            alternating(co_code, i + 1, len(op2)),
                        )
                    )
                ):
                    break
            else:
                # no point in continuing since the bytecodes are different anyway
                break
            # Splice in the transform and continue
            co_code = (
                co_code[:i] + f_code[i : i + 2 * len(op1)] + co_code[i + 2 * len(op2) :]
            )
            i += 2 * len(op1)

    # Normalize consts, in particular replace any lambda consts with the
    # corresponding const from the template function, IFF they have the same
    # source key.

    f_consts = f.__code__.co_consts
    l_consts = l.__code__.co_consts
    if len(f_consts) == len(l_consts) and any(
        inspect.iscode(l_const) for l_const in l_consts
    ):
        normalized_consts = []
        for f_const, l_const in zip(f_consts, l_consts):
            if (
                inspect.iscode(l_const)
                and inspect.iscode(f_const)
                and _function_key(f_const) == _function_key(l_const)
            ):
                # If the lambdas are compiled from the same source, make them be the
                # same object so that the toplevel lambdas end up equal. Note that if
                # the default arguments differ in this case then the bytecode must
                # also differ, since the default arguments are set up by the bytecode.
                # I.e., this appears to be safe wrt false positives.
                normalized_consts.append(f_const)
            else:
                normalized_consts.append(l_const)
    else:
        normalized_consts = l_consts

    return l.__code__.replace(
        co_code=bytes(co_code),
        co_consts=tuple(normalized_consts),
    )


def _function_key(f, *, bounded_size=False):
    """Returns a digest that differentiates functions that have different sources.

    Either a function or a code object may be passed. If code object, default
    arg/kwarg values are not recoverable - this is the best we can do, and is
    sufficient for the use case of comparing nested lambdas.
    """
    try:
        code = f.__code__
        defaults_repr = repr((f.__defaults__, f.__kwdefaults__))
    except AttributeError:
        code = f
        defaults_repr = ()
    consts_repr = repr(code.co_consts)
    if bounded_size:
        # Compress repr to avoid keeping arbitrarily large strings pinned as cache
        # keys. We don't do this unconditionally because hashing takes time, and is
        # not necessary if the key is used just for comparison (and is not stored).
        if len(consts_repr) > 48:
            consts_repr = hashlib.sha384(consts_repr.encode()).digest()
        if len(defaults_repr) > 48:
            defaults_repr = hashlib.sha384(consts_repr.encode()).digest()
    return (
        consts_repr,
        defaults_repr,
        code.co_argcount,
        code.co_kwonlyargcount,
        code.co_code,
        code.co_names,
        code.co_varnames,
        code.co_freevars,
        code.co_name,
    )


_module_map: dict[int, str] = {}


def _mimic_lambda_from_node(f, node):
    # Compile the source (represented by an ast.Lambda node) in a context that
    # as far as possible mimics the context that f was compiled in. If - and
    # only if - this was the source of f then the result is indistinguishable
    # from f itself (to a casual observer such as _function_key).
    f_globals = f.__globals__.copy()
    f_code = f.__code__
    source = ast.unparse(node)

    # Install values for non-literal argument defaults. Thankfully, these are
    # always captured by value - so there is no interaction with the closure.
    if f.__defaults__:
        for f_default, l_default in zip(f.__defaults__, node.args.defaults):
            if isinstance(l_default, ast.Name):
                f_globals[l_default.id] = f_default
    if f.__kwdefaults__:
        for l_default, l_varname in zip(node.args.kw_defaults, node.args.kwonlyargs):
            if isinstance(l_default, ast.Name):  # pragma: no cover # shouldn't be?
                f_globals[l_default.id] = f.__kwdefaults__[l_varname.arg]

    # CPython's compiler treats known imports differently than normal globals,
    # so check if we use attributes from globals that are modules (if so, we
    # import them explicitly and redundantly in the exec below)
    referenced_modules = [
        (local_name, module)
        for attr in extract_all_attributes(node)
        if (
            isinstance(attr.value, ast.Name)
            and (local_name := attr.value.id)
            and inspect.ismodule(module := f_globals.get(local_name))
        )
    ]

    if not f_code.co_freevars and not referenced_modules:
        compiled = eval(source, f_globals)
    else:
        if f_code.co_freevars:
            # We have to reconstruct a local closure. The closure will have
            # the same values as the original function, although this is not
            # required for source/bytecode equality.
            f_globals |= {
                f"__lc{i}": c.cell_contents for i, c in enumerate(f.__closure__)
            }
            captures = [f"{name}=__lc{i}" for i, name in enumerate(f_code.co_freevars)]
            capture_str = ";".join(captures) + ";"
        else:
            capture_str = ""
        if referenced_modules:
            # We add import statements for all referenced modules, since that
            # influences the compiled code. The assumption is that these modules
            # were explicitly imported, not assigned, in the source - if not,
            # this may/will give a different compilation result.
            global _module_map
            if len(_module_map) != len(sys.modules):  # pragma: no branch
                _module_map = {id(module): name for name, module in sys.modules.items()}
            imports = [
                (module_name, local_name)
                for local_name, module in referenced_modules
                if (module_name := _module_map.get(id(module))) is not None
            ]
            import_fragments = [f"{name} as {asname}" for name, asname in set(imports)]
            import_str = f"import {','.join(import_fragments)}\n"
        else:
            import_str = ""
        exec_str = (
            f"{import_str}def __construct_lambda(): {capture_str} return ({source})"
        )
        exec(exec_str, f_globals)
        compiled = f_globals["__construct_lambda"]()

    return compiled


def _lambda_code_matches_node(f, node):
    try:
        compiled = _mimic_lambda_from_node(f, node)
    except (NameError, SyntaxError):  # pragma: no cover
        return False
    if _function_key(f) == _function_key(compiled):
        return True
    # Try harder
    compiled.__code__ = _normalize_code(f, compiled)
    return _function_key(f) == _function_key(compiled)


def _lambda_description(f, leeway=10, *, fail_if_confused_with_perfect_candidate=False):
    if hasattr(f, "__wrapped_target"):
        f = f.__wrapped_target

    # You might be wondering how a lambda can have a return-type annotation?
    # The answer is that we add this at runtime, in new_given_signature(),
    # and we do support strange choices as applying @given() to a lambda.
    sig = inspect.signature(f)
    assert sig.return_annotation in (Parameter.empty, None), sig

    # Using pytest-xdist on Python 3.13, there's an entry in the linecache for
    # file "<string>", which then returns nonsense to getsource.  Discard it.
    linecache.cache.pop("<string>", None)

    def format_lambda(body):
        # The signature is more informative than the corresponding ast.unparse
        # output in the case of default argument values, so add the signature
        # to the unparsed body
        return (
            f"lambda {str(sig)[1:-1]}: {body}" if sig.parameters else f"lambda: {body}"
        )

    if_confused = format_lambda("<unknown>")

    try:
        source_lines, lineno0 = inspect.findsource(f)
        source_lines = tuple(source_lines)  # make it hashable
    except OSError:
        return if_confused

    try:
        all_lambdas = AST_LAMBDAS_CACHE[source_lines]
    except KeyError:
        # The source isn't already parsed, so we try to shortcut by parsing just
        # the local block. If that fails to produce a code-identical lambda,
        # fall through to the full parse.
        local_lines = inspect.getblock(source_lines[lineno0:])
        local_block = textwrap.dedent("".join(local_lines))
        if local_block.startswith("."):
            # The fairly common ".map(lambda x: ...)" case. This partial block
            # isn't valid syntax, but it might be if we remove the leading ".".
            local_block = local_block[1:]

        try:
            local_tree = ast.parse(local_block)
        except SyntaxError:
            pass
        else:
            local_lambdas = extract_all_lambdas(local_tree)
            for candidate in local_lambdas:
                if ast_arguments_matches_signature(
                    candidate.args, sig
                ) and _lambda_code_matches_node(f, candidate):
                    return format_lambda(ast.unparse(candidate.body))

        # Local parse failed or didn't produce a match, go ahead with the full parse
        try:
            tree = ast.parse("".join(source_lines))
        except SyntaxError:  # pragma: no cover
            all_lambdas = []
        else:
            all_lambdas = extract_all_lambdas(tree)
        AST_LAMBDAS_CACHE[source_lines] = all_lambdas

    aligned_lambdas = []
    for candidate in all_lambdas:
        if (
            candidate.lineno - leeway <= lineno0 + 1 <= candidate.lineno + leeway
            and ast_arguments_matches_signature(candidate.args, sig)
        ):
            aligned_lambdas.append(candidate)

    aligned_lambdas.sort(key=lambda c: abs(lineno0 + 1 - c.lineno))
    for candidate in aligned_lambdas:
        if _lambda_code_matches_node(f, candidate):
            return format_lambda(ast.unparse(candidate.body))

    # None of the aligned lambdas match perfectly in generated code.
    if (
        fail_if_confused_with_perfect_candidate
        and aligned_lambdas
        and aligned_lambdas[0].lineno == lineno0 + 1
    ):  # pragma: no cover
        # This arg is forced on in conftest.py, to ensure we resolve all known
        # cases.
        raise ValueError("None of the source-file lambda candidates were matched")
    return if_confused


def lambda_description(f):
    """
    Returns a syntactically-valid expression describing `f`. This is often, but
    not always, the exact lambda definition string which appears in the source code.
    The difference comes from parsing the lambda ast into `tree` and then returning
    the result of `ast.unparse(tree)`, which may differ in whitespace, double vs
    single quotes, etc.

    Returns a string indicating an unknown body if the parsing gets confused in any way.
    """
    try:
        return LAMBDA_DESCRIPTION_CACHE[f]
    except KeyError:
        pass

    key = _function_key(f, bounded_size=True)
    failed_fnames = []
    try:
        description, failed_fnames = LAMBDA_DIGEST_DESCRIPTION_CACHE[key]
        if (
            "<unknown>" not in description and f.__code__.co_filename in failed_fnames
        ):  # pragma: no cover
            # Only accept the <unknown> description if it comes from parsing this
            # file - otherwise, try again below, maybe we have more luck in another
            # file. Once lucky, we keep keep using the successful description for *new*
            # lambdas but not for this one - so it doesn't change name during its
            # lifetime.
            LAMBDA_DESCRIPTION_CACHE[f] = description
            return description
    except KeyError:
        failed_fnames = []

    description = _lambda_description(f)
    LAMBDA_DESCRIPTION_CACHE[f] = description
    if "<unknown>" in description:
        failed_fnames.append(f.__code__.co_filename)
    LAMBDA_DIGEST_DESCRIPTION_CACHE[key] = description, failed_fnames
    return description


def get_pretty_function_description(f: object) -> str:
    if isinstance(f, partial):
        return pretty(f)
    if not hasattr(f, "__name__"):
        return repr(f)
    name = f.__name__  # type: ignore
    if name == "<lambda>":
        return lambda_description(f)
    elif isinstance(f, (types.MethodType, types.BuiltinMethodType)):
        self = f.__self__
        # Some objects, like `builtins.abs` are of BuiltinMethodType but have
        # their module as __self__.  This might include c-extensions generally?
        if not (self is None or inspect.isclass(self) or inspect.ismodule(self)):
            if self is global_random_instance:
                return f"random.{name}"
            return f"{self!r}.{name}"
    elif isinstance(name, str) and getattr(dict, name, object()) is f:
        # special case for keys/values views in from_type() / ghostwriter output
        return f"dict.{name}"
    return name


def nicerepr(v: Any) -> str:
    if inspect.isfunction(v):
        return get_pretty_function_description(v)
    elif isinstance(v, type):
        return v.__name__
    else:
        # With TypeVar T, show List[T] instead of TypeError on List[~T]
        return re.sub(r"(\[)~([A-Z][a-z]*\])", r"\g<1>\g<2>", pretty(v))


def repr_call(
    f: Any, args: Sequence[object], kwargs: dict[str, object], *, reorder: bool = True
) -> str:
    # Note: for multi-line pretty-printing, see RepresentationPrinter.repr_call()
    if reorder:
        args, kwargs = convert_positional_arguments(f, args, kwargs)

    bits = [nicerepr(x) for x in args]

    for p in get_signature(f).parameters.values():
        if p.name in kwargs and not p.kind.name.startswith("VAR_"):
            bits.append(f"{p.name}={nicerepr(kwargs.pop(p.name))}")
    if kwargs:
        for a in sorted(kwargs):
            bits.append(f"{a}={nicerepr(kwargs[a])}")

    rep = nicerepr(f)
    if rep.startswith("lambda") and ":" in rep:
        rep = f"({rep})"
    repr_len = len(rep) + sum(len(b) for b in bits)  # approx
    if repr_len > 30000:
        warnings.warn(
            "Generating overly large repr. This is an expensive operation, and with "
            f"a length of {repr_len//1000} kB is unlikely to be useful. Use -Wignore "
            "to ignore the warning, or -Werror to get a traceback.",
            HypothesisWarning,
            stacklevel=2,
        )
    return rep + "(" + ", ".join(bits) + ")"


def check_valid_identifier(identifier: str) -> None:
    if not identifier.isidentifier():
        raise ValueError(f"{identifier!r} is not a valid python identifier")


eval_cache: dict[str, ModuleType] = {}


def source_exec_as_module(source: str) -> ModuleType:
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


COPY_SIGNATURE_SCRIPT = """
from hypothesis.utils.conventions import not_set

def accept({funcname}):
    def {name}{signature}:
        return {funcname}({invocation})
    return {name}
""".lstrip()


def get_varargs(
    sig: Signature, kind: int = Parameter.VAR_POSITIONAL
) -> Optional[Parameter]:
    for p in sig.parameters.values():
        if p.kind is kind:
            return p
    return None


def define_function_signature(name, docstring, signature):
    """A decorator which sets the name, signature and docstring of the function
    passed into it."""
    if name == "<lambda>":
        name = "_lambda_"
    check_valid_identifier(name)
    for a in signature.parameters:
        check_valid_identifier(a)

    used_names = {*signature.parameters, name}

    newsig = signature.replace(
        parameters=[
            p if p.default is signature.empty else p.replace(default=not_set)
            for p in (
                p.replace(annotation=signature.empty)
                for p in signature.parameters.values()
            )
        ],
        return_annotation=signature.empty,
    )

    pos_args = [
        p
        for p in signature.parameters.values()
        if p.kind.name.startswith("POSITIONAL_")
    ]

    def accept(f):
        fsig = inspect.signature(f, follow_wrapped=False)
        must_pass_as_kwargs = []
        invocation_parts = []
        for p in pos_args:
            if p.name not in fsig.parameters and get_varargs(fsig) is None:
                must_pass_as_kwargs.append(p.name)
            else:
                invocation_parts.append(p.name)
        if get_varargs(signature) is not None:
            invocation_parts.append("*" + get_varargs(signature).name)
        for k in must_pass_as_kwargs:
            invocation_parts.append(f"{k}={k}")
        for p in signature.parameters.values():
            if p.kind is p.KEYWORD_ONLY:
                invocation_parts.append(f"{p.name}={p.name}")
        varkw = get_varargs(signature, kind=Parameter.VAR_KEYWORD)
        if varkw:
            invocation_parts.append("**" + varkw.name)

        candidate_names = ["f"] + [f"f_{i}" for i in range(1, len(used_names) + 2)]

        for funcname in candidate_names:  # pragma: no branch
            if funcname not in used_names:
                break

        source = COPY_SIGNATURE_SCRIPT.format(
            name=name,
            funcname=funcname,
            signature=str(newsig),
            invocation=", ".join(invocation_parts),
        )
        result = source_exec_as_module(source).accept(f)
        result.__doc__ = docstring
        result.__defaults__ = tuple(
            p.default
            for p in signature.parameters.values()
            if p.default is not signature.empty and "POSITIONAL" in p.kind.name
        )
        kwdefaults = {
            p.name: p.default
            for p in signature.parameters.values()
            if p.default is not signature.empty and p.kind is p.KEYWORD_ONLY
        }
        if kwdefaults:
            result.__kwdefaults__ = kwdefaults
        annotations = {
            p.name: p.annotation
            for p in signature.parameters.values()
            if p.annotation is not signature.empty
        }
        if signature.return_annotation is not signature.empty:
            annotations["return"] = signature.return_annotation
        if annotations:
            result.__annotations__ = annotations
        return result

    return accept


def impersonate(target):
    """Decorator to update the attributes of a function so that to external
    introspectors it will appear to be the target function.

    Note that this updates the function in place, it doesn't return a
    new one.
    """

    def accept(f):
        # Lie shamelessly about where this code comes from, to hide the hypothesis
        # internals from pytest, ipython, and other runtime introspection.
        f.__code__ = f.__code__.replace(
            co_filename=target.__code__.co_filename,
            co_firstlineno=target.__code__.co_firstlineno,
        )
        f.__name__ = target.__name__
        f.__module__ = target.__module__
        f.__doc__ = target.__doc__
        f.__globals__["__hypothesistracebackhide__"] = True
        # But leave an breadcrumb for _describe_lambda to follow, it's
        # just confused by the lies above
        f.__wrapped_target = target
        return f

    return accept


def proxies(target: T) -> Callable[[Callable], T]:
    replace_sig = define_function_signature(
        target.__name__.replace("<lambda>", "_lambda_"),  # type: ignore
        target.__doc__,
        get_signature(target, follow_wrapped=False),
    )

    def accept(proxy):
        return impersonate(target)(wraps(target)(replace_sig(proxy)))

    return accept


def is_identity_function(f: Callable) -> bool:
    try:
        code = f.__code__
    except AttributeError:
        try:
            f = f.__call__  # type: ignore
            code = f.__code__
        except AttributeError:
            return False

    # We only accept a single unbound argument. While it would be possible to
    # accept extra defaulted arguments, it would be pointless as they couldn't
    # be referenced at all in the code object (or the co_code check would fail).
    bound_args = int(inspect.ismethod(f))
    if code.co_argcount != bound_args + 1 or code.co_kwonlyargcount > 0:
        return False

    # We know that f accepts a single positional argument, now check that its
    # code object is simply "return first unbound argument".
    template = (lambda self, x: x) if bound_args else (lambda x: x)  # type: ignore
    try:
        return code.co_code == template.__code__.co_code
    except AttributeError:  # pragma: no cover  # pypy only
        # In PyPy, some builtin functions have a code object ('builtin-code')
        # lacking co_code, perhaps because they are native-compiled and don't have
        # a corresponding bytecode. Regardless, since Python doesn't have any
        # builtin identity function it seems safe to say that this one isn't
        return False
