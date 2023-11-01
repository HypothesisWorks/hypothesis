import operator
from datetime import datetime, time, timezone
from functools import partial
from typing import Any, Callable, Iterator, List, Protocol, Tuple, Type, TypeVar

import annotated_types as at

import hypothesis.strategies as st
from hypothesis.errors import InvalidArgument

try:
    import zoneinfo
except ImportError:
    try:
        from backports import zoneinfo  # type: ignore
    except ImportError:
        # We raise an error recommending `pip install hypothesis[zoneinfo]`
        # when at.Timezone is used.
        zoneinfo = None  # type: ignore


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


def _infer_strategy(type_: Type[Ex], constraints: List[at.BaseMetadata]) -> st.SearchStrategy[Ex]:
    tz_constraint = next((c for c in constraints if isinstance(c, at.Timezone)), None)
    if tz_constraint is not None:
        if type_ not in [datetime, time]:
            raise InvalidArgument(f"Annotated type {type_} is not applicable with constraint {tz_constraint}")

        constructor = st.datetimes if type_ is datetime else st.times
        tz_attr = tz_constraint.tz

        if tz_attr is None:
            return constructor()
        if tz_attr is ...:
            return constructor(timezones=st.timezones())
        if isinstance(tz_attr, timezone):
            return constructor(timezones=st.just(tz_attr))
        if isinstance(tz_attr, str):
            if zoneinfo is None:
                # TODO this is duplicated from the st.timezones body, should be refactored:
                raise ModuleNotFoundError(
                    "The zoneinfo module is required, but could not be imported.  "
                    "Run `pip install hypothesis[zoneinfo]` and try again."
                )
            return constructor(timezones=st.just(zoneinfo.ZoneInfo(tz_attr)))
        else:
            raise InvalidArgument(f"Unknown argument for annotated_types.Timezone: {tz_attr!r}")

    return st.from_type(type_)


def from_annotated_types(type_: Type[Ex], args: Tuple[Any, ...]) -> st.SearchStrategy[Ex]:
    constraints = list(_get_constraints(args))
    base_strategy = _infer_strategy(type_, constraints)

    filter_conditions: List[Callable[[Any], Any]] = []
    for constraint in constraints:
        if type(constraint) in CONSTRAINTS_FILTER_MAP:
            condition = CONSTRAINTS_FILTER_MAP[type(constraint)]
            filter_conditions.append(condition(constraint))

    for filter_condition in filter_conditions:
        base_strategy = base_strategy.filter(filter_condition)

    return base_strategy
