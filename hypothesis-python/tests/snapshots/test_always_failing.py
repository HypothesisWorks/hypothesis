# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
import hashlib
from ipaddress import IPv4Address

import pytest
from pytest import param

from hypothesis import given, strategies as st

from tests.snapshots.conftest import EXPLAIN_SETTINGS, SNAPSHOT_SETTINGS
from tests.common.utils import run_test_for_falsifying_example

class Opaque:
    """Object with no useful repr, forcing call-style output."""


class Pair:
    def __init__(self, x, y):
        self.x = x
        self.y = y


@pytest.mark.parametrize("given_kwargs",
[
    # Primitives
    param({"n": st.integers()}, id="integers"),
    param({"x": st.floats()}, id="floats"),
    param({"b": st.booleans()}, id="booleans"),
    param({"s": st.text()}, id="text"),
    param({"b": st.binary()}, id="binary"),
    param({"c": st.characters()}, id="characters"),
    param({"n": st.none()}, id="none"),
    param({"z": st.complex_numbers()}, id="complex_numbers"),
    param({"d": st.decimals()}, id="decimals"),
    param({"f": st.fractions()}, id="fractions"),
    # Date/time
    param({"d": st.dates()}, id="dates"),
    param({"dt": st.datetimes()}, id="datetimes"),
    param({"t": st.times()}, id="times"),
    param({"td": st.timedeltas()}, id="timedeltas"),
    # Collections
    param({"xs": st.lists(st.integers())}, id="lists"),
    param({"xs": st.sets(st.integers())}, id="sets"),
    param({"xs": st.frozensets(st.integers())}, id="frozensets"),
    param(
        {"t": st.tuples(st.integers(), st.text(), st.booleans())}, id="tuples"
    ),
    param(
        {"d": st.dictionaries(st.text(max_size=3), st.integers())}, id="dictionaries"
    ),
    param(
        {
            "d": st.fixed_dictionaries(
                {"name": st.text(max_size=5), "age": st.integers()}
            )
        },
        id="fixed_dictionaries",
    ),
    param({"it": st.iterables(st.integers())}, id="iterables"),
    param({"p": st.permutations(list(range(5)))}, id="permutations"),
    # Combinators
    param({"x": st.just(42)}, id="just"),
    param(
        {"x": st.sampled_from(["alice", "bob", "charlie"])}, id="sampled_from"
    ),
    param({"x": st.one_of(st.integers(), st.text())}, id="one_of"),
    param({"s": st.from_regex(r"[a-z]{3,5}", fullmatch=True)}, id="from_regex"),
    param({"x": st.from_type(IPv4Address)}, id="from_type"),
    param(
        {"x": st.recursive(st.integers(), lambda s: st.lists(s, max_size=3))},
        id="recursive",
    ),
    param({"x": st.deferred(st.integers)}, id="deferred"),
    param({"x": st.shared(st.integers(), key="test")}, id="shared"),
    param({"s": st.integers().map(str)}, id="map_to_str"),
    param(
        {"b": st.binary().map(lambda b: hashlib.sha256(b).digest())}, id="map_to_bytes"
    ),
    param({"n": st.integers().filter(lambda n: n % 2 == 0)}, id="filter"),
    param(
        {"p": st.builds(Pair, x=st.integers(), y=st.text(max_size=3))}, id="builds"
    ),
    param({"xs": st.from_type(list[int])}, id="builds_from_type"),
    param(
        {"f": st.functions(like=lambda x: x, returns=st.booleans())}, id="functions"
    ),
    # Special types
    param({"u": st.uuids()}, id="uuids"),
    param({"e": st.emails()}, id="emails"),
    param({"ip": st.ip_addresses()}, id="ip_addresses"),
    param({"s": st.slices(10)}, id="slices"),
    param({"r": st.randoms()}, id="randoms"),
    # Multi-arg
    param({"n": st.integers(), "s": st.text()}, id="two_args"),
    param(
        {
            "a": st.integers(),
            "b": st.floats(),
            "c": st.text(),
            "d": st.booleans(),
            "e": st.none(),
        },
        id="many_args",
    ),
    param(
        {
            "xs": st.lists(st.integers()),
            "mapping": st.dictionaries(st.text(max_size=3), st.booleans()),
            "choice": st.sampled_from([10, 20, 30]),
        },
        id="mixed_strategies",
    ),
    # Lambda formatting
    param({"x": st.builds(lambda: Opaque())}, id="builds_no_arg_lambda"),
    param(
        {"x": st.builds(lambda n: Opaque(), n=st.integers())},
        id="builds_single_arg_lambda",
    ),
    param(
        {"x": st.builds(lambda x, y: Opaque(), x=st.integers(), y=st.text())},
        id="builds_multi_arg_lambda",
    ),
    param(
        {"x": st.builds(lambda x, y: Opaque(), st.integers(), st.text())},
        id="builds_lambda_positional_args",
    ),
    param(
        {
            "x": st.builds(
                lambda x, y, z: Opaque(),
                st.integers(),
                y=st.text(),
                z=st.booleans(),
            )
        },
        id="builds_lambda_mixed_args",
    ),
    param(
        {"x": st.builds(lambda x, y: Pair(x, y), x=st.integers(), y=st.text())},
        id="builds_lambda_returning_object",
    ),
    param(
        {"x": st.integers().map(lambda n: Opaque())}, id="map_lambda_opaque_result"
    ),
    param(
        {"x": st.integers().map(lambda n: n * 2).map(lambda n: Opaque())},
        id="map_chained_lambdas_opaque",
    ),
    param(
        {"x": st.builds(lambda a, b="hello": Opaque(), a=st.integers())},
        id="builds_lambda_with_defaults",
    ),
    param(
        {
            "x": st.integers(min_value=0, max_value=3).flatmap(
                lambda n: st.text(min_size=n, max_size=n)
            )
        },
        id="flatmap_lambda",
    ),
]
)
def test_always_failing(given_kwargs, snapshot):
    @SNAPSHOT_SETTINGS
    @given(**given_kwargs)
    def inner(**kwargs):
        raise AssertionError

    assert run_test_for_falsifying_example(inner) == snapshot


@pytest.mark.parametrize("given_kwargs",
[
    param(
        {"x": st.integers().map(lambda n: n + 1)},
        id="map_lambda_explain_forces_call_style",
    ),
    param({"s": st.from_regex(r"..", fullmatch=True)}, id="explain_from_regex"),
    param({"s": st.integers().map(str)}, id="explain_map_to_str"),
]


)
def test_always_failing_explain(given_kwargs, snapshot):
    @EXPLAIN_SETTINGS
    @given(**given_kwargs)
    def inner(**kwargs):
        raise AssertionError

    assert run_test_for_falsifying_example(inner) == snapshot
