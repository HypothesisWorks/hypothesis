# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import operator
import warnings
from functools import partial
from typing import Any, Callable, Iterator, List, Protocol, Tuple, Type, TypeVar

import annotated_types as at

import hypothesis.strategies as st
from hypothesis.errors import HypothesisWarning
from hypothesis.reporting import debug_report

Ex = TypeVar("Ex", covariant=True)


class SupportsLen(Protocol):
    def __len__(self) -> int:
        ...


def max_len(element: SupportsLen, max_length: int) -> bool:
    return len(element) <= max_length


def min_len(element: SupportsLen, min_length: int) -> bool:
    return len(element) >= min_length


CONSTRAINTS_FILTER_MAP = {
    # Due to the order of operator.gt/ge/lt/le arguments, order is inversed:
    at.Gt: lambda constraint: partial(operator.lt, constraint.gt),
    at.Ge: lambda constraint: partial(operator.le, constraint.ge),
    at.Lt: lambda constraint: partial(operator.gt, constraint.lt),
    at.Le: lambda constraint: partial(operator.ge, constraint.le),
    at.MaxLen: lambda constraint: partial(max_len, max_length=constraint.max_length),
    at.MinLen: lambda constraint: partial(min_len, max_length=constraint.min_length),
    at.Predicate: lambda constraint: constraint.func,
}


def _get_constraints(args: Tuple[Any, ...]) -> Iterator[at.BaseMetadata]:
    for arg in args:
        if isinstance(arg, at.BaseMetadata):
            yield arg
        elif getattr(arg, "__is_annotated_types_grouped_metadata__", False):
            yield from arg
        elif isinstance(arg, slice):
            yield from at.Len(arg.start or 0, arg.stop)


def from_annotated_types(
    type_: Type[Ex], args: Tuple[Any, ...]
) -> st.SearchStrategy[Ex]:
    # `constraints` elements can be "consumed" by the next following calls/instructions
    constraints = list(_get_constraints(args))

    unsupported_constraints = [
        c for c in constraints if isinstance(c, (at.MultipleOf, at.Timezone))
    ]
    unknown_constraints = []

    if unsupported_constraints:
        warnings.warn(
            f"{', '.join(map(repr, unsupported_constraints))} ",
            f"{'is' if len(unsupported_constraints) == 1 else 'are'} ",
            "currently not supported and will be ignored.",
            HypothesisWarning,
            stacklevel=2,
        )
        for c in unsupported_constraints:
            constraints.remove(c)

    base_strategy = st.from_type(type_)

    filter_conditions: List[Callable[[Any], Any]] = []
    for constraint in constraints:
        if type(constraint) in CONSTRAINTS_FILTER_MAP:
            condition = CONSTRAINTS_FILTER_MAP[type(constraint)](constraint)
            filter_conditions.append(condition)
        else:
            unknown_constraints.append(constraint)

    for filter_condition in filter_conditions:
        base_strategy = base_strategy.filter(filter_condition)

    if unknown_constraints:
        debug_report(
            "WARNING: the following constraints are unknown and will be ignored: "
            f"{', '.join(map(repr, unknown_constraints))}."
        )

    return base_strategy
