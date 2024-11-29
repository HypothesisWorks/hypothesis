# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import sys
from collections import namedtuple

from hypothesis.strategies import (
    binary,
    booleans,
    builds,
    complex_numbers,
    decimals,
    dictionaries,
    fixed_dictionaries,
    floats,
    fractions,
    frozensets,
    integers,
    just,
    lists,
    none,
    one_of,
    randoms,
    recursive,
    sampled_from,
    sets,
    text,
    tuples,
)

from tests.common.debug import TIME_INCREMENT

__all__ = ["TIME_INCREMENT", "OrderedPair", "standard_types"]

OrderedPair = namedtuple("OrderedPair", ("left", "right"))

ordered_pair = integers().flatmap(
    lambda right: integers(min_value=0).map(
        lambda length: OrderedPair(right - length, right)
    )
)


def constant_list(strat):
    return strat.flatmap(lambda v: lists(just(v)))


ABC = namedtuple("ABC", ("a", "b", "c"))


def abc(x, y, z):
    return builds(ABC, x, y, z)


standard_types = [
    lists(none(), max_size=0),
    tuples(),
    sets(none(), max_size=0),
    frozensets(none(), max_size=0),
    fixed_dictionaries({}),
    abc(booleans(), booleans(), booleans()),
    abc(booleans(), booleans(), integers()),
    fixed_dictionaries({"a": integers(), "b": booleans()}),
    dictionaries(booleans(), integers()),
    dictionaries(text(), booleans()),
    one_of(integers(), tuples(booleans())),
    sampled_from(range(10)),
    one_of(just("a"), just("b"), just("c")),
    sampled_from(("a", "b", "c")),
    integers(),
    integers(min_value=3),
    integers(min_value=(-(2**32)), max_value=(2**64)),
    floats(),
    floats(min_value=-2.0, max_value=3.0),
    floats(),
    floats(min_value=-2.0),
    floats(),
    floats(max_value=-0.0),
    floats(),
    floats(min_value=0.0),
    floats(min_value=3.14, max_value=3.14),
    text(),
    binary(),
    booleans(),
    tuples(booleans(), booleans()),
    frozensets(integers()),
    sets(frozensets(booleans())),
    complex_numbers(),
    fractions(),
    decimals(),
    lists(lists(booleans())),
    lists(floats(0.0, 0.0)),
    ordered_pair,
    constant_list(integers()),
    integers().filter(lambda x: abs(x) > 100),
    floats(min_value=-sys.float_info.max, max_value=sys.float_info.max),
    none(),
    randoms(use_true_random=True),
    booleans().flatmap(lambda x: booleans() if x else complex_numbers()),
    recursive(base=booleans(), extend=lambda x: lists(x, max_size=3), max_leaves=10),
]
