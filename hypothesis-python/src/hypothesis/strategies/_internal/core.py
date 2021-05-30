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

import enum
import math
import operator
import random
import re
import string
import sys
import typing
from decimal import Context, Decimal, localcontext
from fractions import Fraction
from functools import reduce
from inspect import Parameter, getfullargspec, isabstract, isclass, signature
from types import FunctionType
from typing import (
    Any,
    AnyStr,
    Callable,
    Dict,
    FrozenSet,
    Hashable,
    Iterable,
    List,
    Optional,
    Pattern,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)
from uuid import UUID

import attr

from hypothesis.control import cleanup, note
from hypothesis.errors import InvalidArgument, ResolutionFailed
from hypothesis.internal.cathetus import cathetus
from hypothesis.internal.charmap import as_general_categories
from hypothesis.internal.compat import (
    ceil,
    floor,
    get_type_hints,
    is_typed_named_tuple,
    typing_root_type,
)
from hypothesis.internal.conjecture.utils import (
    calc_label_from_cls,
    check_sample,
    integer_range,
)
from hypothesis.internal.entropy import get_seeder_and_restorer
from hypothesis.internal.reflection import (
    define_function_signature,
    get_pretty_function_description,
    nicerepr,
    required_args,
)
from hypothesis.internal.validation import (
    check_type,
    check_valid_integer,
    check_valid_interval,
    check_valid_magnitude,
    check_valid_size,
    check_valid_sizes,
    try_convert,
)
from hypothesis.strategies._internal import SearchStrategy, check_strategy
from hypothesis.strategies._internal.collections import (
    FixedAndOptionalKeysDictStrategy,
    FixedKeysDictStrategy,
    ListStrategy,
    TupleStrategy,
    UniqueListStrategy,
    UniqueSampledListStrategy,
    tuples,
)
from hypothesis.strategies._internal.deferred import DeferredStrategy
from hypothesis.strategies._internal.functions import FunctionStrategy
from hypothesis.strategies._internal.lazy import LazyStrategy
from hypothesis.strategies._internal.misc import just, none, nothing
from hypothesis.strategies._internal.numbers import Real, floats, integers
from hypothesis.strategies._internal.recursive import RecursiveStrategy
from hypothesis.strategies._internal.shared import SharedStrategy
from hypothesis.strategies._internal.strategies import (
    Ex,
    SampledFromStrategy,
    T,
    one_of,
)
from hypothesis.strategies._internal.strings import (
    FixedSizeBytes,
    OneCharStringStrategy,
)
from hypothesis.strategies._internal.utils import cacheable, defines_strategy
from hypothesis.utils.conventions import InferType, infer, not_set

UniqueBy = Union[Callable[[Ex], Hashable], Tuple[Callable[[Ex], Hashable], ...]]


@cacheable
@defines_strategy()
def booleans() -> SearchStrategy[bool]:
    """Returns a strategy which generates instances of :class:`python:bool`.

    Examples from this strategy will shrink towards ``False`` (i.e.
    shrinking will replace ``True`` with ``False`` where possible).
    """
    return SampledFromStrategy([False, True], repr_="booleans()")


@overload
def sampled_from(elements: Sequence[T]) -> SearchStrategy[T]:
    raise NotImplementedError


@overload  # noqa: F811
def sampled_from(elements: Type[enum.Enum]) -> SearchStrategy[Any]:
    # `SearchStrategy[Enum]` is unreliable due to metaclass issues.
    raise NotImplementedError


@defines_strategy(try_non_lazy=True)  # noqa: F811
def sampled_from(elements):
    """Returns a strategy which generates any value present in ``elements``.

    Note that as with :func:`~hypothesis.strategies.just`, values will not be
    copied and thus you should be careful of using mutable data.

    ``sampled_from`` supports ordered collections, as well as
    :class:`~python:enum.Enum` objects.  :class:`~python:enum.Flag` objects
    may also generate any combination of their members.

    Examples from this strategy shrink by replacing them with values earlier in
    the list. So e.g. ``sampled_from([10, 1])`` will shrink by trying to replace
    1 values with 10, and ``sampled_from([1, 10])`` will shrink by trying to
    replace 10 values with 1.

    It is an error to sample from an empty sequence, because returning :func:`nothing`
    makes it too easy to silently drop parts of compound strategies.  If you need
    that behaviour, use ``sampled_from(seq) if seq else nothing()``.
    """
    values = check_sample(elements, "sampled_from")
    if not values:
        if (
            isinstance(elements, type)
            and issubclass(elements, enum.Enum)
            and vars(elements).get("__annotations__")
        ):
            # See https://github.com/HypothesisWorks/hypothesis/issues/2923
            raise InvalidArgument(
                f"Cannot sample from {elements.__module__}.{elements.__name__} "
                "because it contains no elements.  It does however have annotations, "
                "so maybe you tried to write an enum as if it was a dataclass?"
            )
        raise InvalidArgument("Cannot sample from a length-zero sequence.")
    if len(values) == 1:
        return just(values[0])
    if isinstance(elements, type) and issubclass(elements, enum.Enum):
        repr_ = f"sampled_from({elements.__module__}.{elements.__name__})"
    else:
        repr_ = f"sampled_from({elements!r})"
    if isclass(elements) and issubclass(elements, enum.Flag):
        # Combinations of enum.Flag members are also members.  We generate
        # these dynamically, because static allocation takes O(2^n) memory.
        # LazyStrategy is used for the ease of force_repr.
        inner = sets(sampled_from(list(values)), min_size=1).map(
            lambda s: reduce(operator.or_, s)
        )
        return LazyStrategy(lambda: inner, args=[], kwargs={}, force_repr=repr_)
    return SampledFromStrategy(values, repr_)


def identity(x):
    return x


@cacheable
@defines_strategy()
def lists(
    elements: SearchStrategy[Ex],
    *,
    min_size: int = 0,
    max_size: Optional[int] = None,
    unique_by: Optional[UniqueBy] = None,
    unique: bool = False,
) -> SearchStrategy[List[Ex]]:
    """Returns a list containing values drawn from elements with length in the
    interval [min_size, max_size] (no bounds in that direction if these are
    None). If max_size is 0, only the empty list will be drawn.

    If ``unique`` is True (or something that evaluates to True), we compare direct
    object equality, as if unique_by was ``lambda x: x``. This comparison only
    works for hashable types.

    If ``unique_by`` is not None it must be a callable or tuple of callables
    returning a hashable type when given a value drawn from elements. The
    resulting list will satisfy the condition that for ``i`` != ``j``,
    ``unique_by(result[i])`` != ``unique_by(result[j])``.

    If ``unique_by`` is a tuple of callables the uniqueness will be respective
    to each callable.

    For example, the following will produce two columns of integers with both
    columns being unique respectively.

    .. code-block:: pycon

        >>> twoints = st.tuples(st.integers(), st.integers())
        >>> st.lists(twoints, unique_by=(lambda x: x[0], lambda x: x[1]))

    Examples from this strategy shrink by trying to remove elements from the
    list, and by shrinking each individual element of the list.
    """
    check_valid_sizes(min_size, max_size)
    check_strategy(elements, "elements")
    if unique:
        if unique_by is not None:
            raise InvalidArgument(
                "cannot specify both unique and unique_by "
                "(you probably only want to set unique_by)"
            )
        else:
            unique_by = identity

    if max_size == 0:
        return builds(list)
    if unique_by is not None:
        if not (callable(unique_by) or isinstance(unique_by, tuple)):
            raise InvalidArgument(
                f"unique_by={unique_by!r} is not a callable or tuple of callables"
            )
        if callable(unique_by):
            unique_by = (unique_by,)
        if len(unique_by) == 0:
            raise InvalidArgument("unique_by is empty")
        for i, f in enumerate(unique_by):
            if not callable(f):
                raise InvalidArgument(f"unique_by[{i}]={f!r} is not a callable")
        # Note that lazy strategies automatically unwrap when passed to a defines_strategy
        # function.
        tuple_suffixes = None
        if (
            # We're generating a list of tuples unique by the first element, perhaps
            # via st.dictionaries(), and this will be more efficient if we rearrange
            # our strategy somewhat to draw the first element then draw add the rest.
            isinstance(elements, TupleStrategy)
            and len(elements.element_strategies) >= 1
            and len(unique_by) == 1
            and (
                # Introspection for either `itemgetter(0)`, or `lambda x: x[0]`
                isinstance(unique_by[0], operator.itemgetter)  # type: ignore
                and repr(unique_by[0]) == "operator.itemgetter(0)"
                or isinstance(unique_by[0], FunctionType)
                and re.fullmatch(
                    get_pretty_function_description(unique_by[0]),
                    r"lambda ([a-z]+): \1\[0\]",
                )
            )
        ):
            unique_by = (identity,)
            tuple_suffixes = TupleStrategy(elements.element_strategies[1:])
            elements = elements.element_strategies[0]

        if isinstance(elements, SampledFromStrategy):
            element_count = len(elements.elements)
            if min_size > element_count:
                raise InvalidArgument(
                    f"Cannot create a collection of min_size={min_size!r} unique "
                    f"elements with values drawn from only {element_count} distinct "
                    "elements"
                )

            if max_size is not None:
                max_size = min(max_size, element_count)
            else:
                max_size = element_count

            return UniqueSampledListStrategy(
                elements=elements,
                max_size=max_size,
                min_size=min_size,
                keys=unique_by,
                tuple_suffixes=tuple_suffixes,
            )

        return UniqueListStrategy(
            elements=elements,
            max_size=max_size,
            min_size=min_size,
            keys=unique_by,
            tuple_suffixes=tuple_suffixes,
        )
    return ListStrategy(elements, min_size=min_size, max_size=max_size)


@cacheable
@defines_strategy()
def sets(
    elements: SearchStrategy[Ex],
    *,
    min_size: int = 0,
    max_size: Optional[int] = None,
) -> SearchStrategy[Set[Ex]]:
    """This has the same behaviour as lists, but returns sets instead.

    Note that Hypothesis cannot tell if values are drawn from elements
    are hashable until running the test, so you can define a strategy
    for sets of an unhashable type but it will fail at test time.

    Examples from this strategy shrink by trying to remove elements from the
    set, and by shrinking each individual element of the set.
    """
    return lists(
        elements=elements, min_size=min_size, max_size=max_size, unique=True
    ).map(set)


@cacheable
@defines_strategy()
def frozensets(
    elements: SearchStrategy[Ex],
    *,
    min_size: int = 0,
    max_size: Optional[int] = None,
) -> SearchStrategy[FrozenSet[Ex]]:
    """This is identical to the sets function but instead returns
    frozensets."""
    return lists(
        elements=elements, min_size=min_size, max_size=max_size, unique=True
    ).map(frozenset)


class PrettyIter:
    def __init__(self, values):
        self._values = values
        self._iter = iter(self._values)

    def __iter__(self):
        return self._iter

    def __next__(self):
        return next(self._iter)

    def __repr__(self):
        return f"iter({self._values!r})"


@defines_strategy()
def iterables(
    elements: SearchStrategy[Ex],
    *,
    min_size: int = 0,
    max_size: Optional[int] = None,
    unique_by: Optional[UniqueBy] = None,
    unique: bool = False,
) -> SearchStrategy[Iterable[Ex]]:
    """This has the same behaviour as lists, but returns iterables instead.

    Some iterables cannot be indexed (e.g. sets) and some do not have a
    fixed length (e.g. generators). This strategy produces iterators,
    which cannot be indexed and do not have a fixed length. This ensures
    that you do not accidentally depend on sequence behaviour.
    """
    return lists(
        elements=elements,
        min_size=min_size,
        max_size=max_size,
        unique_by=unique_by,
        unique=unique,
    ).map(PrettyIter)


@defines_strategy()
def fixed_dictionaries(
    mapping: Dict[T, SearchStrategy[Ex]],
    *,
    optional: Optional[Dict[T, SearchStrategy[Ex]]] = None,
) -> SearchStrategy[Dict[T, Ex]]:
    """Generates a dictionary of the same type as mapping with a fixed set of
    keys mapping to strategies. ``mapping`` must be a dict subclass.

    Generated values have all keys present in mapping, in iteration order,
    with the corresponding values drawn from mapping[key].

    If ``optional`` is passed, the generated value *may or may not* contain each
    key from ``optional`` and a value drawn from the corresponding strategy.
    Generated values may contain optional keys in an arbitrary order.

    Examples from this strategy shrink by shrinking each individual value in
    the generated dictionary, and omitting optional key-value pairs.
    """
    check_type(dict, mapping, "mapping")
    for k, v in mapping.items():
        check_strategy(v, f"mapping[{k!r}]")
    if optional is not None:
        check_type(dict, optional, "optional")
        for k, v in optional.items():
            check_strategy(v, f"optional[{k!r}]")
        if type(mapping) != type(optional):
            raise InvalidArgument(
                "Got arguments of different types: mapping=%s, optional=%s"
                % (nicerepr(type(mapping)), nicerepr(type(optional)))
            )
        if set(mapping) & set(optional):
            raise InvalidArgument(
                "The following keys were in both mapping and optional, "
                "which is invalid: %r" % (set(mapping) & set(optional))
            )
        return FixedAndOptionalKeysDictStrategy(mapping, optional)
    return FixedKeysDictStrategy(mapping)


@cacheable
@defines_strategy()
def dictionaries(
    keys: SearchStrategy[Ex],
    values: SearchStrategy[T],
    *,
    dict_class: type = dict,
    min_size: int = 0,
    max_size: Optional[int] = None,
) -> SearchStrategy[Dict[Ex, T]]:
    # Describing the exact dict_class to Mypy drops the key and value types,
    # so we report Dict[K, V] instead of Mapping[Any, Any] for now.  Sorry!
    """Generates dictionaries of type ``dict_class`` with keys drawn from the ``keys``
    argument and values drawn from the ``values`` argument.

    The size parameters have the same interpretation as for
    :func:`~hypothesis.strategies.lists`.

    Examples from this strategy shrink by trying to remove keys from the
    generated dictionary, and by shrinking each generated key and value.
    """
    check_valid_sizes(min_size, max_size)
    if max_size == 0:
        return fixed_dictionaries(dict_class())
    check_strategy(keys, "keys")
    check_strategy(values, "values")

    return lists(
        tuples(keys, values),
        min_size=min_size,
        max_size=max_size,
        unique_by=operator.itemgetter(0),
    ).map(dict_class)


@cacheable
@defines_strategy(force_reusable_values=True)
def characters(
    *,
    whitelist_categories: Optional[Sequence[str]] = None,
    blacklist_categories: Optional[Sequence[str]] = None,
    blacklist_characters: Optional[Sequence[str]] = None,
    min_codepoint: Optional[int] = None,
    max_codepoint: Optional[int] = None,
    whitelist_characters: Optional[Sequence[str]] = None,
) -> SearchStrategy[str]:
    r"""Generates characters, length-one :class:`python:str`\ ings,
    following specified filtering rules.

    - When no filtering rules are specified, any character can be produced.
    - If ``min_codepoint`` or ``max_codepoint`` is specified, then only
      characters having a codepoint in that range will be produced.
    - If ``whitelist_categories`` is specified, then only characters from those
      Unicode categories will be produced. This is a further restriction,
      characters must also satisfy ``min_codepoint`` and ``max_codepoint``.
    - If ``blacklist_categories`` is specified, then any character from those
      categories will not be produced.  Any overlap between
      ``whitelist_categories`` and ``blacklist_categories`` will raise an
      exception, as each character can only belong to a single class.
    - If ``whitelist_characters`` is specified, then any additional characters
      in that list will also be produced.
    - If ``blacklist_characters`` is specified, then any characters in
      that list will be not be produced. Any overlap between
      ``whitelist_characters`` and ``blacklist_characters`` will raise an
      exception.

    The ``_codepoint`` arguments must be integers between zero and
    :obj:`python:sys.maxunicode`.  The ``_characters`` arguments must be
    collections of length-one unicode strings, such as a unicode string.

    The ``_categories`` arguments must be used to specify either the
    one-letter Unicode major category or the two-letter Unicode
    `general category`_.  For example, ``('Nd', 'Lu')`` signifies "Number,
    decimal digit" and "Letter, uppercase".  A single letter ('major category')
    can be given to match all corresponding categories, for example ``'P'``
    for characters in any punctuation category.

    .. _general category: https://wikipedia.org/wiki/Unicode_character_property

    Examples from this strategy shrink towards the codepoint for ``'0'``,
    or the first allowable codepoint after it if ``'0'`` is excluded.
    """
    check_valid_size(min_codepoint, "min_codepoint")
    check_valid_size(max_codepoint, "max_codepoint")
    check_valid_interval(min_codepoint, max_codepoint, "min_codepoint", "max_codepoint")
    if (
        min_codepoint is None
        and max_codepoint is None
        and whitelist_categories is None
        and blacklist_categories is None
        and whitelist_characters is not None
    ):
        raise InvalidArgument(
            "Nothing is excluded by other arguments, so passing only "
            f"whitelist_characters={whitelist_characters!r} would have no effect.  "
            "Also pass whitelist_categories=(), or use "
            f"sampled_from({whitelist_characters!r}) instead."
        )
    blacklist_characters = blacklist_characters or ""
    whitelist_characters = whitelist_characters or ""
    overlap = set(blacklist_characters).intersection(whitelist_characters)
    if overlap:
        raise InvalidArgument(
            "Characters %r are present in both whitelist_characters=%r, and "
            "blacklist_characters=%r"
            % (sorted(overlap), whitelist_characters, blacklist_characters)
        )
    blacklist_categories = as_general_categories(
        blacklist_categories, "blacklist_categories"
    )
    if (
        whitelist_categories is not None
        and not whitelist_categories
        and not whitelist_characters
    ):
        raise InvalidArgument(
            "When whitelist_categories is an empty collection and there are "
            "no characters specified in whitelist_characters, nothing can "
            "be generated by the characters() strategy."
        )
    whitelist_categories = as_general_categories(
        whitelist_categories, "whitelist_categories"
    )
    both_cats = set(blacklist_categories or ()).intersection(whitelist_categories or ())
    if both_cats:
        raise InvalidArgument(
            "Categories %r are present in both whitelist_categories=%r, and "
            "blacklist_categories=%r"
            % (sorted(both_cats), whitelist_categories, blacklist_categories)
        )

    return OneCharStringStrategy(
        whitelist_categories=whitelist_categories,
        blacklist_categories=blacklist_categories,
        blacklist_characters=blacklist_characters,
        min_codepoint=min_codepoint,
        max_codepoint=max_codepoint,
        whitelist_characters=whitelist_characters,
    )


@cacheable
@defines_strategy(force_reusable_values=True)
def text(
    alphabet: Union[Sequence[str], SearchStrategy[str]] = characters(
        blacklist_categories=("Cs",)
    ),
    *,
    min_size: int = 0,
    max_size: Optional[int] = None,
) -> SearchStrategy[str]:
    """Generates strings with characters drawn from ``alphabet``, which should
    be a collection of length one strings or a strategy generating such strings.

    The default alphabet strategy can generate the full unicode range but
    excludes surrogate characters because they are invalid in the UTF-8
    encoding.  You can use :func:`~hypothesis.strategies.characters` without
    arguments to find surrogate-related bugs such as :bpo:`34454`.

    ``min_size`` and ``max_size`` have the usual interpretations.
    Note that Python measures string length by counting codepoints: U+00C5
    ``Å`` is a single character, while U+0041 U+030A ``Å`` is two - the ``A``,
    and a combining ring above.

    Examples from this strategy shrink towards shorter strings, and with the
    characters in the text shrinking as per the alphabet strategy.
    This strategy does not :func:`~python:unicodedata.normalize` examples,
    so generated strings may be in any or none of the 'normal forms'.
    """
    check_valid_sizes(min_size, max_size)
    if isinstance(alphabet, SearchStrategy):
        char_strategy = alphabet
    else:
        non_string = [c for c in alphabet if not isinstance(c, str)]
        if non_string:
            raise InvalidArgument(
                "The following elements in alphabet are not unicode "
                "strings:  %r" % (non_string,)
            )
        not_one_char = [c for c in alphabet if len(c) != 1]
        if not_one_char:
            raise InvalidArgument(
                "The following elements in alphabet are not of length "
                "one, which leads to violation of size constraints:  %r"
                % (not_one_char,)
            )
        char_strategy = (
            characters(whitelist_categories=(), whitelist_characters=alphabet)
            if alphabet
            else nothing()
        )
    if (max_size == 0 or char_strategy.is_empty) and not min_size:
        return just("")
    return lists(char_strategy, min_size=min_size, max_size=max_size).map("".join)


@cacheable
@defines_strategy()
def from_regex(
    regex: Union[AnyStr, Pattern[AnyStr]], *, fullmatch: bool = False
) -> SearchStrategy[AnyStr]:
    r"""Generates strings that contain a match for the given regex (i.e. ones
    for which :func:`python:re.search` will return a non-None result).

    ``regex`` may be a pattern or :func:`compiled regex <python:re.compile>`.
    Both byte-strings and unicode strings are supported, and will generate
    examples of the same type.

    You can use regex flags such as :obj:`python:re.IGNORECASE` or
    :obj:`python:re.DOTALL` to control generation. Flags can be passed either
    in compiled regex or inside the pattern with a ``(?iLmsux)`` group.

    Some regular expressions are only partly supported - the underlying
    strategy checks local matching and relies on filtering to resolve
    context-dependent expressions.  Using too many of these constructs may
    cause health-check errors as too many examples are filtered out. This
    mainly includes (positive or negative) lookahead and lookbehind groups.

    If you want the generated string to match the whole regex you should use
    boundary markers. So e.g. ``r"\A.\Z"`` will return a single character
    string, while ``"."`` will return any string, and ``r"\A.$"`` will return
    a single character optionally followed by a ``"\n"``.
    Alternatively, passing ``fullmatch=True`` will ensure that the whole
    string is a match, as if you had used the ``\A`` and ``\Z`` markers.

    Examples from this strategy shrink towards shorter strings and lower
    character values, with exact behaviour that may depend on the pattern.
    """
    check_type(bool, fullmatch, "fullmatch")
    # TODO: We would like to move this to the top level, but pending some major
    # refactoring it's hard to do without creating circular imports.
    from hypothesis.strategies._internal.regex import regex_strategy

    return regex_strategy(regex, fullmatch)


@cacheable
@defines_strategy(force_reusable_values=True)
def binary(
    *,
    min_size: int = 0,
    max_size: Optional[int] = None,
) -> SearchStrategy[bytes]:
    """Generates :class:`python:bytes`.

    The generated :class:`python:bytes` will have a length of at least ``min_size``
    and at most ``max_size``.  If ``max_size`` is None there is no upper limit.

    Examples from this strategy shrink towards smaller strings and lower byte
    values.
    """
    check_valid_sizes(min_size, max_size)
    if min_size == max_size:
        return FixedSizeBytes(min_size)
    return lists(
        integers(min_value=0, max_value=255), min_size=min_size, max_size=max_size
    ).map(bytes)


@cacheable
@defines_strategy()
def randoms(
    *,
    note_method_calls: bool = False,
    use_true_random: bool = False,
) -> SearchStrategy[random.Random]:
    """Generates instances of ``random.Random``. The generated Random instances
    are of a special HypothesisRandom subclass.

    - If ``note_method_calls`` is set to ``True``, Hypothesis will print the
      randomly drawn values in any falsifying test case. This can be helpful
      for debugging the behaviour of randomized algorithms.
    - If ``use_true_random`` is set to ``True`` then values will be drawn from
      their usual distribution, otherwise they will actually be Hypothesis
      generated values (and will be shrunk accordingly for any failing test
      case). Setting ``use_true_random=False`` will tend to expose bugs that
      would occur with very low probability when it is set to True, and this
      flag should only be set to True when your code relies on the distribution
      of values for correctness.
    """
    check_type(bool, note_method_calls, "note_method_calls")
    check_type(bool, use_true_random, "use_true_random")

    from hypothesis.strategies._internal.random import RandomStrategy

    return RandomStrategy(
        use_true_random=use_true_random, note_method_calls=note_method_calls
    )


class RandomSeeder:
    def __init__(self, seed):
        self.seed = seed

    def __repr__(self):
        return f"RandomSeeder({self.seed!r})"


class RandomModule(SearchStrategy):
    def do_draw(self, data):
        seed = data.draw(integers(0, 2 ** 32 - 1))
        seed_all, restore_all = get_seeder_and_restorer(seed)
        seed_all()
        cleanup(restore_all)
        return RandomSeeder(seed)


@cacheable
@defines_strategy()
def random_module() -> SearchStrategy[RandomSeeder]:
    """The Hypothesis engine handles PRNG state for the stdlib and Numpy random
    modules internally, always seeding them to zero and restoring the previous
    state after the test.

    If having a fixed seed would unacceptably weaken your tests, and you
    cannot use a ``random.Random`` instance provided by
    :func:`~hypothesis.strategies.randoms`, this strategy calls
    :func:`python:random.seed` with an arbitrary integer and passes you
    an opaque object whose repr displays the seed value for debugging.
    If ``numpy.random`` is available, that state is also managed.

    Examples from these strategy shrink to seeds closer to zero.
    """
    return shared(RandomModule(), key="hypothesis.strategies.random_module()")


class BuildsStrategy(SearchStrategy):
    def __init__(self, target, args, kwargs):
        self.target = target
        self.args = args
        self.kwargs = kwargs

    def do_draw(self, data):
        try:
            return self.target(
                *(data.draw(a) for a in self.args),
                **{k: data.draw(v) for k, v in self.kwargs.items()},
            )
        except TypeError as err:
            if (
                isinstance(self.target, type)
                and issubclass(self.target, enum.Enum)
                and not (self.args or self.kwargs)
            ):
                name = self.target.__module__ + "." + self.target.__qualname__
                raise InvalidArgument(
                    f"Calling {name} with no arguments raised an error - "
                    f"try using sampled_from({name}) instead of builds({name})"
                ) from err
            if not (self.args or self.kwargs):
                from .types import is_a_new_type, is_generic_type

                if is_a_new_type(self.target) or is_generic_type(self.target):
                    raise InvalidArgument(
                        f"Calling {self.target!r} with no arguments raised an "
                        f"error - try using from_type({self.target!r}) instead "
                        f"of builds({self.target!r})"
                    ) from err
            raise

    def validate(self):
        tuples(*self.args).validate()
        fixed_dictionaries(self.kwargs).validate()


# The ideal signature builds(target, /, *args, **kwargs) is unfortunately a
# SyntaxError before Python 3.8 so we emulate it with manual argument unpacking.
# Note that for the benefit of documentation and introspection tools, we set the
# __signature__ attribute to show the semantic rather than actual signature.
@cacheable
@defines_strategy()
def builds(
    *callable_and_args: Union[Callable[..., Ex], SearchStrategy[Any]],
    **kwargs: Union[SearchStrategy[Any], InferType],
) -> SearchStrategy[Ex]:
    """Generates values by drawing from ``args`` and ``kwargs`` and passing
    them to the callable (provided as the first positional argument) in the
    appropriate argument position.

    e.g. ``builds(target, integers(), flag=booleans())`` would draw an
    integer ``i`` and a boolean ``b`` and call ``target(i, flag=b)``.

    If the callable has type annotations, they will be used to infer a strategy
    for required arguments that were not passed to builds.  You can also tell
    builds to infer a strategy for an optional argument by passing the special
    value :const:`hypothesis.infer` as a keyword argument to
    builds, instead of a strategy for that argument to the callable.

    If the callable is a class defined with :pypi:`attrs`, missing required
    arguments will be inferred from the attribute on a best-effort basis,
    e.g. by checking :ref:`attrs standard validators <attrs:api_validators>`.
    Dataclasses are handled natively by the inference from type hints.

    Examples from this strategy shrink by shrinking the argument values to
    the callable.
    """
    if not callable_and_args:
        raise InvalidArgument(
            "builds() must be passed a callable as the first positional "
            "argument, but no positional arguments were given."
        )
    target, args = callable_and_args[0], callable_and_args[1:]
    if not callable(target):
        raise InvalidArgument(
            "The first positional argument to builds() must be a callable "
            "target to construct."
        )

    if infer in args:
        # Avoid an implementation nightmare juggling tuples and worse things
        raise InvalidArgument(
            "infer was passed as a positional argument to "
            "builds(), but is only allowed as a keyword arg"
        )
    required = required_args(target, args, kwargs)
    to_infer = {k for k, v in kwargs.items() if v is infer}
    if required or to_infer:
        if isinstance(target, type) and attr.has(target):
            # Use our custom introspection for attrs classes
            from hypothesis.strategies._internal.attrs import from_attrs

            return from_attrs(target, args, kwargs, required | to_infer)
        # Otherwise, try using type hints
        hints = get_type_hints(target)
        if to_infer - set(hints):
            raise InvalidArgument(
                "passed infer for %s, but there is no type annotation"
                % (", ".join(sorted(to_infer - set(hints))))
            )
        for kw in set(hints) & (required | to_infer):
            kwargs[kw] = from_type(hints[kw])

    # Mypy doesn't realise that `infer` is gone from kwargs now
    # and thinks that target and args have the same (union) type.
    return BuildsStrategy(target, args, kwargs)


if sys.version_info[:2] >= (3, 8):  # pragma: no cover
    # See notes above definition - this signature is compatible and better
    # matches the semantics of the function.  Great for documentation!
    sig = signature(builds)
    args, kwargs = sig.parameters.values()
    builds.__signature__ = sig.replace(
        parameters=[
            Parameter(
                name="target",
                kind=Parameter.POSITIONAL_ONLY,
                annotation=Callable[..., Ex],
            ),
            args.replace(name="args", annotation=SearchStrategy[Any]),
            kwargs,
        ]
    )


@cacheable
@defines_strategy(never_lazy=True)
def from_type(thing: Type[Ex]) -> SearchStrategy[Ex]:
    """Looks up the appropriate search strategy for the given type.

    ``from_type`` is used internally to fill in missing arguments to
    :func:`~hypothesis.strategies.builds` and can be used interactively
    to explore what strategies are available or to debug type resolution.

    You can use :func:`~hypothesis.strategies.register_type_strategy` to
    handle your custom types, or to globally redefine certain strategies -
    for example excluding NaN from floats, or use timezone-aware instead of
    naive time and datetime strategies.

    The resolution logic may be changed in a future version, but currently
    tries these five options:

    1. If ``thing`` is in the default lookup mapping or user-registered lookup,
       return the corresponding strategy.  The default lookup covers all types
       with Hypothesis strategies, including extras where possible.
    2. If ``thing`` is from the :mod:`python:typing` module, return the
       corresponding strategy (special logic).
    3. If ``thing`` has one or more subtypes in the merged lookup, return
       the union of the strategies for those types that are not subtypes of
       other elements in the lookup.
    4. Finally, if ``thing`` has type annotations for all required arguments,
       and is not an abstract class, it is resolved via
       :func:`~hypothesis.strategies.builds`.
    5. Because :mod:`abstract types <python:abc>` cannot be instantiated,
       we treat abstract types as the union of their concrete subclasses.
       Note that this lookup works via inheritance but not via
       :obj:`~python:abc.ABCMeta.register`, so you may still need to use
       :func:`~hypothesis.strategies.register_type_strategy`.

    There is a valuable recipe for leveraging ``from_type()`` to generate
    "everything except" values from a specified type. I.e.

    .. code-block:: python

        def everything_except(excluded_types):
            return (
                from_type(type)
                .flatmap(from_type)
                .filter(lambda x: not isinstance(x, excluded_types))
            )

    For example, ``everything_except(int)`` returns a strategy that can
    generate anything that ``from_type()`` can ever generate, except for
    instances of :class:`python:int`, and excluding instances of types
    added via :func:`~hypothesis.strategies.register_type_strategy`.

    This is useful when writing tests which check that invalid input is
    rejected in a certain way.
    """
    # This tricky little dance is because we want to show the repr of the actual
    # underlying strategy wherever possible, as a form of user education, but
    # would prefer to fall back to the default "from_type(...)" repr instead of
    # "deferred(...)" for recursive types or invalid arguments.
    try:
        return _from_type(thing)
    except Exception:
        return LazyStrategy(
            lambda thing: deferred(lambda: _from_type(thing)),
            (thing,),
            {},
            force_repr=f"from_type({thing!r})",
        )


def _from_type(thing: Type[Ex]) -> SearchStrategy[Ex]:
    # TODO: We would like to move this to the top level, but pending some major
    # refactoring it's hard to do without creating circular imports.
    from hypothesis.strategies._internal import types

    def as_strategy(strat_or_callable, thing, final=True):
        # User-provided strategies need some validation, and callables even more
        # of it.  We do this in three places, hence the helper function
        if not isinstance(strat_or_callable, SearchStrategy):
            assert callable(strat_or_callable)  # Validated in register_type_strategy
            try:
                # On Python 3.6, typing.Hashable is just an alias for abc.Hashable,
                # and the resolver function for Type throws an AttributeError because
                # Hashable has no __args__.  We discard such errors when attempting
                # to resolve subclasses, because the function was passed a weird arg.
                strategy = strat_or_callable(thing)
            except Exception:  # pragma: no cover
                if not final:
                    return nothing()
                raise
        else:
            strategy = strat_or_callable
        if not isinstance(strategy, SearchStrategy):
            raise ResolutionFailed(
                "Error: %s was registered for %r, but returned non-strategy %r"
                % (thing, nicerepr(strat_or_callable), strategy)
            )
        if strategy.is_empty:
            raise ResolutionFailed(f"Error: {thing!r} resolved to an empty strategy")
        return strategy

    if not isinstance(thing, type):
        if types.is_a_new_type(thing):
            # Check if we have an explicitly registered strategy for this thing,
            # resolve it so, and otherwise resolve as for the base type.
            if thing in types._global_type_lookup:
                return as_strategy(types._global_type_lookup[thing], thing)
            return from_type(thing.__supertype__)
        # Under Python 3.6, Unions are not instances of `type` - but we
        # still want to resolve them!
        if getattr(thing, "__origin__", None) is typing.Union:
            args = sorted(thing.__args__, key=types.type_sorting_key)
            return one_of([from_type(t) for t in args])
    if not types.is_a_type(thing):
        # The implementation of typing_extensions.Literal under Python 3.6 is
        # *very strange*.  Notably, `type(Literal[x]) != Literal` so we have to
        # use the first form directly, and because it uses __values__ instead of
        # __args__ we inline the relevant logic here until the end of life date.
        if types.is_typing_literal(thing):  # pragma: no cover
            assert sys.version_info[:2] == (3, 6)
            args_dfs_stack = list(thing.__values__)  # type: ignore
            literals = []
            while args_dfs_stack:
                arg = args_dfs_stack.pop()
                if types.is_typing_literal(arg):
                    args_dfs_stack.extend(reversed(arg.__values__))
                else:
                    literals.append(arg)
            return sampled_from(literals)
        raise InvalidArgument(f"thing={thing} must be a type")
    # Now that we know `thing` is a type, the first step is to check for an
    # explicitly registered strategy.  This is the best (and hopefully most
    # common) way to resolve a type to a strategy.  Note that the value in the
    # lookup may be a strategy or a function from type -> strategy; and we
    # convert empty results into an explicit error.
    try:
        if thing in types._global_type_lookup:
            return as_strategy(types._global_type_lookup[thing], thing)
    except TypeError:  # pragma: no cover
        # This is due to a bizarre divergence in behaviour under Python 3.9.0:
        # typing.Callable[[], foo] has __args__ = (foo,) but collections.abc.Callable
        # has __args__ = ([], foo); and as a result is non-hashable.
        pass
    if (
        hasattr(typing, "_TypedDictMeta")
        and type(thing) is typing._TypedDictMeta  # type: ignore
        or hasattr(types.typing_extensions, "_TypedDictMeta")  # type: ignore
        and type(thing) is types.typing_extensions._TypedDictMeta  # type: ignore
    ):  # pragma: no cover
        # The __optional_keys__ attribute may or may not be present, but if there's no
        # way to tell and we just have to assume that everything is required.
        # See https://github.com/python/cpython/pull/17214 for details.
        optional = getattr(thing, "__optional_keys__", ())
        anns = {k: from_type(v) for k, v in thing.__annotations__.items()}
        return fixed_dictionaries(  # type: ignore
            mapping={k: v for k, v in anns.items() if k not in optional},
            optional={k: v for k, v in anns.items() if k in optional},
        )
    # We also have a special case for TypeVars.
    # They are represented as instances like `~T` when they come here.
    # We need to work with their type instead.
    if isinstance(thing, TypeVar) and type(thing) in types._global_type_lookup:
        return as_strategy(types._global_type_lookup[type(thing)], thing)
    # If there's no explicitly registered strategy, maybe a subtype of thing
    # is registered - if so, we can resolve it to the subclass strategy.
    # We'll start by checking if thing is from from the typing module,
    # because there are several special cases that don't play well with
    # subclass and instance checks.
    if isinstance(thing, typing_root_type) or (
        sys.version_info[:2] >= (3, 9)
        and isinstance(getattr(thing, "__origin__", None), type)
        and getattr(thing, "__args__", None)
    ):
        return types.from_typing_type(thing)
    # If it's not from the typing module, we get all registered types that are
    # a subclass of `thing` and are not themselves a subtype of any other such
    # type.  For example, `Number -> integers() | floats()`, but bools() is
    # not included because bool is a subclass of int as well as Number.
    strategies = [
        as_strategy(v, thing, final=False)
        for k, v in sorted(types._global_type_lookup.items(), key=repr)
        if isinstance(k, type)
        and issubclass(k, thing)
        and sum(types.try_issubclass(k, typ) for typ in types._global_type_lookup) == 1
    ]
    if any(not s.is_empty for s in strategies):
        return one_of(strategies)
    # If we don't have a strategy registered for this type or any subtype, we
    # may be able to fall back on type annotations.
    if issubclass(thing, enum.Enum):
        return sampled_from(thing)

    # Finally, try to build an instance by calling the type object.  Unlike builds(),
    # this block *does* try to infer strategies for arguments with default values.
    # That's because of the semantic different; builds() -> "call this with ..."
    # so we only infer when *not* doing so would be an error; from_type() -> "give
    # me arbitrary instances" so the greater variety is acceptable.
    # And if it's *too* varied, express your opinions with register_type_strategy()
    if not isabstract(thing):
        # If we know that builds(thing) will fail, give a better error message
        required = required_args(thing)
        if required and not (
            required.issubset(get_type_hints(thing))
            or attr.has(thing)
            or is_typed_named_tuple(thing)  # weird enough that we have a specific check
        ):
            raise ResolutionFailed(
                f"Could not resolve {thing!r} to a strategy; consider "
                "using register_type_strategy"
            )
        try:
            hints = get_type_hints(thing)
            params = signature(thing).parameters
        except Exception:
            return builds(thing)
        kwargs = {}
        for k, p in params.items():
            if (
                k in hints
                and k != "return"
                and p.default is not Parameter.empty
                and p.kind in (Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY)
            ):
                kwargs[k] = just(p.default) | _from_type(hints[k])
        return builds(thing, **kwargs)
    # And if it's an abstract type, we'll resolve to a union of subclasses instead.
    subclasses = thing.__subclasses__()
    if not subclasses:
        raise ResolutionFailed(
            f"Could not resolve {thing!r} to a strategy, because it is an abstract "
            "type without any subclasses. Consider using register_type_strategy"
        )
    subclass_strategies = nothing()
    for sc in subclasses:
        try:
            subclass_strategies |= _from_type(sc)
        except Exception:
            pass
    if subclass_strategies.is_empty:
        # We're unable to resolve subclasses now, but we might be able to later -
        # so we'll just go back to the mixed distribution.
        return sampled_from(subclasses).flatmap(from_type)
    return subclass_strategies


@cacheable
@defines_strategy(force_reusable_values=True)
def fractions(
    min_value: Optional[Union[Real, str]] = None,
    max_value: Optional[Union[Real, str]] = None,
    *,
    max_denominator: Optional[int] = None,
) -> SearchStrategy[Fraction]:
    """Returns a strategy which generates Fractions.

    If ``min_value`` is not None then all generated values are no less than
    ``min_value``.  If ``max_value`` is not None then all generated values are no
    greater than ``max_value``.  ``min_value`` and ``max_value`` may be anything accepted
    by the :class:`~fractions.Fraction` constructor.

    If ``max_denominator`` is not None then the denominator of any generated
    values is no greater than ``max_denominator``. Note that ``max_denominator`` must
    be None or a positive integer.

    Examples from this strategy shrink towards smaller denominators, then
    closer to zero.
    """
    min_value = try_convert(Fraction, min_value, "min_value")
    max_value = try_convert(Fraction, max_value, "max_value")
    # These assertions tell Mypy what happened in try_convert
    assert min_value is None or isinstance(min_value, Fraction)
    assert max_value is None or isinstance(max_value, Fraction)

    check_valid_interval(min_value, max_value, "min_value", "max_value")
    check_valid_integer(max_denominator, "max_denominator")

    if max_denominator is not None:
        if max_denominator < 1:
            raise InvalidArgument("max_denominator=%r must be >= 1" % max_denominator)
        if min_value is not None and min_value.denominator > max_denominator:
            raise InvalidArgument(
                "The min_value=%r has a denominator greater than the "
                "max_denominator=%r" % (min_value, max_denominator)
            )
        if max_value is not None and max_value.denominator > max_denominator:
            raise InvalidArgument(
                "The max_value=%r has a denominator greater than the "
                "max_denominator=%r" % (max_value, max_denominator)
            )

    if min_value is not None and min_value == max_value:
        return just(min_value)

    def dm_func(denom):
        """Take denom, construct numerator strategy, and build fraction."""
        # Four cases of algebra to get integer bounds and scale factor.
        min_num, max_num = None, None
        if max_value is None and min_value is None:
            pass
        elif min_value is None:
            max_num = denom * max_value.numerator
            denom *= max_value.denominator
        elif max_value is None:
            min_num = denom * min_value.numerator
            denom *= min_value.denominator
        else:
            low = min_value.numerator * max_value.denominator
            high = max_value.numerator * min_value.denominator
            scale = min_value.denominator * max_value.denominator
            # After calculating our integer bounds and scale factor, we remove
            # the gcd to avoid drawing more bytes for the example than needed.
            # Note that `div` can be at most equal to `scale`.
            div = math.gcd(scale, math.gcd(low, high))
            min_num = denom * low // div
            max_num = denom * high // div
            denom *= scale // div

        return builds(
            Fraction, integers(min_value=min_num, max_value=max_num), just(denom)
        )

    if max_denominator is None:
        return integers(min_value=1).flatmap(dm_func)

    return (
        integers(1, max_denominator)
        .flatmap(dm_func)
        .map(lambda f: f.limit_denominator(max_denominator))
    )


def _as_finite_decimal(
    value: Union[Real, str, None], name: str, allow_infinity: Optional[bool]
) -> Optional[Decimal]:
    """Convert decimal bounds to decimals, carefully."""
    assert name in ("min_value", "max_value")
    if value is None:
        return None
    if not isinstance(value, Decimal):
        with localcontext(Context()):  # ensure that default traps are enabled
            value = try_convert(Decimal, value, name)
    assert isinstance(value, Decimal)
    if value.is_finite():
        return value
    if value.is_infinite() and (value < 0 if "min" in name else value > 0):
        if allow_infinity or allow_infinity is None:
            return None
        raise InvalidArgument(
            f"allow_infinity={allow_infinity!r}, but {name}={value!r}"
        )
    # This could be infinity, quiet NaN, or signalling NaN
    raise InvalidArgument(f"Invalid {name}={value!r}")


@cacheable
@defines_strategy(force_reusable_values=True)
def decimals(
    min_value: Optional[Union[Real, str]] = None,
    max_value: Optional[Union[Real, str]] = None,
    *,
    allow_nan: Optional[bool] = None,
    allow_infinity: Optional[bool] = None,
    places: Optional[int] = None,
) -> SearchStrategy[Decimal]:
    """Generates instances of :class:`python:decimal.Decimal`, which may be:

    - A finite rational number, between ``min_value`` and ``max_value``.
    - Not a Number, if ``allow_nan`` is True.  None means "allow NaN, unless
      ``min_value`` and ``max_value`` are not None".
    - Positive or negative infinity, if ``max_value`` and ``min_value``
      respectively are None, and ``allow_infinity`` is not False.  None means
      "allow infinity, unless excluded by the min and max values".

    Note that where floats have one ``NaN`` value, Decimals have four: signed,
    and either *quiet* or *signalling*.  See `the decimal module docs
    <https://docs.python.org/3/library/decimal.html#special-values>`_ for
    more information on special values.

    If ``places`` is not None, all finite values drawn from the strategy will
    have that number of digits after the decimal place.

    Examples from this strategy do not have a well defined shrink order but
    try to maximize human readability when shrinking.
    """
    # Convert min_value and max_value to Decimal values, and validate args
    check_valid_integer(places, "places")
    if places is not None and places < 0:
        raise InvalidArgument("places=%r may not be negative" % places)
    min_value = _as_finite_decimal(min_value, "min_value", allow_infinity)
    max_value = _as_finite_decimal(max_value, "max_value", allow_infinity)
    check_valid_interval(min_value, max_value, "min_value", "max_value")
    if allow_infinity and (None not in (min_value, max_value)):
        raise InvalidArgument("Cannot allow infinity between finite bounds")
    # Set up a strategy for finite decimals.  Note that both floating and
    # fixed-point decimals require careful handling to remain isolated from
    # any external precision context - in short, we always work out the
    # required precision for lossless operation and use context methods.
    if places is not None:
        # Fixed-point decimals are basically integers with a scale factor
        def ctx(val):
            """Return a context in which this value is lossless."""
            precision = ceil(math.log10(abs(val) or 1)) + places + 1
            return Context(prec=max([precision, 1]))

        def int_to_decimal(val):
            context = ctx(val)
            return context.quantize(context.multiply(val, factor), factor)

        factor = Decimal(10) ** -places
        min_num, max_num = None, None
        if min_value is not None:
            min_num = ceil(ctx(min_value).divide(min_value, factor))
        if max_value is not None:
            max_num = floor(ctx(max_value).divide(max_value, factor))
        if min_num is not None and max_num is not None and min_num > max_num:
            raise InvalidArgument(
                f"There are no decimals with {places} places between "
                f"min_value={min_value!r} and max_value={max_value!r}"
            )
        strat = integers(min_num, max_num).map(int_to_decimal)
    else:
        # Otherwise, they're like fractions featuring a power of ten
        def fraction_to_decimal(val):
            precision = (
                ceil(math.log10(abs(val.numerator) or 1) + math.log10(val.denominator))
                + 1
            )
            return Context(prec=precision or 1).divide(
                Decimal(val.numerator), val.denominator
            )

        strat = fractions(min_value, max_value).map(fraction_to_decimal)
    # Compose with sampled_from for infinities and NaNs as appropriate
    special: List[Decimal] = []
    if allow_nan or (allow_nan is None and (None in (min_value, max_value))):
        special.extend(map(Decimal, ("NaN", "-NaN", "sNaN", "-sNaN")))
    if allow_infinity or (allow_infinity is max_value is None):
        special.append(Decimal("Infinity"))
    if allow_infinity or (allow_infinity is min_value is None):
        special.append(Decimal("-Infinity"))
    return strat | (sampled_from(special) if special else nothing())


@defines_strategy(never_lazy=True)
def recursive(
    base: SearchStrategy[Ex],
    extend: Callable[[SearchStrategy[Any]], SearchStrategy[T]],
    *,
    max_leaves: int = 100,
) -> SearchStrategy[Union[T, Ex]]:
    """base: A strategy to start from.

    extend: A function which takes a strategy and returns a new strategy.

    max_leaves: The maximum number of elements to be drawn from base on a given
    run.

    This returns a strategy ``S`` such that ``S = extend(base | S)``. That is,
    values may be drawn from base, or from any strategy reachable by mixing
    applications of | and extend.

    An example may clarify: ``recursive(booleans(), lists)`` would return a
    strategy that may return arbitrarily nested and mixed lists of booleans.
    So e.g. ``False``, ``[True]``, ``[False, []]``, and ``[[[[True]]]]`` are
    all valid values to be drawn from that strategy.

    Examples from this strategy shrink by trying to reduce the amount of
    recursion and by shrinking according to the shrinking behaviour of base
    and the result of extend.

    """

    return RecursiveStrategy(base, extend, max_leaves)


class PermutationStrategy(SearchStrategy):
    def __init__(self, values):
        self.values = values

    def do_draw(self, data):
        # Reversed Fisher-Yates shuffle: swap each element with itself or with
        # a later element.  This shrinks i==j for each element, i.e. to no
        # change.  We don't consider the last element as it's always a no-op.
        result = list(self.values)
        for i in range(len(result) - 1):
            j = integer_range(data, i, len(result) - 1)
            result[i], result[j] = result[j], result[i]
        return result


@defines_strategy()
def permutations(values: Sequence[T]) -> SearchStrategy[List[T]]:
    """Return a strategy which returns permutations of the ordered collection
    ``values``.

    Examples from this strategy shrink by trying to become closer to the
    original order of values.
    """
    values = check_sample(values, "permutations")
    if not values:
        return builds(list)

    return PermutationStrategy(values)


class CompositeStrategy(SearchStrategy):
    def __init__(self, definition, args, kwargs):
        self.definition = definition
        self.args = args
        self.kwargs = kwargs

    def do_draw(self, data):
        return self.definition(data.draw, *self.args, **self.kwargs)

    def calc_label(self):
        return calc_label_from_cls(self.definition)


@cacheable
def composite(f: Callable[..., Ex]) -> Callable[..., SearchStrategy[Ex]]:
    """Defines a strategy that is built out of potentially arbitrarily many
    other strategies.

    This is intended to be used as a decorator. See
    :ref:`the full documentation for more details <composite-strategies>`
    about how to use this function.

    Examples from this strategy shrink by shrinking the output of each draw
    call.
    """
    if isinstance(f, (classmethod, staticmethod)):
        special_method = type(f)
        f = f.__func__
    else:
        special_method = None

    argspec = getfullargspec(f)

    if argspec.defaults is not None and len(argspec.defaults) == len(argspec.args):
        raise InvalidArgument("A default value for initial argument will never be used")
    if len(argspec.args) == 0 and not argspec.varargs:
        raise InvalidArgument(
            "Functions wrapped with composite must take at least one "
            "positional argument."
        )

    annots = {
        k: v
        for k, v in argspec.annotations.items()
        if k in (argspec.args + argspec.kwonlyargs + ["return"])
    }
    new_argspec = argspec._replace(args=argspec.args[1:], annotations=annots)

    @defines_strategy()
    @define_function_signature(f.__name__, f.__doc__, new_argspec)
    def accept(*args, **kwargs):
        return CompositeStrategy(f, args, kwargs)

    accept.__module__ = f.__module__
    if special_method is not None:
        return special_method(accept)
    return accept


@defines_strategy(force_reusable_values=True)
@cacheable
def complex_numbers(
    *,
    min_magnitude: Real = 0,
    max_magnitude: Optional[Real] = None,
    allow_infinity: Optional[bool] = None,
    allow_nan: Optional[bool] = None,
) -> SearchStrategy[complex]:
    """Returns a strategy that generates complex numbers.

    This strategy draws complex numbers with constrained magnitudes.
    The ``min_magnitude`` and ``max_magnitude`` parameters should be
    non-negative :class:`~python:numbers.Real` numbers; a value
    of ``None`` corresponds an infinite upper bound.

    If ``min_magnitude`` is nonzero or ``max_magnitude`` is finite, it
    is an error to enable ``allow_nan``.  If ``max_magnitude`` is finite,
    it is an error to enable ``allow_infinity``.

    The magnitude constraints are respected up to a relative error
    of (around) floating-point epsilon, due to implementation via
    the system ``sqrt`` function.

    Examples from this strategy shrink by shrinking their real and
    imaginary parts, as :func:`~hypothesis.strategies.floats`.

    If you need to generate complex numbers with particular real and
    imaginary parts or relationships between parts, consider using
    :func:`builds(complex, ...) <hypothesis.strategies.builds>` or
    :func:`@composite <hypothesis.strategies.composite>` respectively.
    """
    check_valid_magnitude(min_magnitude, "min_magnitude")
    check_valid_magnitude(max_magnitude, "max_magnitude")
    check_valid_interval(min_magnitude, max_magnitude, "min_magnitude", "max_magnitude")
    if max_magnitude == math.inf:
        max_magnitude = None

    if allow_infinity is None:
        allow_infinity = bool(max_magnitude is None)
    elif allow_infinity and max_magnitude is not None:
        raise InvalidArgument(
            "Cannot have allow_infinity=%r with max_magnitude=%r"
            % (allow_infinity, max_magnitude)
        )
    if allow_nan is None:
        allow_nan = bool(min_magnitude == 0 and max_magnitude is None)
    elif allow_nan and not (min_magnitude == 0 and max_magnitude is None):
        raise InvalidArgument(
            "Cannot have allow_nan=%r, min_magnitude=%r max_magnitude=%r"
            % (allow_nan, min_magnitude, max_magnitude)
        )
    allow_kw = {"allow_nan": allow_nan, "allow_infinity": allow_infinity}

    if min_magnitude == 0 and max_magnitude is None:
        # In this simple but common case, there are no constraints on the
        # magnitude and therefore no relationship between the real and
        # imaginary parts.
        return builds(complex, floats(**allow_kw), floats(**allow_kw))

    @composite
    def constrained_complex(draw):
        # Draw the imaginary part, and determine the maximum real part given
        # this and the max_magnitude
        if max_magnitude is None:
            zi = draw(floats(**allow_kw))
            rmax = None
        else:
            zi = draw(floats(-max_magnitude, max_magnitude, **allow_kw))
            rmax = cathetus(max_magnitude, zi)
        # Draw the real part from the allowed range given the imaginary part
        if min_magnitude == 0 or math.fabs(zi) >= min_magnitude:
            zr = draw(floats(None if rmax is None else -rmax, rmax, **allow_kw))
        else:
            zr = draw(floats(cathetus(min_magnitude, zi), rmax, **allow_kw))
        # Order of conditions carefully tuned so that for a given pair of
        # magnitude arguments, we always either draw or do not draw the bool
        # (crucial for good shrinking behaviour) but only invert when needed.
        if min_magnitude > 0 and draw(booleans()) and math.fabs(zi) <= min_magnitude:
            zr = -zr
        return complex(zr, zi)

    return constrained_complex()


@defines_strategy(never_lazy=True)
def shared(
    base: SearchStrategy[Ex],
    *,
    key: Optional[Hashable] = None,
) -> SearchStrategy[Ex]:
    """Returns a strategy that draws a single shared value per run, drawn from
    base. Any two shared instances with the same key will share the same value,
    otherwise the identity of this strategy will be used. That is:

    >>> s = integers()  # or any other strategy
    >>> x = shared(s)
    >>> y = shared(s)

    In the above x and y may draw different (or potentially the same) values.
    In the following they will always draw the same:

    >>> x = shared(s, key="hi")
    >>> y = shared(s, key="hi")

    Examples from this strategy shrink as per their base strategy.
    """
    return SharedStrategy(base, key)


@cacheable
@defines_strategy(force_reusable_values=True)
def uuids(*, version: Optional[int] = None) -> SearchStrategy[UUID]:
    """Returns a strategy that generates :class:`UUIDs <uuid.UUID>`.

    If the optional version argument is given, value is passed through
    to :class:`~python:uuid.UUID` and only UUIDs of that version will
    be generated.

    All returned values from this will be unique, so e.g. if you do
    ``lists(uuids())`` the resulting list will never contain duplicates.

    Examples from this strategy don't have any meaningful shrink order.
    """
    if version not in (None, 1, 2, 3, 4, 5):
        raise InvalidArgument(
            (
                "version=%r, but version must be in (None, 1, 2, 3, 4, 5) "
                "to pass to the uuid.UUID constructor."
            )
            % (version,)
        )
    return shared(
        randoms(use_true_random=True), key="hypothesis.strategies.uuids.generator"
    ).map(lambda r: UUID(version=version, int=r.getrandbits(128)))


class RunnerStrategy(SearchStrategy):
    def __init__(self, default):
        self.default = default

    def do_draw(self, data):
        runner = getattr(data, "hypothesis_runner", not_set)
        if runner is not_set:
            if self.default is not_set:
                raise InvalidArgument(
                    "Cannot use runner() strategy with no "
                    "associated runner or explicit default."
                )
            else:
                return self.default
        else:
            return runner


@defines_strategy(force_reusable_values=True)
def runner(*, default: Any = not_set) -> SearchStrategy[Any]:
    """A strategy for getting "the current test runner", whatever that may be.
    The exact meaning depends on the entry point, but it will usually be the
    associated 'self' value for it.

    If there is no current test runner and a default is provided, return
    that default. If no default is provided, raises InvalidArgument.

    Examples from this strategy do not shrink (because there is only one).
    """
    return RunnerStrategy(default)


class DataObject:
    """This type only exists so that you can write type hints for tests using
    the :func:`~hypothesis.strategies.data` strategy.  Do not use it directly!
    """

    # Note that "only exists" here really means "is only exported to users",
    # but we want to treat it as "semi-stable", not document it as "public API".

    def __init__(self, data):
        self.count = 0
        self.conjecture_data = data

    def __repr__(self):
        return "data(...)"

    def draw(self, strategy: SearchStrategy[Ex], label: Any = None) -> Ex:
        check_strategy(strategy, "strategy")
        result = self.conjecture_data.draw(strategy)
        self.count += 1
        if label is not None:
            note(f"Draw {self.count} ({label}): {result!r}")
        else:
            note(f"Draw {self.count}: {result!r}")
        return result


class DataStrategy(SearchStrategy):
    supports_find = False

    def do_draw(self, data):
        if not hasattr(data, "hypothesis_shared_data_strategy"):
            data.hypothesis_shared_data_strategy = DataObject(data)
        return data.hypothesis_shared_data_strategy

    def __repr__(self):
        return "data()"

    def map(self, f):
        self.__not_a_first_class_strategy("map")

    def filter(self, f):
        self.__not_a_first_class_strategy("filter")

    def flatmap(self, f):
        self.__not_a_first_class_strategy("flatmap")

    def example(self):
        self.__not_a_first_class_strategy("example")

    def __not_a_first_class_strategy(self, name):
        raise InvalidArgument(
            "Cannot call %s on a DataStrategy. You should probably be using "
            "@composite for whatever it is you're trying to do." % (name,)
        )


@cacheable
@defines_strategy(never_lazy=True)
def data() -> SearchStrategy[DataObject]:
    """This isn't really a normal strategy, but instead gives you an object
    which can be used to draw data interactively from other strategies.

    See :ref:`the rest of the documentation <interactive-draw>` for more
    complete information.

    Examples from this strategy do not shrink (because there is only one),
    but the result of calls to each draw() call shrink as they normally would.
    """
    return DataStrategy()


def register_type_strategy(
    custom_type: Type[Ex],
    strategy: Union[SearchStrategy[Ex], Callable[[Type[Ex]], SearchStrategy[Ex]]],
) -> None:
    """Add an entry to the global type-to-strategy lookup.

    This lookup is used in :func:`~hypothesis.strategies.builds` and
    :func:`@given <hypothesis.given>`.

    :func:`~hypothesis.strategies.builds` will be used automatically for
    classes with type annotations on ``__init__`` , so you only need to
    register a strategy if one or more arguments need to be more tightly
    defined than their type-based default, or if you want to supply a strategy
    for an argument with a default value.

    ``strategy`` may be a search strategy, or a function that takes a type and
    returns a strategy (useful for generic types).

    Note that you may not register a parametrised generic type (such as
    ``MyCollection[int]``) directly, because the resolution logic does not
    handle this case correctly.  Instead, you may register a *function* for
    ``MyCollection`` and `inspect the type parameters within that function
    <https://stackoverflow.com/q/48572831>`__.
    """
    # TODO: We would like to move this to the top level, but pending some major
    # refactoring it's hard to do without creating circular imports.
    from hypothesis.strategies._internal import types

    if not types.is_a_type(custom_type):
        raise InvalidArgument("custom_type=%r must be a type")
    elif not (isinstance(strategy, SearchStrategy) or callable(strategy)):
        raise InvalidArgument(
            "strategy=%r must be a SearchStrategy, or a function that takes "
            "a generic type and returns a specific SearchStrategy"
        )
    elif isinstance(strategy, SearchStrategy) and strategy.is_empty:
        raise InvalidArgument("strategy=%r must not be empty")
    elif types.has_type_arguments(custom_type):
        origin = getattr(custom_type, "__origin__", None)
        raise InvalidArgument(
            f"Cannot register generic type {custom_type!r}, because it has type "
            "arguments which would not be handled.  Instead, register a function "
            f"for {origin!r} which can inspect specific type objects and return a "
            "strategy."
        )

    types._global_type_lookup[custom_type] = strategy
    from_type.__clear_cache()  # type: ignore


@cacheable
@defines_strategy(never_lazy=True)
def deferred(definition: Callable[[], SearchStrategy[Ex]]) -> SearchStrategy[Ex]:
    """A deferred strategy allows you to write a strategy that references other
    strategies that have not yet been defined. This allows for the easy
    definition of recursive and mutually recursive strategies.

    The definition argument should be a zero-argument function that returns a
    strategy. It will be evaluated the first time the strategy is used to
    produce an example.

    Example usage:

    >>> import hypothesis.strategies as st
    >>> x = st.deferred(lambda: st.booleans() | st.tuples(x, x))
    >>> x.example()
    (((False, (True, True)), (False, True)), (True, True))
    >>> x.example()
    True

    Mutual recursion also works fine:

    >>> a = st.deferred(lambda: st.booleans() | b)
    >>> b = st.deferred(lambda: st.tuples(a, a))
    >>> a.example()
    True
    >>> b.example()
    (False, (False, ((False, True), False)))

    Examples from this strategy shrink as they normally would from the strategy
    returned by the definition.
    """
    return DeferredStrategy(definition)


@defines_strategy(force_reusable_values=True)
def emails() -> SearchStrategy[str]:
    """A strategy for generating email addresses as unicode strings. The
    address format is specified in :rfc:`5322#section-3.4.1`. Values shrink
    towards shorter local-parts and host domains.

    This strategy is useful for generating "user data" for tests, as
    mishandling of email addresses is a common source of bugs.
    """
    from hypothesis.provisional import domains

    local_chars = string.ascii_letters + string.digits + "!#$%&'*+-/=^_`{|}~"
    local_part = text(local_chars, min_size=1, max_size=64)
    # TODO: include dot-atoms, quoted strings, escaped chars, etc in local part
    return builds("{}@{}".format, local_part, domains()).filter(
        lambda addr: len(addr) <= 254
    )


@defines_strategy()
def functions(
    *,
    like: Callable[..., Any] = lambda: None,
    returns: Optional[SearchStrategy[Any]] = None,
    pure: bool = False,
) -> SearchStrategy[Callable[..., Any]]:
    # The proper type signature of `functions()` would have T instead of Any, but mypy
    # disallows default args for generics: https://github.com/python/mypy/issues/3737
    """functions(*, like=lambda: None, returns=none(), pure=False)

    A strategy for functions, which can be used in callbacks.

    The generated functions will mimic the interface of ``like``, which must
    be a callable (including a class, method, or function).  The return value
    for the function is drawn from the ``returns`` argument, which must be a
    strategy.

    If ``pure=True``, all arguments passed to the generated function must be
    hashable, and if passed identical arguments the original return value will
    be returned again - *not* regenerated, so beware mutable values.

    If ``pure=False``, generated functions do not validate their arguments, and
    may return a different value if called again with the same arguments.

    Generated functions can only be called within the scope of the ``@given``
    which created them.  This strategy does not support ``.example()``.
    """
    check_type(bool, pure, "pure")
    if not callable(like):
        raise InvalidArgument(
            "The first argument to functions() must be a callable to imitate, "
            "but got non-callable like=%r" % (nicerepr(like),)
        )

    if returns is None:
        hints = get_type_hints(like)
        returns = from_type(hints.get("return", type(None)))

    check_strategy(returns, "returns")
    return FunctionStrategy(like, returns, pure)


@composite
def slices(draw: Any, size: int) -> slice:
    """Generates slices that will select indices up to the supplied size

    Generated slices will have start and stop indices that range from -size to size - 1
    and will step in the appropriate direction. Slices should only produce an empty selection
    if the start and end are the same.

    Examples from this strategy shrink toward 0 and smaller values
    """
    check_valid_size(size, "size")
    if size == 0:
        step = draw(none() | integers().filter(bool))
        return slice(None, None, step)

    min_start = min_stop = 0
    max_start = max_stop = size
    min_step = 1
    # For slices start is inclusive and stop is exclusive
    start = draw(integers(min_start, max_start) | none())
    stop = draw(integers(min_stop, max_stop) | none())

    # Limit step size to be reasonable
    if start is None and stop is None:
        max_step = size
    elif start is None:
        max_step = stop
    elif stop is None:
        max_step = start
    else:
        max_step = abs(start - stop)

    step = draw(integers(min_step, max_step or 1))

    if (stop or 0) < (start or 0):
        step *= -1

    if draw(booleans()) and start is not None:
        start -= size
    if draw(booleans()) and stop is not None:
        stop -= size

    return slice(start, stop, step)
