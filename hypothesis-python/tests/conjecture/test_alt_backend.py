# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import itertools
import math
import sys
from contextlib import contextmanager
from random import Random
from typing import Optional

import pytest

from hypothesis import HealthCheck, Verbosity, assume, given, settings, strategies as st
from hypothesis.control import current_build_context
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.errors import (
    BackendCannotProceed,
    Flaky,
    HypothesisException,
    InvalidArgument,
    Unsatisfiable,
)
from hypothesis.internal.compat import int_to_bytes
from hypothesis.internal.conjecture.data import (
    AVAILABLE_PROVIDERS,
    COLLECTION_DEFAULT_MAX_SIZE,
    ConjectureData,
    PrimitiveProvider,
)
from hypothesis.internal.conjecture.engine import ConjectureRunner
from hypothesis.internal.floats import SIGNALING_NAN
from hypothesis.internal.intervalsets import IntervalSet

from tests.common.debug import minimal
from tests.common.utils import capture_observations, capture_out
from tests.conjecture.common import ir_nodes


class PrngProvider(PrimitiveProvider):
    # A test-only implementation of the PrimitiveProvider interface, which uses
    # a very simple PRNG to choose each value. Dumb but efficient, and entirely
    # independent of our real backend

    def __init__(self, conjecturedata: "ConjectureData | None", /) -> None:
        super().__init__(conjecturedata)
        self.prng = Random(0)

    def draw_boolean(
        self,
        p: float = 0.5,
        *,
        forced: Optional[bool] = None,
        fake_forced: bool = False,
    ) -> bool:
        if forced is not None:
            return forced
        return self.prng.random() < p

    def draw_integer(
        self,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        *,
        weights: Optional[dict[int, float]] = None,
        shrink_towards: int = 0,
        forced: Optional[int] = None,
        fake_forced: bool = False,
    ) -> int:
        assert isinstance(shrink_towards, int)  # otherwise ignored here
        if forced is not None:
            return forced

        if weights is not None:
            assert min_value is not None
            assert max_value is not None
            # use .choices so we can use the weights= param.
            choices = self.prng.choices(
                range(min_value, max_value + 1), weights=weights, k=1
            )
            return choices[0]

        if min_value is None and max_value is None:
            min_value = -(2**127)
            max_value = 2**127 - 1
        elif min_value is None:
            min_value = max_value - 2**64
        elif max_value is None:
            max_value = min_value + 2**64
        return self.prng.randint(min_value, max_value)

    def draw_float(
        self,
        *,
        min_value: float = -math.inf,
        max_value: float = math.inf,
        allow_nan: bool = True,
        smallest_nonzero_magnitude: float,
        forced: Optional[float] = None,
        fake_forced: bool = False,
    ) -> float:
        if forced is not None:
            return forced

        if allow_nan and self.prng.random() < 1 / 32:
            nans = [math.nan, -math.nan, SIGNALING_NAN, -SIGNALING_NAN]
            return self.prng.choice(nans)

        # small chance of inf values, if they are in bounds
        if min_value <= math.inf <= max_value and self.prng.random() < 1 / 32:
            return math.inf
        if min_value <= -math.inf <= max_value and self.prng.random() < 1 / 32:
            return -math.inf

        # get rid of infs, they cause nans if we pass them to prng.uniform
        if min_value in [-math.inf, math.inf]:
            min_value = math.copysign(1, min_value) * sys.float_info.max
            # being too close to the bounds causes prng.uniform to only return
            # inf.
            min_value /= 2
        if max_value in [-math.inf, math.inf]:
            max_value = math.copysign(1, max_value) * sys.float_info.max
            max_value /= 2

        value = self.prng.uniform(min_value, max_value)
        if value and abs(value) < smallest_nonzero_magnitude:
            return math.copysign(0.0, value)
        return value

    def draw_string(
        self,
        intervals: IntervalSet,
        *,
        min_size: int = 0,
        max_size: int = COLLECTION_DEFAULT_MAX_SIZE,
        forced: Optional[str] = None,
        fake_forced: bool = False,
    ) -> str:
        if forced is not None:
            return forced
        size = self.prng.randint(
            min_size, max(min_size, min(100 if max_size is None else max_size, 100))
        )
        return "".join(map(chr, self.prng.choices(intervals, k=size)))

    def draw_bytes(
        self,
        min_size: int = 0,
        max_size: int = COLLECTION_DEFAULT_MAX_SIZE,
        *,
        forced: Optional[bytes] = None,
        fake_forced: bool = False,
    ) -> bytes:
        if forced is not None:
            return forced
        max_size = 100 if max_size is None else max_size
        size = self.prng.randint(min_size, max_size)
        try:
            return self.prng.randbytes(size)
        except AttributeError:  # randbytes is new in python 3.9
            return bytes(self.prng.randint(0, 255) for _ in range(size))


@contextmanager
def temp_register_backend(name, cls):
    try:
        AVAILABLE_PROVIDERS[name] = f"{__name__}.{cls.__name__}"
        yield
    finally:
        AVAILABLE_PROVIDERS.pop(name)


@pytest.mark.parametrize(
    "strategy",
    [
        st.booleans(),
        st.integers(0, 3),
        st.floats(0, 1),
        st.text(max_size=3),
        st.binary(max_size=3),
    ],
    ids=repr,
)
def test_find_with_backend_then_convert_to_buffer_shrink_and_replay(strategy):
    db = InMemoryExampleDatabase()
    assert not db.data

    with temp_register_backend("prng", PrngProvider):

        @settings(database=db, backend="prng")
        @given(strategy)
        def test(value):
            if isinstance(value, float):
                assert value >= 0.5
            else:
                assert value

        with pytest.raises(AssertionError):
            test()

    assert db.data
    buffers = {x for x in db.data[next(iter(db.data))] if x}
    assert buffers, db.data


def test_backend_can_shrink_integers():
    with temp_register_backend("prng", PrngProvider):
        n = minimal(
            st.integers(),
            lambda n: n >= 123456,
            settings=settings(backend="prng", database=None),
        )

    assert n == 123456


def test_backend_can_shrink_bytes():
    with temp_register_backend("prng", PrngProvider):
        b = minimal(
            # this test doubles as coverage for popping draw_bytes ir nodes,
            # and that path is only taken with fixed size for the moment. can
            # be removed when we support variable length binary at the ir level.
            st.binary(min_size=2, max_size=2),
            lambda b: len(b) >= 2 and b[1] >= 10,
            settings=settings(backend="prng", database=None),
        )

    assert b == int_to_bytes(10, size=2)


def test_backend_can_shrink_strings():
    with temp_register_backend("prng", PrngProvider):
        s = minimal(
            st.text(),
            lambda s: len(s) >= 10,
            settings=settings(backend="prng", database=None),
        )

    assert len(s) == 10


def test_backend_can_shrink_booleans():
    with temp_register_backend("prng", PrngProvider):
        b = minimal(
            st.booleans(), lambda b: b, settings=settings(backend="prng", database=None)
        )

    assert b


def test_backend_can_shrink_floats():
    with temp_register_backend("prng", PrngProvider):
        f = minimal(
            st.floats(),
            lambda f: f >= 100.5,
            settings=settings(backend="prng", database=None),
        )

    assert f == 101.0


# mostly a shoehorned coverage test until the shrinker is migrated to the ir
# and calls cached_test_function_ir with backends consistently.
@given(ir_nodes())
def test_new_conjecture_data_ir_with_backend(node):
    def test(data):
        getattr(data, f"draw_{node.ir_type}")(**node.kwargs)

    with temp_register_backend("prng", PrngProvider):
        runner = ConjectureRunner(test, settings=settings(backend="prng"))
        runner.cached_test_function_ir([node.value])


# trivial provider for tests which don't care about drawn distributions.
class TrivialProvider(PrimitiveProvider):
    def draw_integer(self, *args, **kwargs):
        return 1

    def draw_boolean(self, *args, **kwargs):
        return True

    def draw_float(self, *args, **kwargs):
        return 1.0

    def draw_bytes(self, *args, **kwargs):
        return b""

    def draw_string(self, *args, **kwargs):
        return ""


class InvalidLifetime(TrivialProvider):

    lifetime = "forever and a day!"


def test_invalid_lifetime():
    with temp_register_backend("invalid_lifetime", InvalidLifetime):
        with pytest.raises(InvalidArgument):
            ConjectureRunner(
                lambda: True, settings=settings(backend="invalid_lifetime")
            )


function_lifetime_init_count = 0


class LifetimeTestFunction(TrivialProvider):
    lifetime = "test_function"

    def __init__(self, conjecturedata):
        super().__init__(conjecturedata)
        # hacky, but no easy alternative.
        global function_lifetime_init_count
        function_lifetime_init_count += 1


def test_function_lifetime():
    with temp_register_backend("lifetime_function", LifetimeTestFunction):

        @given(st.integers())
        @settings(backend="lifetime_function")
        def test_function(n):
            pass

        assert function_lifetime_init_count == 0
        test_function()
        assert function_lifetime_init_count == 1
        test_function()
        assert function_lifetime_init_count == 2


test_case_lifetime_init_count = 0


class LifetimeTestCase(TrivialProvider):
    lifetime = "test_case"

    def __init__(self, conjecturedata):
        super().__init__(conjecturedata)
        global test_case_lifetime_init_count
        test_case_lifetime_init_count += 1


def test_case_lifetime():
    test_function_count = 0

    with temp_register_backend("lifetime_case", LifetimeTestCase):

        @given(st.integers())
        @settings(backend="lifetime_case", database=InMemoryExampleDatabase())
        def test_function(n):
            nonlocal test_function_count
            test_function_count += 1

        assert test_case_lifetime_init_count == 0
        test_function()

        # we create a new provider each time we *try* to generate an input to the
        # test function, but this could be filtered out, discarded as duplicate,
        # etc. We also sometimes try predetermined inputs to the test function,
        # such as the zero buffer, which does not entail creating providers.
        # These two facts combined mean that the number of inits could be
        # anywhere reasonably close to the number of function calls.
        assert (
            test_function_count - 10
            <= test_case_lifetime_init_count
            <= test_function_count + 10
        )


def test_flaky_with_backend():
    with temp_register_backend("trivial", TrivialProvider), capture_observations():

        calls = 0

        @given(st.integers())
        @settings(backend="trivial", database=None)
        def test_function(n):
            nonlocal calls
            calls += 1
            assert n != calls % 2

        with pytest.raises(Flaky):
            test_function()


class BadRealizeProvider(TrivialProvider):
    def realize(self, value):
        return None


def test_bad_realize():
    with temp_register_backend("bad_realize", BadRealizeProvider):

        @given(st.integers())
        @settings(backend="bad_realize")
        def test_function(n):
            pass

        with pytest.raises(
            HypothesisException,
            match="expected .* from BadRealizeProvider.realize",
        ):
            test_function()


class RealizeProvider(TrivialProvider):
    avoid_realization = True

    def realize(self, value):
        if isinstance(value, int):
            return 42
        return value


def test_realize():
    with temp_register_backend("realize", RealizeProvider):

        values = []

        @given(st.integers())
        @settings(backend="realize")
        def test_function(n):
            values.append(current_build_context().data.provider.realize(n))

        test_function()

        assert all(n == 42 for n in values)


def test_realize_dependent_draw():
    with temp_register_backend("realize", RealizeProvider):

        @given(st.data())
        @settings(backend="realize")
        def test_function(data):
            n1 = data.draw(st.integers())
            n2 = data.draw(st.integers(n1, n1 + 10))
            assert n1 <= n2

        test_function()


@pytest.mark.parametrize("verbosity", [Verbosity.verbose, Verbosity.debug])
def test_realization_with_verbosity(verbosity):
    with temp_register_backend("realize", RealizeProvider):

        @given(st.floats())
        @settings(backend="realize", verbosity=verbosity)
        def test_function(f):
            pass

        with capture_out() as out:
            test_function()
        assert "Trying example: <symbolics>" in out.getvalue()


@pytest.mark.parametrize("verbosity", [Verbosity.verbose, Verbosity.debug])
def test_realization_with_verbosity_draw(verbosity):
    with temp_register_backend("realize", RealizeProvider):

        @given(st.data())
        @settings(backend="realize", verbosity=verbosity)
        def test_function(data):
            data.draw(st.integers())

        with capture_out() as out:
            test_function()
        assert "Draw 1: <symbolic>" in out.getvalue()


class ObservableProvider(TrivialProvider):
    def observe_test_case(self):
        return {"msg_key": "some message", "data_key": [1, "2", {}]}

    def observe_information_messages(self, *, lifetime):
        if lifetime == "test_case":
            yield {"type": "info", "title": "trivial-data", "content": {"k2": "v2"}}
        else:
            assert lifetime == "test_function"
            yield {"type": "alert", "title": "Trivial alert", "content": "message here"}
            yield {"type": "info", "title": "trivial-data", "content": {"k2": "v2"}}

    def realize(self, value):
        # Get coverage of the can't-realize path for observability outputs
        raise BackendCannotProceed


def test_custom_observations_from_backend():
    with temp_register_backend("observable", ObservableProvider):

        @given(st.none())
        @settings(backend="observable", database=None)
        def test_function(_):
            pass

        with capture_observations() as ls:
            test_function()

    assert len(ls) >= 3
    cases = [t["metadata"]["backend"] for t in ls if t["type"] == "test_case"]
    assert {"msg_key": "some message", "data_key": [1, "2", {}]} in cases

    assert "<backend failed to realize symbolic arguments>" in repr(ls)

    infos = [
        {k: v for k, v in t.items() if k in ("title", "content")}
        for t in ls
        if t["type"] != "test_case"
    ]
    assert {"title": "Trivial alert", "content": "message here"} in infos
    assert {"title": "trivial-data", "content": {"k2": "v2"}} in infos


class FallibleProvider(TrivialProvider):
    def __init__(self, conjecturedata: "ConjectureData", /) -> None:
        super().__init__(conjecturedata)
        self._it = itertools.cycle([1, 1, 1, "discard_test_case", "other"])

    def draw_integer(self, *args, **kwargs):
        x = next(self._it)
        if isinstance(x, str):
            raise BackendCannotProceed(x)
        return x


def test_falls_back_to_default_backend():
    with temp_register_backend("fallible", FallibleProvider):
        seen_other_ints = False

        @given(st.integers())
        @settings(backend="fallible", database=None, max_examples=100)
        def test_function(x):
            nonlocal seen_other_ints
            seen_other_ints |= x != 1

        test_function()
        assert seen_other_ints  # must have swapped backends then


def test_can_raise_unsatisfiable_after_falling_back():
    with temp_register_backend("fallible", FallibleProvider):

        @given(st.integers())
        @settings(
            backend="fallible",
            database=None,
            max_examples=100,
            suppress_health_check=[HealthCheck.filter_too_much],
        )
        def test_function(x):
            assume(x == "unsatisfiable")

        with pytest.raises(Unsatisfiable):
            test_function()


class ExhaustibleProvider(TrivialProvider):
    scope = "exhausted"

    def __init__(self, conjecturedata: "ConjectureData", /) -> None:
        super().__init__(conjecturedata)
        self._calls = 0

    def draw_integer(self, *args, **kwargs):
        self._calls += 1
        if self._calls > 20:
            # This is complete nonsense of course, so we'll see Hypothesis complain
            # that we found a problem after the backend reported verification.
            raise BackendCannotProceed(self.scope)
        return 1


class UnsoundVerifierProvider(ExhaustibleProvider):
    scope = "verified"


@pytest.mark.parametrize("provider", [ExhaustibleProvider, UnsoundVerifierProvider])
def test_notes_incorrect_verification(provider):
    msg = "backend='p' claimed to verify this test passes - please send them a bug report!"
    with temp_register_backend("p", provider):

        @given(st.integers())
        @settings(backend="p", database=None, max_examples=100)
        def test_function(x):
            assert x == 1  # True from this backend, false in general!

        with pytest.raises(AssertionError) as ctx:
            test_function()
        assert (msg in ctx.value.__notes__) == (provider is UnsoundVerifierProvider)


def test_invalid_provider_kw():
    with pytest.raises(InvalidArgument, match="got an instance instead"):
        ConjectureData(
            max_length=0,
            prefix=b"",
            random=None,
            provider=TrivialProvider(None),
            provider_kw={"one": "two"},
        )
