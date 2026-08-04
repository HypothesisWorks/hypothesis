# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Recover preimages of string-building functions, for inverting .map().

Given ``strategy.map(f)`` where ``f`` builds a string - by concatenating
constants, interpolating into an f-string / str.format / %%-template, calling
``str()``, or applying string methods like ``.upper()`` or ``.replace()`` -
we can often work out which argument(s) would have produced a given output.
:func:`preimage_candidates` analyses the source of ``f`` (via the same
machinery as our filter-rewriting: :mod:`hypothesis.internal.filtering` and
:mod:`hypothesis.internal.lambda_sources`) and yields candidate preimages in
roughly simplest-first order.

Everything here is best-effort and unverified: template matching is ambiguous
(``f"{a}-{b}"`` matched against ``"x-y-z"`` has two splits), case-folding is
lossy, and a rebound global can make the analysed source diverge from runtime
behaviour.  Callers *must* check ``equal_values(f(candidate), value)`` before
trusting a candidate; ``MappedStrategy._invert`` does so unconditionally, and
the eventual replay re-verifies again, so a wrong candidate costs only a
missed shrinking opportunity, never correctness.

Ambiguous inverses (template splits, un-replacements, ...) are enumerated
lazily and bounded: at most ``_MAX_CANDIDATES`` candidates are ever yielded
per call, and the more explosive per-op enumerations carry their own small
internal bounds.  We deliberately re-analyse the function on every call
rather than caching by function object; this only runs at shrink time.
"""

import ast
import inspect
import string
import textwrap
import types
from itertools import combinations, islice
from typing import NamedTuple

from hypothesis.errors import CannotInvert
from hypothesis.internal.conjecture.junkdrawer import equal_values
from hypothesis.internal.lambda_sources import lambda_description

_MAX_CANDIDATES = 32
_MAX_HOLES = 4
_MAX_UNREPLACE_SITES = 5

# binding key for the whole argument, as opposed to an integer index into it
_WHOLE = object()
_unresolved = object()

_CASE_METHODS = ("upper", "lower", "title", "casefold", "capitalize", "swapcase")
_STRIP_METHODS = ("strip", "lstrip", "rstrip")
_SYNTH_DESCRIPTORS = _CASE_METHODS + _STRIP_METHODS


class _Unsupported(Exception):
    pass


class _Ctx(NamedTuple):
    argname: str
    cells: dict
    globals: dict


class _Hole(NamedTuple):
    node: ast.expr
    # how the hole's value was rendered into its segment: "direct" (already a
    # str), "str" (via str()/format()), or "int" (via %d)
    conv: str


def _resolve(node, ctx):
    """Evaluate a constant subexpression, or return _unresolved.

    Only literals, closure/global variable lookups, and tuples thereof - never
    calls, attributes, or anything else that could execute user code.
    """
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name) and node.id != ctx.argname:
        if node.id in ctx.cells:
            return ctx.cells[node.id]
        return ctx.globals.get(node.id, _unresolved)
    if isinstance(node, ast.Tuple):
        elts = [_resolve(e, ctx) for e in node.elts]
        if any(e is _unresolved for e in elts):
            return _unresolved
        return tuple(elts)
    return _unresolved


def _resolve_str(node, ctx):
    value = _resolve(node, ctx)
    # a str subclass is fine as a template/prefix; use its plain-str content
    return str(value) if isinstance(value, str) else _unresolved


def _formatted_hole(node, ctx):
    # an ast.FormattedValue: support plain {x} and {x!s}, but no format specs
    if node.conversion not in (-1, ord("s")):
        raise _Unsupported
    spec = node.format_spec
    if spec is not None and not (isinstance(spec, ast.JoinedStr) and not spec.values):
        raise _Unsupported
    return _Hole(node.value, "str")


def _flatten_concat(node, ctx):
    """Decompose a concatenation-family expression into a list of constant
    string segments and _Holes."""
    const = _resolve_str(node, ctx)
    if const is not _unresolved:
        return [const]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _flatten_concat(node.left, ctx) + _flatten_concat(node.right, ctx)
    if isinstance(node, ast.JoinedStr):
        segments = []
        for part in node.values:
            if isinstance(part, ast.FormattedValue):
                segments.append(_formatted_hole(part, ctx))
            else:
                assert isinstance(part, ast.Constant)
                assert isinstance(part.value, str)
                segments.append(part.value)
        return segments
    return [_Hole(node, "direct")]


def _format_segments(node, ctx):
    """Segments for a ``template.format(...)`` call node."""
    template = _resolve_str(node.func.value, ctx)
    if template is _unresolved or any(k.arg is None for k in node.keywords):
        raise _Unsupported
    keywords = {k.arg: k.value for k in node.keywords}
    segments = []
    auto = 0
    try:
        parsed = list(string.Formatter().parse(template))
    except ValueError:
        raise _Unsupported from None
    for literal, field, spec, conversion in parsed:
        segments.append(literal)
        if field is None:
            continue
        if spec not in (None, "") or conversion not in (None, "s"):
            raise _Unsupported
        if field == "":
            field, auto = str(auto), auto + 1
        if field.isdigit():
            if int(field) >= len(node.args):
                raise _Unsupported
            sub = node.args[int(field)]
        elif field.isidentifier() and field in keywords:
            sub = keywords[field]
        else:
            raise _Unsupported
        segments.append(_Hole(sub, "str"))
    return segments


def _percent_segments(template, right):
    """Segments for a ``template % right`` node; supports %s, %d, and %%."""
    parts = []
    buf = []
    i = 0
    while i < len(template):
        if template[i] == "%":
            if i + 1 >= len(template):
                raise _Unsupported
            c = template[i + 1]
            if c == "%":
                buf.append("%")
            elif c in "sd":
                parts.append(("".join(buf), c))
                buf.clear()
            else:
                raise _Unsupported
            i += 2
        else:
            buf.append(template[i])
            i += 1
    trailing = "".join(buf)

    if isinstance(right, ast.Tuple):
        nodes = list(right.elts)
    elif len(parts) == 1:
        nodes = [right]
    elif isinstance(right, ast.Name):
        # "%s=%s" % t: the fields index into the single tuple argument
        nodes = [
            ast.Subscript(value=right, slice=ast.Constant(value=i))
            for i in range(len(parts))
        ]
    else:
        raise _Unsupported
    if len(nodes) != len(parts):
        raise _Unsupported

    segments = []
    for (literal, conv), sub in zip(parts, nodes, strict=True):
        segments.append(literal)
        segments.append(_Hole(sub, "str" if conv == "s" else "int"))
    segments.append(trailing)
    return segments


def _assignments(segments, value):
    """Yield lists of (hole, substring) pairs matching value against the
    template, shortest-earlier-holes first."""
    if not segments:
        if not value:
            yield []
        return
    seg, rest = segments[0], segments[1:]
    if isinstance(seg, str):
        if value.startswith(seg):
            yield from _assignments(rest, value[len(seg) :])
        return
    if not rest:
        yield [(seg, value)]
        return
    if isinstance(rest[0], str) and rest[0]:
        # the next segment is a nonempty literal: split at its occurrences
        start = 0
        while (i := value.find(rest[0], start)) != -1:
            for tail in _assignments(rest[1:], value[i + len(rest[0]) :]):
                yield [(seg, value[:i]), *tail]
            start = i + 1
    else:
        for i in range(len(value) + 1):
            for tail in _assignments(rest, value[i:]):
                yield [(seg, value[:i]), *tail]


def _str_parse_candidates(s):
    """Values v with str(v) == s, i.e. preimages of a str()-rendering."""
    yield s
    try:
        i = int(s)
        if str(i) == s:
            yield i
    except ValueError:
        pass
    try:
        x = float(s)
        if str(x) == s:
            yield x
    except (ValueError, OverflowError):
        pass
    if s in ("True", "False"):
        yield s == "True"
    if s == "None":
        yield None


def _invert_hole(hole, segment, ctx):
    if hole.conv == "direct":
        yield from _invert_node(hole.node, segment, ctx)
    elif hole.conv == "str":
        for v in _str_parse_candidates(segment):
            yield from _invert_node(hole.node, v, ctx)
    else:
        assert hole.conv == "int"
        try:
            v = int(segment)
        except ValueError:
            return
        if str(v) == segment:  # %d renders exactly as str() for an int
            yield from _invert_node(hole.node, v, ctx)


def _merge(a, b):
    merged = dict(a)
    for key, value in b.items():
        if key in merged:
            if not equal_values(merged[key], value):
                return None
        else:
            merged[key] = value
    return merged


def _match_and_bind(segments, value, ctx):
    if sum(isinstance(s, _Hole) for s in segments) > _MAX_HOLES:
        return

    def bind(assignment, acc):
        if not assignment:
            yield acc
            return
        (hole, segment), rest = assignment[0], assignment[1:]
        for b in _invert_hole(hole, segment, ctx):
            if (merged := _merge(acc, b)) is not None:
                yield from bind(rest, merged)

    for assignment in _assignments(segments, value):
        yield from bind(assignment, {})


def _case_candidates(value, method):
    out = []
    foldings = (
        value,
        value.lower(),
        value.upper(),
        value.capitalize(),
        value.title(),
        value.swapcase(),
        value.casefold(),
    )
    for pre in foldings:
        if pre not in out and getattr(pre, method)() == value:
            out.append(pre)
    return out


def _unreplace_candidates(value, old, new):
    """Strings pre with pre.replace(old, new) == value, boundedly many."""
    if not old or old == new:
        candidates = [value]
    elif not new:
        # replacement deleted every occurrence of old; positions unrecoverable
        candidates = [value]
    else:
        candidates = [value.replace(new, old), value]
        positions = []
        start = 0
        while (i := value.find(new, start)) != -1:
            positions.append(i)
            start = i + len(new)
        if 1 < len(positions) <= _MAX_UNREPLACE_SITES:
            # partial un-replacements: some occurrences of new were literal
            for r in range(len(positions) - 1, 0, -1):
                for combo in combinations(positions, r):
                    pre = []
                    prev = 0
                    for pos in combo:
                        pre.append(value[prev:pos])
                        pre.append(old)
                        prev = pos + len(new)
                    pre.append(value[prev:])
                    candidates.append("".join(pre))
    seen = []
    for pre in candidates:
        if pre not in seen and pre.replace(old, new) == value:
            seen.append(pre)
            yield pre


def _zfill_candidates(value, width):
    out = []
    if value.zfill(width) == value:
        out.append(value)
    sign = value[0] if value[:1] in ("+", "-") else ""
    body = value[len(sign) :]
    leading = len(body) - len(body.lstrip("0"))
    for k in range(leading, 0, -1):  # most-stripped (simplest) first
        pre = sign + body[k:]
        if pre not in out and pre.zfill(width) == value:
            out.append(pre)
    return out


def _invert_method_call(node, value, ctx):
    method = node.func.attr
    recv = node.func.value
    if node.keywords and method != "format":
        return
    args = [_resolve(a, ctx) for a in node.args]
    if method not in ("join", "format") and any(a is _unresolved for a in args):
        return

    if method in _CASE_METHODS and not args:
        for pre in _case_candidates(value, method):
            yield from _invert_node(recv, pre, ctx)
    elif method in _STRIP_METHODS and len(args) <= 1:
        chars = args[0] if args else None
        if not (chars is None or isinstance(chars, str)):
            return
        # only the fixed point; re-adding stripped characters is unbounded
        if getattr(value, method)(chars) == value:
            yield from _invert_node(recv, value, ctx)
    elif method == "replace" and len(args) == 2:
        old, new = args
        if isinstance(old, str) and isinstance(new, str):
            for pre in _unreplace_candidates(value, old, new):
                yield from _invert_node(recv, pre, ctx)
    elif method in ("removeprefix", "removesuffix") and len(args) == 1:
        affix = args[0]
        if not isinstance(affix, str):
            return
        readded = affix + value if method == "removeprefix" else value + affix
        for pre in (value, readded):
            if getattr(pre, method)(affix) == value:
                yield from _invert_node(recv, pre, ctx)
    elif method == "zfill" and len(args) == 1:
        if isinstance(args[0], int) and not isinstance(args[0], bool):
            for pre in _zfill_candidates(value, args[0]):
                yield from _invert_node(recv, pre, ctx)
    elif method == "join" and len(node.args) == 1:
        sep = _resolve_str(recv, ctx)
        if sep is _unresolved:
            return
        parts = value.split(sep) if sep else list(value)
        # sep.join(value.split(sep)) == value always holds, so no local check
        for pre in (parts, tuple(parts)):
            yield from _invert_node(node.args[0], pre, ctx)
    elif method == "format":
        try:
            segments = _format_segments(node, ctx)
        except _Unsupported:
            return
        yield from _match_and_bind(segments, value, ctx)


def _invert_node(node, value, ctx):
    """Yield candidate bindings {_WHOLE: v} or {index: v, ...} such that
    evaluating node with the argument so bound plausibly gives value."""
    if isinstance(node, ast.Name) and node.id == ctx.argname:
        yield {_WHOLE: value}
        return
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == ctx.argname
        and isinstance(node.slice, ast.Constant)
        and type(node.slice.value) is int
        and node.slice.value >= 0
    ):
        yield {node.slice.value: value}
        return
    const = _resolve(node, ctx)
    if const is not _unresolved:
        if equal_values(const, value):
            yield {}
        return
    if not isinstance(value, str):
        return

    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Add):
            try:
                segments = _flatten_concat(node, ctx)
            except _Unsupported:
                return
            yield from _match_and_bind(segments, value, ctx)
        elif isinstance(node.op, ast.Mult):
            for cnode, sub in ((node.left, node.right), (node.right, node.left)):
                const = _resolve(cnode, ctx)
                if isinstance(const, int) and not isinstance(const, bool):
                    if const >= 1 and len(value) % const == 0:
                        pre = value[: len(value) // const]
                        if pre * const == value:
                            yield from _invert_node(sub, pre, ctx)
                    return
                elif isinstance(const, str):
                    if const and len(value) % len(const) == 0:
                        k = len(value) // len(const)
                        if const * k == value:
                            yield from _invert_node(sub, k, ctx)
                    return
        elif isinstance(node.op, ast.Mod):
            template = _resolve_str(node.left, ctx)
            if template is _unresolved:
                return
            try:
                segments = _percent_segments(template, node.right)
            except _Unsupported:
                return
            yield from _match_and_bind(segments, value, ctx)
    elif isinstance(node, ast.JoinedStr):
        try:
            segments = _flatten_concat(node, ctx)
        except _Unsupported:
            return
        yield from _match_and_bind(segments, value, ctx)
    elif isinstance(node, ast.Call):
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "str"
            and len(node.args) == 1
            and not node.keywords
            and "str" not in ctx.cells
            and ctx.globals.get("str", str) is str
        ):
            for v in _str_parse_candidates(value):
                yield from _invert_node(node.args[0], v, ctx)
        elif isinstance(node.func, ast.Attribute):
            yield from _invert_method_call(node, value, ctx)


def _source_and_scope(fn):
    """Return (source, cells, globals) for fn, raising CannotInvert if its
    source is unavailable.  A few sourceless builtins are recognized directly
    by synthesizing an equivalent lambda."""
    if fn is str:
        return "lambda x: str(x)", {}, {}
    if (
        isinstance(fn, types.MethodDescriptorType)
        and getattr(fn, "__objclass__", None) is str
        and fn.__name__ in _SYNTH_DESCRIPTORS
    ):
        return f"lambda x: x.{fn.__name__}()", {}, {}
    if (
        isinstance(fn, types.BuiltinMethodType)
        and isinstance(getattr(fn, "__self__", None), str)
        and fn.__name__ in ("join", "format")
    ):
        return f"lambda x: _self.{fn.__name__}(x)", {"_self": fn.__self__}, {}
    if not isinstance(fn, types.FunctionType):
        raise CannotInvert(f"no source available for {fn!r}")
    if fn.__name__ == "<lambda>":
        source = lambda_description(fn)
        if "<unknown>" in source:
            raise CannotInvert(f"could not extract source of {fn!r}")
    else:
        try:
            source = textwrap.dedent(inspect.getsource(fn))
        except (OSError, TypeError):
            raise CannotInvert(f"could not extract source of {fn!r}") from None
    cells = {}
    if fn.__closure__:
        for name, cell in zip(fn.__code__.co_freevars, fn.__closure__, strict=True):
            try:
                cells[name] = cell.cell_contents
            except ValueError:  # pragma: no cover  # empty cell
                pass
    return source, cells, fn.__globals__


def _analyze(fn):
    source, cells, globs = _source_and_scope(fn)
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):  # pragma: no cover
        # lambda_description output and synthesized sources always parse, so
        # this is reachable only via a pathological inspect.getsource result
        raise CannotInvert(f"could not parse source of {fn!r}") from None
    while isinstance(tree, ast.Module) and len(tree.body) == 1:
        tree = tree.body[0]
    while isinstance(tree, ast.Expr):
        tree = tree.value

    if isinstance(tree, ast.Lambda):
        body = tree.body
    elif isinstance(tree, ast.FunctionDef):
        stmts = tree.body
        if stmts and isinstance(stmts[0], ast.Expr):  # docstring
            stmts = stmts[1:]
        if len(stmts) != 1 or not isinstance(stmts[0], ast.Return):
            raise CannotInvert(f"body of {fn!r} is not a single expression")
        body = stmts[0].value
    else:
        raise CannotInvert(f"could not analyze {fn!r}")
    arguments = tree.args
    params = arguments.posonlyargs + arguments.args
    if (
        len(params) != 1
        or body is None
        or arguments.vararg
        or arguments.kwonlyargs
        or arguments.kwarg
    ):
        raise CannotInvert(f"{fn!r} does not take exactly one argument")
    return body, _Ctx(params[0].arg, cells, globs)


def preimage_candidates(fn, value):
    """Analyze fn and return an iterator of candidate arguments x such that
    fn(x) may equal value, simplest-first and capped at _MAX_CANDIDATES.

    Raises CannotInvert if fn cannot be analyzed at all.  Candidates are NOT
    verified: callers must check equal_values(fn(candidate), value).
    """
    body, ctx = _analyze(fn)

    def gen():
        for binding in _invert_node(body, value, ctx):
            if not binding:
                continue
            if set(binding) == {_WHOLE}:
                yield binding[_WHOLE]
            elif _WHOLE not in binding and set(binding) == set(range(len(binding))):
                # fn indexed into its argument: it was a tuple (or list)
                elements = tuple(binding[i] for i in range(len(binding)))
                yield elements
                yield list(elements)

    return islice(gen(), _MAX_CANDIDATES)
