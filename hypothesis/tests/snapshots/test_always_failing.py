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

from tests.common.utils import (
    EXPLAIN_SETTINGS,
    SNAPSHOT_SETTINGS,
    run_test_for_falsifying_example,
)


class Opaque:
    """Object with no useful repr, forcing call-style output."""


class Pair:
    def __init__(self, x, y):
        self.x = x
        self.y = y


@pytest.mark.parametrize(
    "given_args",
    [
        # Primitives
        param([st.integers()], id="integers"),
        param([st.floats()], id="floats"),
        param([st.booleans()], id="booleans"),
        param([st.text()], id="text"),
        param([st.binary()], id="binary"),
        param([st.characters()], id="characters"),
        param([st.none()], id="none"),
        param([st.complex_numbers()], id="complex_numbers"),
        param([st.decimals()], id="decimals"),
        param([st.fractions()], id="fractions"),
        # Date/time
        param([st.dates()], id="dates"),
        param([st.datetimes()], id="datetimes"),
        param([st.times()], id="times"),
        param([st.timedeltas()], id="timedeltas"),
        # Collections
        param([st.lists(st.integers())], id="lists"),
        param([st.sets(st.integers())], id="sets"),
        param([st.frozensets(st.integers())], id="frozensets"),
        param([st.tuples(st.integers(), st.text(), st.booleans())], id="tuples"),
        param([st.dictionaries(st.text(max_size=3), st.integers())], id="dictionaries"),
        param(
            [
                st.fixed_dictionaries(
                    {"name": st.text(max_size=5), "age": st.integers()}
                )
            ],
            id="fixed_dictionaries",
        ),
        param([st.iterables(st.integers())], id="iterables"),
        param([st.permutations(list(range(5)))], id="permutations"),
        # Combinators
        param([st.just(42)], id="just"),
        param([st.sampled_from(["alice", "bob", "charlie"])], id="sampled_from"),
        param([st.one_of(st.integers(), st.text())], id="one_of"),
        param([st.from_regex(r"[a-z]{3,5}", fullmatch=True)], id="from_regex"),
        param([st.from_type(IPv4Address)], id="from_type"),
        param(
            [st.recursive(st.integers(), lambda s: st.lists(s, max_size=3))],
            id="recursive",
        ),
        param([st.deferred(st.integers)], id="deferred"),
        param([st.shared(st.integers(), key="test")], id="shared"),
        param([st.integers().map(str)], id="map_to_str"),
        param(
            [st.binary().map(lambda b: hashlib.sha256(b).digest())], id="map_to_bytes"
        ),
        param([st.integers().filter(lambda n: n % 2 == 0)], id="filter"),
        param([st.builds(Pair, x=st.integers(), y=st.text(max_size=3))], id="builds"),
        param([st.from_type(list[int])], id="builds_from_type"),
        param([st.functions(like=lambda x: x, returns=st.booleans())], id="functions"),
        # Special types
        param([st.uuids()], id="uuids"),
        param([st.emails()], id="emails"),
        param([st.ip_addresses()], id="ip_addresses"),
        param([st.slices(10)], id="slices"),
        param([st.randoms()], id="randoms"),
        # Multi-arg
        param([st.integers(), st.text()], id="two_args"),
        param(
            [st.integers(), st.floats(), st.text(), st.booleans(), st.none()],
            id="many_args",
        ),
        param(
            [
                st.lists(st.integers()),
                st.dictionaries(st.text(max_size=3), st.booleans()),
                st.sampled_from([10, 20, 30]),
            ],
            id="mixed_strategies",
        ),
        # Lambda formatting
        param([st.builds(lambda: Opaque())], id="builds_no_arg_lambda"),
        param(
            [st.builds(lambda n: Opaque(), n=st.integers())],
            id="builds_single_arg_lambda",
        ),
        param(
            [st.builds(lambda x, y: Opaque(), x=st.integers(), y=st.text())],
            id="builds_multi_arg_lambda",
        ),
        param(
            [st.builds(lambda x, y: Opaque(), st.integers(), st.text())],
            id="builds_lambda_positional_args",
        ),
        param(
            [
                st.builds(
                    lambda x, y, z: Opaque(),
                    st.integers(),
                    y=st.text(),
                    z=st.booleans(),
                )
            ],
            id="builds_lambda_mixed_args",
        ),
        param(
            [st.builds(lambda x, y: Pair(x, y), x=st.integers(), y=st.text())],
            id="builds_lambda_returning_object",
        ),
        param([st.integers().map(lambda n: Opaque())], id="map_lambda_opaque_result"),
        param(
            [st.integers().map(lambda n: n * 2).map(lambda n: Opaque())],
            id="map_chained_lambdas_opaque",
        ),
        param(
            [st.builds(lambda a, b="hello": Opaque(), a=st.integers())],
            id="builds_lambda_with_defaults",
        ),
        param(
            [
                st.integers(min_value=0, max_value=3).flatmap(
                    lambda n: st.text(min_size=n, max_size=n)
                )
            ],
            id="flatmap_lambda",
        ),
    ],
)
def test_always_failing(given_args, snapshot):
    given_kwargs = {f"v{i}": v for i, v in enumerate(given_args)}

    @SNAPSHOT_SETTINGS
    @given(**given_kwargs)
    def inner(**kwargs):
        raise AssertionError

    assert run_test_for_falsifying_example(inner) == snapshot


@pytest.mark.parametrize(
    "given_args",
    [
        param(
            [st.integers().map(lambda n: n + 1)],
            id="map_lambda_explain_forces_call_style",
        ),
        param([st.from_regex(r"..", fullmatch=True)], id="explain_from_regex"),
        param([st.integers().map(str)], id="explain_map_to_str"),
    ],
)
def test_always_failing_explain(given_args, snapshot):
    given_kwargs = {f"v{i}": v for i, v in enumerate(given_args)}

    @EXPLAIN_SETTINGS
    @given(**given_kwargs)
    def inner(**kwargs):
        raise AssertionError

    assert run_test_for_falsifying_example(inner) == snapshot
