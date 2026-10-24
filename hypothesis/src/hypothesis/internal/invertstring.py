# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Recover preimages of string-building packs, for inverting ``.map()``.

Given ``strategy.map(f)`` where ``f`` wraps its argument in constant text -
``lambda s: "id-" + s``, ``lambda s: f"id-{s}"``, or the bound method
``"id-{}".format`` - work out which argument produced a given output by
analysing the source of ``f``. Everything here is best-effort and
unverified: callers must check ``equal_values(f(preimage), value)`` before
trusting a candidate preimage.
"""

import ast
import inspect
import string
import textwrap
import types
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal, TypeAlias

from hypothesis.internal.lambda_sources import lambda_description


@dataclass(slots=True, frozen=True)
class _Ctx:
    argname: str
    cells: dict
    globals: dict


_ConvT: TypeAlias = Literal["direct", "str"]


@dataclass(slots=True, frozen=True)
class _Hole:
    conv: _ConvT


@dataclass(slots=True, frozen=True)
class Template:
    """A pack of the form ``prefix + arg + suffix``, rendering the argument
    directly (``conv="direct"``) or via str() (``conv="str"``)."""

    prefix: str
    suffix: str
    conv: _ConvT

    def split(self, value: str) -> "str | None":
        """The substring of value the argument rendered into, or None if the
        constant prefix/suffix is absent - which proves value is not in the
        pack's image."""
        if (
            len(value) >= len(self.prefix) + len(self.suffix)
            and value.startswith(self.prefix)
            and value.endswith(self.suffix)
        ):
            return value[len(self.prefix) : len(value) - len(self.suffix)]
        return None

    def parses(self, segment: str) -> Iterator[object]:
        """Unverified candidate preimages rendering as segment."""
        yield segment
        if self.conv == "str":
            # The pre-format value is genuinely unknown here: we know what it
            # rendered into, not what it was.
            # TODO: represent that as a hole with an unknown value, instead
            # of guessing likely parses.
            try:
                yield ast.literal_eval(segment)
            except Exception:
                pass


def _resolve_str(node: ast.expr, ctx: _Ctx) -> "str | None":
    """Evaluate a constant string subexpression - only literals and
    closure/global lookups, never anything that could execute user code."""
    if isinstance(node, ast.Constant):
        value: object = node.value
    elif isinstance(node, ast.Name) and node.id != ctx.argname:
        value = ctx.cells[node.id] if node.id in ctx.cells else ctx.globals.get(node.id)
    else:
        return None
    # a str subclass is fine as a constant segment; use its plain-str content
    return str(value) if isinstance(value, str) else None


def _format_segments(template: str) -> "list[str | _Hole] | None":
    """Segments of a format template like ``"id-{}"``: literal strings
    interleaved with holes, or None for specs we don't support."""
    out: list[str | _Hole] = []
    try:
        parsed = list(string.Formatter().parse(template))
    except ValueError:
        return None
    for literal, field, spec, conversion in parsed:
        out.append(literal)
        if field is None:
            continue
        if (
            field not in ("", "0")
            or spec not in (None, "")
            or conversion not in (None, "s")
        ):
            return None
        out.append(_Hole("str"))
    return out


def _segments(node: ast.expr, ctx: _Ctx) -> "list[str | _Hole] | None":
    """Decompose a string-building expression into constant segments and
    holes for the argument, or None if it is not a supported shape."""
    if (const := _resolve_str(node, ctx)) is not None:
        return [const]
    if isinstance(node, ast.Name) and node.id == ctx.argname:
        return [_Hole("direct")]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _segments(node.left, ctx)
        right = _segments(node.right, ctx)
        if left is None or right is None:
            return None
        return left + right
    if isinstance(node, ast.JoinedStr):
        out: list[str | _Hole] = []
        for part in node.values:
            if isinstance(part, ast.FormattedValue):
                if (
                    part.conversion not in (-1, ord("s"))
                    or part.format_spec is not None
                    or not isinstance(part.value, ast.Name)
                    or part.value.id != ctx.argname
                ):
                    return None
                out.append(_Hole("str"))
            else:
                assert isinstance(part, ast.Constant)
                assert isinstance(part.value, str)
                out.append(part.value)
        return out
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "format"
        and not node.keywords
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == ctx.argname
    ):
        template = _resolve_str(node.func.value, ctx)
        if template is None:
            return None
        return _format_segments(template)
    return None


def _to_template(segments: "list[str | _Hole] | None") -> "Template | None":
    if segments is None:
        return None
    holes = [s for s in segments if isinstance(s, _Hole)]
    if len(holes) != 1:
        return None
    i = segments.index(holes[0])
    # everything other than the single hole is a constant string segment
    return Template(
        prefix="".join(s for s in segments[:i] if isinstance(s, str)),
        suffix="".join(s for s in segments[i + 1 :] if isinstance(s, str)),
        conv=holes[0].conv,
    )


def string_template(fn: object) -> "Template | None":
    """The single-hole constant-text template fn builds, or None if fn
    cannot be analysed or is not of that shape."""
    if fn in (str, repr):
        # str and repr are the trivial template: parse the whole value back
        return Template(prefix="", suffix="", conv="str")
    # the bound-method pattern .map("id-{}".format) has no source to analyse;
    # recognize it directly from the template it is bound to
    if (
        isinstance(fn, types.BuiltinMethodType)
        and fn.__name__ == "format"
        and isinstance(getattr(fn, "__self__", None), str)
    ):
        return _to_template(_format_segments(str(fn.__self__)))
    if not isinstance(fn, types.FunctionType):
        return None
    if fn.__name__ == "<lambda>":
        source = lambda_description(fn)
        if "<unknown>" in source:
            return None
    else:
        try:
            source = textwrap.dedent(inspect.getsource(fn))
        except (OSError, TypeError):
            return None
    try:
        tree: ast.AST = ast.parse(source)
    except (SyntaxError, ValueError):  # pragma: no cover
        return None
    while isinstance(tree, ast.Module) and len(tree.body) == 1:
        tree = tree.body[0]
    while isinstance(tree, ast.Expr):
        tree = tree.value

    if isinstance(tree, ast.Lambda):
        body: ast.expr | None = tree.body
    elif isinstance(tree, ast.FunctionDef):
        stmts = tree.body
        if stmts and isinstance(stmts[0], ast.Expr):  # docstring
            stmts = stmts[1:]
        if len(stmts) != 1 or not isinstance(stmts[0], ast.Return):
            return None
        body = stmts[0].value
    else:
        return None
    if body is None:
        return None
    arguments = tree.args
    params = arguments.posonlyargs + arguments.args
    if len(params) != 1 or arguments.vararg or arguments.kwonlyargs or arguments.kwarg:
        return None

    cells = {}
    if fn.__closure__:
        for name, cell in zip(fn.__code__.co_freevars, fn.__closure__, strict=True):
            try:
                cells[name] = cell.cell_contents
            except ValueError:  # pragma: no cover  # empty cell
                pass
    ctx = _Ctx(params[0].arg, cells, fn.__globals__)
    return _to_template(_segments(body, ctx))
