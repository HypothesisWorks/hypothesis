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

"""Tools for understanding predicates, to satisfy them by construction.

For example::

    integers().filter(lamda x: x >= 0) -> integers(min_value=0)

This is intractable in general, but reasonably easy for simple cases involving
numeric bounds, strings with length or regex constraints, and collection lengths -
and those are precisely the most common cases.  When they arise in e.g. Pandas
dataframes, it's also pretty painful to do the constructive version by hand in
a library; so we prefer to share all the implementation effort here.
See https://github.com/HypothesisWorks/hypothesis/issues/2701 for details.
"""

import ast
import inspect
import math
import operator
from decimal import Decimal
from fractions import Fraction
from functools import partial
from typing import Any, Callable, Dict, NamedTuple, Optional, TypeVar

from hypothesis.internal.compat import ceil, floor
from hypothesis.internal.reflection import extract_lambda_source

Ex = TypeVar("Ex")
Predicate = Callable[[Ex], bool]


class ConstructivePredicate(NamedTuple):
    """Return kwargs to the appropriate strategy, and the predicate if needed.

    For example::

        integers().filter(lambda x: x >= 0)
        -> {"min_value": 0"}, None

        integers().filter(lambda x: x >= 0 and x % 7)
        -> {"min_value": 0}, lambda x: x % 7

    At least in principle - for now we usually return the predicate unchanged
    if needed.

    We have a separate get-predicate frontend for each "group" of strategies; e.g.
    for each numeric type, for strings, for bytes, for collection sizes, etc.
    """

    kwargs: Dict[str, Any]
    predicate: Optional[Predicate]

    @classmethod
    def unchanged(cls, predicate):
        return cls({}, predicate)


ARG = object()


def convert(node, argname):
    if isinstance(node, ast.Name):
        if node.id != argname:
            raise ValueError("Non-local variable")
        return ARG
    return ast.literal_eval(node)


def comp_to_kwargs(a, op, b, *, argname=None):
    """ """
    if isinstance(a, ast.Name) == isinstance(b, ast.Name):
        raise ValueError("Can't analyse this comparison")
    a = convert(a, argname)
    b = convert(b, argname)
    assert (a is ARG) != (b is ARG)

    if isinstance(op, ast.Lt):
        if a is ARG:
            return {"max_value": b, "exclude_max": True}
        return {"min_value": a, "exclude_min": True}
    elif isinstance(op, ast.LtE):
        if a is ARG:
            return {"max_value": b}
        return {"min_value": a}
    elif isinstance(op, ast.Eq):
        if a is ARG:
            return {"min_value": b, "max_value": b}
        return {"min_value": a, "max_value": a}
    elif isinstance(op, ast.GtE):
        if a is ARG:
            return {"min_value": b}
        return {"max_value": a}
    elif isinstance(op, ast.Gt):
        if a is ARG:
            return {"min_value": b, "exclude_min": True}
        return {"max_value": a, "exclude_max": True}
    raise ValueError("Unhandled comparison operator")


def tidy(kwargs):
    if not kwargs["exclude_min"]:
        del kwargs["exclude_min"]
        if kwargs["min_value"] == -math.inf:
            del kwargs["min_value"]
    if not kwargs["exclude_max"]:
        del kwargs["exclude_max"]
        if kwargs["max_value"] == math.inf:
            del kwargs["max_value"]
    return kwargs


def merge_kwargs(*rest):
    base = {
        "min_value": -math.inf,
        "max_value": math.inf,
        "exclude_min": False,
        "exclude_max": False,
    }
    for kw in rest:
        if "min_value" in kw:
            if kw["min_value"] > base["min_value"]:
                base["exclude_min"] = kw.get("exclude_min", False)
                base["min_value"] = kw["min_value"]
            elif kw["min_value"] == base["min_value"]:
                base["exclude_min"] |= kw.get("exclude_min", False)
            else:
                base["exclude_min"] = False
        if "max_value" in kw:
            if kw["max_value"] < base["max_value"]:
                base["exclude_max"] = kw.get("exclude_max", False)
                base["max_value"] = kw["max_value"]
            elif kw["max_value"] == base["max_value"]:
                base["exclude_max"] |= kw.get("exclude_max", False)
            else:
                base["exclude_max"] = False
    return tidy(base)


def numeric_bounds_from_ast(tree, *, argname=None):
    """Take an AST; return a dict of bounds or None.

    >>> lambda x: x >= 0
    {"min_value": 0}
    >>> lambda x: x < 10
    {"max_value": 10, "exclude_max": True}
    >>> lambda x: x >= y
    None
    """
    while isinstance(tree, ast.Module) and len(tree.body) == 1:
        tree = tree.body[0]
    if isinstance(tree, ast.Expr):
        tree = tree.value

    if isinstance(tree, ast.Lambda) and len(tree.args.args) == 1:
        assert argname is None
        return numeric_bounds_from_ast(tree.body, argname=tree.args.args[0].arg)

    if isinstance(tree, ast.FunctionDef) and len(tree.args.args) == 1:
        assert argname is None
        if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Return):
            return None
        return numeric_bounds_from_ast(
            tree.body[0].value, argname=tree.args.args[0].arg
        )

    if isinstance(tree, ast.Compare):
        ops = tree.ops
        vals = tree.comparators
        comparisons = [(tree.left, ops[0], vals[0])]
        for i, (op, val) in enumerate(zip(ops[1:], vals[1:]), start=1):
            comparisons.append((vals[i - 1], op, val))
        try:
            bounds = [comp_to_kwargs(*x, argname=argname) for x in comparisons]
        except ValueError:
            return None
        return merge_kwargs(*bounds)

    if isinstance(tree, ast.BoolOp) and isinstance(tree.op, ast.And):
        bounds = [
            numeric_bounds_from_ast(node, argname=argname) for node in tree.values
        ]
        return merge_kwargs(*bounds)

    return None


UNSATISFIABLE = ConstructivePredicate.unchanged(lambda _: False)


def get_numeric_predicate_bounds(predicate: Predicate) -> ConstructivePredicate:
    """Shared logic for understanding numeric bounds.

    We then specialise this in the other functions below, to ensure that e.g.
    all the values are representable in the types that we're planning to generate
    so that the strategy validation doesn't complain.
    """
    if (
        isinstance(predicate, partial)
        and len(predicate.args) == 1
        and not predicate.keywords
    ):
        arg = predicate.args[0]
        if (
            (isinstance(arg, Decimal) and Decimal.is_snan(arg))
            or not isinstance(arg, (int, float, Fraction, Decimal))
            or math.isnan(arg)
        ):
            return ConstructivePredicate.unchanged(predicate)
        options = {
            # We're talking about op(arg, x) - the reverse of our usual intuition!
            operator.lt: {"min_value": arg, "exclude_min": True},  # lambda x: arg < x
            operator.le: {"min_value": arg},  # lambda x: arg <= x
            operator.eq: {"min_value": arg, "max_value": arg},  # lambda x: arg == x
            operator.ge: {"max_value": arg},  # lambda x: arg >= x
            operator.gt: {"max_value": arg, "exclude_max": True},  # lambda x: arg > x
        }
        if predicate.func in options:
            return ConstructivePredicate(options[predicate.func], None)

    try:
        if predicate.__name__ == "<lambda>":
            source = extract_lambda_source(predicate)
        else:
            source = inspect.getsource(predicate)
        kwargs = numeric_bounds_from_ast(ast.parse(source))
    except Exception:
        pass
    else:
        if kwargs is not None:
            return ConstructivePredicate(kwargs, None)

    return ConstructivePredicate.unchanged(predicate)


def get_integer_predicate_bounds(predicate: Predicate) -> ConstructivePredicate:
    kwargs, predicate = get_numeric_predicate_bounds(predicate)  # type: ignore

    if "min_value" in kwargs:
        if kwargs["min_value"] == -math.inf:
            del kwargs["min_value"]
        elif math.isinf(kwargs["min_value"]):
            return UNSATISFIABLE
        elif kwargs["min_value"] != int(kwargs["min_value"]):
            kwargs["min_value"] = ceil(kwargs["min_value"])
        elif kwargs.get("exclude_min", False):
            kwargs["min_value"] = int(kwargs["min_value"]) + 1

    if "max_value" in kwargs:
        if kwargs["max_value"] == math.inf:
            del kwargs["max_value"]
        elif math.isinf(kwargs["max_value"]):
            return UNSATISFIABLE
        elif kwargs["max_value"] != int(kwargs["max_value"]):
            kwargs["max_value"] = floor(kwargs["max_value"])
        elif kwargs.get("exclude_max", False):
            kwargs["max_value"] = int(kwargs["max_value"]) - 1

    kwargs = {k: v for k, v in kwargs.items() if k in {"min_value", "max_value"}}
    return ConstructivePredicate(kwargs, predicate)
