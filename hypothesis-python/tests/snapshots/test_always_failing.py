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

from hypothesis import given, strategies as st

from tests.snapshots.conftest import EXPLAIN_SETTINGS, SNAPSHOT_SETTINGS
from tests.common.utils import run_test_for_falsifying_example

class Opaque:
    """Object with no useful repr, forcing call-style output."""


class Pair:
    def __init__(self, x, y):
        self.x = x
        self.y = y


ALWAYS_FAILING_CASES = [
    # Primitives
    pytest.param({"n": st.integers()}, id="integers"),
    pytest.param({"x": st.floats()}, id="floats"),
    pytest.param({"b": st.booleans()}, id="booleans"),
    pytest.param({"s": st.text()}, id="text"),
    pytest.param({"b": st.binary()}, id="binary"),
    pytest.param({"c": st.characters()}, id="characters"),
    pytest.param({"n": st.none()}, id="none"),
    pytest.param({"z": st.complex_numbers()}, id="complex_numbers"),
    pytest.param({"d": st.decimals()}, id="decimals"),
    pytest.param({"f": st.fractions()}, id="fractions"),
    # Date/time
    pytest.param({"d": st.dates()}, id="dates"),
    pytest.param({"dt": st.datetimes()}, id="datetimes"),
    pytest.param({"t": st.times()}, id="times"),
    pytest.param({"td": st.timedeltas()}, id="timedeltas"),
    # Collections
    pytest.param({"xs": st.lists(st.integers())}, id="lists"),
    pytest.param({"xs": st.sets(st.integers())}, id="sets"),
    pytest.param({"xs": st.frozensets(st.integers())}, id="frozensets"),
    pytest.param(
        {"t": st.tuples(st.integers(), st.text(), st.booleans())}, id="tuples"
    ),
    pytest.param(
        {"d": st.dictionaries(st.text(max_size=3), st.integers())}, id="dictionaries"
    ),
    pytest.param(
        {
            "d": st.fixed_dictionaries(
                {"name": st.text(max_size=5), "age": st.integers()}
            )
        },
        id="fixed_dictionaries",
    ),
    pytest.param({"it": st.iterables(st.integers())}, id="iterables"),
    pytest.param({"p": st.permutations(list(range(5)))}, id="permutations"),
    # Combinators
    pytest.param({"x": st.just(42)}, id="just"),
    pytest.param(
        {"x": st.sampled_from(["alice", "bob", "charlie"])}, id="sampled_from"
    ),
    pytest.param({"x": st.one_of(st.integers(), st.text())}, id="one_of"),
    pytest.param({"s": st.from_regex(r"[a-z]{3,5}", fullmatch=True)}, id="from_regex"),
    pytest.param({"x": st.from_type(IPv4Address)}, id="from_type"),
    pytest.param(
        {"x": st.recursive(st.integers(), lambda s: st.lists(s, max_size=3))},
        id="recursive",
    ),
    pytest.param({"x": st.deferred(st.integers)}, id="deferred"),
    pytest.param({"x": st.shared(st.integers(), key="test")}, id="shared"),
    pytest.param({"s": st.integers().map(str)}, id="map_to_str"),
    pytest.param(
        {"b": st.binary().map(lambda b: hashlib.sha256(b).digest())}, id="map_to_bytes"
    ),
    pytest.param({"n": st.integers().filter(lambda n: n % 2 == 0)}, id="filter"),
    pytest.param(
        {"p": st.builds(Pair, x=st.integers(), y=st.text(max_size=3))}, id="builds"
    ),
    pytest.param({"xs": st.from_type(list[int])}, id="builds_from_type"),
    pytest.param(
        {"f": st.functions(like=lambda x: x, returns=st.booleans())}, id="functions"
    ),
    # Special types
    pytest.param({"u": st.uuids()}, id="uuids"),
    pytest.param({"e": st.emails()}, id="emails"),
    pytest.param({"ip": st.ip_addresses()}, id="ip_addresses"),
    pytest.param({"s": st.slices(10)}, id="slices"),
    pytest.param({"r": st.randoms()}, id="randoms"),
    # Multi-arg
    pytest.param({"n": st.integers(), "s": st.text()}, id="two_args"),
    pytest.param(
        {
            "a": st.integers(),
            "b": st.floats(),
            "c": st.text(),
            "d": st.booleans(),
            "e": st.none(),
        },
        id="many_args",
    ),
    pytest.param(
        {
            "xs": st.lists(st.integers()),
            "mapping": st.dictionaries(st.text(max_size=3), st.booleans()),
            "choice": st.sampled_from([10, 20, 30]),
        },
        id="mixed_strategies",
    ),
    # Lambda formatting
    pytest.param({"x": st.builds(lambda: Opaque())}, id="builds_no_arg_lambda"),
    pytest.param(
        {"x": st.builds(lambda n: Opaque(), n=st.integers())},
        id="builds_single_arg_lambda",
    ),
    pytest.param(
        {"x": st.builds(lambda x, y: Opaque(), x=st.integers(), y=st.text())},
        id="builds_multi_arg_lambda",
    ),
    pytest.param(
        {"x": st.builds(lambda x, y: Opaque(), st.integers(), st.text())},
        id="builds_lambda_positional_args",
    ),
    pytest.param(
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
    pytest.param(
        {"x": st.builds(lambda x, y: Pair(x, y), x=st.integers(), y=st.text())},
        id="builds_lambda_returning_object",
    ),
    pytest.param(
        {"x": st.integers().map(lambda n: Opaque())}, id="map_lambda_opaque_result"
    ),
    pytest.param(
        {"x": st.integers().map(lambda n: n * 2).map(lambda n: Opaque())},
        id="map_chained_lambdas_opaque",
    ),
    pytest.param(
        {"x": st.builds(lambda a, b="hello": Opaque(), a=st.integers())},
        id="builds_lambda_with_defaults",
    ),
    pytest.param(
        {
            "x": st.integers(min_value=0, max_value=3).flatmap(
                lambda n: st.text(min_size=n, max_size=n)
            )
        },
        id="flatmap_lambda",
    ),
]


@pytest.mark.parametrize("given_kwargs", ALWAYS_FAILING_CASES)
def test_always_failing(given_kwargs, snapshot):
    @SNAPSHOT_SETTINGS
    @given(**given_kwargs)
    def inner(**kwargs):
        raise AssertionError

    assert run_test_for_falsifying_example(inner) == snapshot


ALWAYS_FAILING_EXPLAIN_CASES = [
    pytest.param(
        {"x": st.integers().map(lambda n: n + 1)},
        id="map_lambda_explain_forces_call_style",
    ),
    pytest.param({"s": st.from_regex(r"..", fullmatch=True)}, id="explain_from_regex"),
    pytest.param({"s": st.integers().map(str)}, id="explain_map_to_str"),
]


@pytest.mark.parametrize("given_kwargs", ALWAYS_FAILING_EXPLAIN_CASES)
def test_always_failing_explain(given_kwargs, snapshot):
    @EXPLAIN_SETTINGS
    @given(**given_kwargs)
    def inner(**kwargs):
        raise AssertionError

    assert run_test_for_falsifying_example(inner) == snapshot
