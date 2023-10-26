import operator
from typing import Any, Tuple, Type, TypeVar, Iterator, Callable, List
from functools import partial

try:
    import annotated_types
except ImportError:
    annotated_types = None

from hypothesis.strategies import from_type

T = TypeVar("T")


def get_constraints(args: Tuple[Any, ...]) -> Iterator[annotated_types.BaseMetadata]:
    for arg in args:
        if isinstance(arg, annotated_types.BaseMetadata):
            yield arg
        elif getattr(arg, "__is_annotated_types_grouped_metadata__", False):
            yield from arg
        elif isinstance(arg, slice):
            yield from annotated_types.Len(arg.start or 0, arg.stop)


def from_annotated_types(type_: Type[T], args: Tuple[Any, ...]):
    if annotated_types is None:
        return None

    base_strategy = from_type(type_)

    filter_conditions: List[Callable[[Any], Any]] = []
    for constraint in get_constraints(args):
        if isinstance(constraint, annotated_types.Gt):
            filter_conditions.append(partial(operator.gt, constraint.gt))
        if isinstance(constraint, annotated_types.Ge):
            filter_conditions.append(partial(operator.ge, constraint.ge))
        if isinstance(constraint, annotated_types.Lt):
            filter_conditions.append(partial(operator.lt, constraint.lt))
        if isinstance(constraint, annotated_types.Le):
            filter_conditions.append(partial(operator.le, constraint.le))
        if isinstance(constraint, annotated_types.Predicate):
            filter_conditions.append(constraint.func)
