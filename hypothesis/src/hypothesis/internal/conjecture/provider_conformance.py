# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import json
import math
import sys
from collections.abc import Callable, Collection, Iterable, Sequence
from random import Random
from typing import Any, cast

from hypothesis import (
    HealthCheck,
    Phase,
    Verbosity,
    assume,
    find,
    note,
    settings as Settings,
    strategies as st,
)
from hypothesis.errors import (
    BackendCannotProceed,
    FlakyFailure,
    Found,
    NoSuchExample,
    StopTest,
)
from hypothesis.internal.compat import batched
from hypothesis.internal.conjecture.choice import (
    ChoiceT,
    ChoiceTypeT,
    choice_equal,
    choice_permitted,
)
from hypothesis.internal.conjecture.data import ConjectureData, Status
from hypothesis.internal.conjecture.providers import (
    COLLECTION_DEFAULT_MAX_SIZE,
    HypothesisProvider,
    PrimitiveProvider,
    with_register_backend,
)
from hypothesis.internal.floats import SMALLEST_SUBNORMAL, sign_aware_lte
from hypothesis.internal.intervalsets import IntervalSet
from hypothesis.stateful import RuleBasedStateMachine, initialize, precondition, rule
from hypothesis.strategies import DrawFn, SearchStrategy
from hypothesis.strategies._internal.strings import OneCharStringStrategy, TextStrategy

_PYTHON_TYPES: dict[ChoiceTypeT, type] = {
    "integer": int,
    "float": float,
    "bytes": bytes,
    "string": str,
    "boolean": bool,
}


def build_intervals(intervals: list[int]) -> list[tuple[int, int]]:
    if len(intervals) % 2:
        intervals = intervals[:-1]
    intervals.sort()
    return list(batched(intervals, 2, strict=True))


def interval_lists(
    *, min_codepoint: int = 0, max_codepoint: int = sys.maxunicode, min_size: int = 0
) -> SearchStrategy[Iterable[Sequence[int]]]:
    return (
        st.lists(
            st.integers(min_codepoint, max_codepoint),
            unique=True,
            min_size=min_size * 2,
        )
        .map(sorted)
        .map(build_intervals)
    )


def intervals(
    *, min_codepoint: int = 0, max_codepoint: int = sys.maxunicode, min_size: int = 0
) -> SearchStrategy[IntervalSet]:
    return st.builds(
        IntervalSet,
        interval_lists(
            min_codepoint=min_codepoint, max_codepoint=max_codepoint, min_size=min_size
        ),
    )


@st.composite
def integer_weights(
    draw: DrawFn, min_value: int | None = None, max_value: int | None = None
) -> dict[int, float]:
    # Sampler doesn't play well with super small floats, so exclude them
    weights = draw(
        st.dictionaries(
            st.integers(min_value=min_value, max_value=max_value),
            st.floats(0.001, 1),
            min_size=1,
            max_size=255,
        )
    )
    # invalid to have a weighting that disallows all possibilities
    assume(sum(weights.values()) != 0)
    # re-normalize probabilities to sum to some arbitrary target < 1
    target = draw(st.floats(0.001, 0.999))
    factor = target / sum(weights.values())
    weights = {k: v * factor for k, v in weights.items()}
    # float rounding error can cause this to fail.
    assume(0.001 <= sum(weights.values()) <= 0.999)
    return weights


@st.composite
def integer_constraints(
    draw,
    *,
    use_min_value=None,
    use_max_value=None,
    use_shrink_towards=None,
    use_weights=None,
    use_forced=False,
):
    min_value = None
    max_value = None
    shrink_towards = 0
    weights = None

    if use_min_value is None:
        use_min_value = draw(st.booleans())
    if use_max_value is None:
        use_max_value = draw(st.booleans())
    use_shrink_towards = draw(st.booleans())
    if use_weights is None:
        use_weights = (
            draw(st.booleans()) if (use_min_value and use_max_value) else False
        )

    # Invariants:
    # (1) min_value <= forced <= max_value
    # (2) sum(weights.values()) < 1
    # (3) len(weights) <= 255

    if use_shrink_towards:
        shrink_towards = draw(st.integers())

    forced = draw(st.integers()) if use_forced else None
    if use_weights:
        assert use_max_value
        assert use_min_value

        min_value = draw(st.integers(max_value=forced))
        min_val = max(min_value, forced) if forced is not None else min_value
        max_value = draw(st.integers(min_value=min_val))

        weights = draw(integer_weights(min_value, max_value))
    else:
        if use_min_value:
            min_value = draw(st.integers(max_value=forced))
        if use_max_value:
            min_vals = []
            if min_value is not None:
                min_vals.append(min_value)
            if forced is not None:
                min_vals.append(forced)
            min_val = max(min_vals) if min_vals else None
            max_value = draw(st.integers(min_value=min_val))
            # degenerate-but-satisfiable ranges are a rich source of bugs
            if min_val is not None and draw(st.data()).conjecture_data.draw_boolean(
                0.25
            ):
                max_value = min_val

    if forced is not None:
        assume((forced - shrink_towards).bit_length() < 128)

    return {
        "min_value": min_value,
        "max_value": max_value,
        "shrink_towards": shrink_towards,
        "weights": weights,
        "forced": forced,
    }


@st.composite
def _collection_constraints(
    draw: DrawFn,
    *,
    forced: Any | None,
    use_min_size: bool | None = None,
    use_max_size: bool | None = None,
) -> dict[str, int]:
    min_size = 0
    max_size = COLLECTION_DEFAULT_MAX_SIZE
    # collections are quite expensive in entropy. cap to avoid overruns.
    cap = 50

    if use_min_size is None:
        use_min_size = draw(st.booleans())
    if use_max_size is None:
        use_max_size = draw(st.booleans())

    if use_min_size:
        min_size = draw(
            st.integers(0, min(len(forced), cap) if forced is not None else cap)
        )

    if use_max_size:
        lower = min_size if forced is None else max(min_size, len(forced))
        max_size = draw(st.integers(min_value=lower))
        if forced is None:
            # cap to some reasonable max size to avoid overruns.
            max_size = min(max_size, min_size + 100)
        # exact-size collections are degenerate-but-satisfiable; generate them
        # more often than chance
        if draw(st.data()).conjecture_data.draw_boolean(0.25):
            max_size = lower

    return {"min_size": min_size, "max_size": max_size}


@st.composite
def string_constraints(
    draw: DrawFn,
    *,
    use_min_size: bool | None = None,
    use_max_size: bool | None = None,
    use_forced: bool = False,
) -> Any:
    interval_set = draw(intervals())
    forced = (
        draw(TextStrategy(OneCharStringStrategy(interval_set))) if use_forced else None
    )
    constraints = draw(
        _collection_constraints(
            forced=forced, use_min_size=use_min_size, use_max_size=use_max_size
        )
    )
    # if the intervalset is empty, then the min size must be zero, because the
    # only valid value is the empty string.
    if len(interval_set) == 0:
        constraints["min_size"] = 0

    return {"intervals": interval_set, "forced": forced, **constraints}


@st.composite
def bytes_constraints(
    draw: DrawFn,
    *,
    use_min_size: bool | None = None,
    use_max_size: bool | None = None,
    use_forced: bool = False,
) -> Any:
    forced = draw(st.binary()) if use_forced else None

    constraints = draw(
        _collection_constraints(
            forced=forced, use_min_size=use_min_size, use_max_size=use_max_size
        )
    )
    return {"forced": forced, **constraints}


@st.composite
def float_constraints(
    draw,
    *,
    use_min_value=None,
    use_max_value=None,
    use_forced=False,
):
    if use_min_value is None:
        use_min_value = draw(st.booleans())
    if use_max_value is None:
        use_max_value = draw(st.booleans())

    forced = draw(st.floats()) if use_forced else None
    pivot = forced if (use_forced and not math.isnan(forced)) else None
    min_value = -math.inf
    max_value = math.inf
    smallest_nonzero_magnitude = SMALLEST_SUBNORMAL
    allow_nan = True if (use_forced and math.isnan(forced)) else draw(st.booleans())

    if use_min_value:
        min_value = draw(st.floats(max_value=pivot, allow_nan=False))

    if use_max_value:
        if pivot is None:
            min_val = min_value
        else:
            min_val = pivot if sign_aware_lte(min_value, pivot) else min_value
        max_value = draw(st.floats(min_value=min_val, allow_nan=False))

    largest_magnitude = max(abs(min_value), abs(max_value))
    # can't force something smaller than our smallest magnitude.
    if pivot is not None and pivot != 0.0:
        largest_magnitude = min(largest_magnitude, pivot)

    # avoid drawing from an empty range
    if largest_magnitude > 0:
        smallest_nonzero_magnitude = draw(
            st.floats(
                min_value=0,
                # smallest_nonzero_magnitude breaks internal clamper invariants if
                # it is allowed to be larger than the magnitude of {min, max}_value.
                #
                # Let's also be reasonable here; smallest_nonzero_magnitude is used
                # for subnormals, so we will never provide a number above 1 in practice.
                max_value=min(largest_magnitude, 1.0),
                exclude_min=True,
            )
        )

    assert sign_aware_lte(min_value, max_value)
    return {
        "min_value": min_value,
        "max_value": max_value,
        "forced": forced,
        "allow_nan": allow_nan,
        "smallest_nonzero_magnitude": smallest_nonzero_magnitude,
    }


@st.composite
def boolean_constraints(draw: DrawFn, *, use_forced: bool = False) -> Any:
    forced = draw(st.booleans()) if use_forced else None
    # avoid invalid forced combinations. Generate the boundary probabilities
    # p=0 and p=1 often, since they carry hard requirements for providers
    # rather than being advisory.
    p_strategy = st.floats(
        0, 1, exclude_min=forced is True, exclude_max=forced is False
    )
    if forced is None:
        p_strategy |= st.sampled_from([0.0, 1.0])
    p = draw(p_strategy)

    return {"p": p, "forced": forced}


def constraints_strategy(choice_type, strategy_constraints=None, *, use_forced=False):
    strategy = {
        "boolean": boolean_constraints,
        "integer": integer_constraints,
        "float": float_constraints,
        "bytes": bytes_constraints,
        "string": string_constraints,
    }[choice_type]
    if strategy_constraints is None:
        strategy_constraints = {}
    return strategy(**strategy_constraints.get(choice_type, {}), use_forced=use_forced)


def choice_types_constraints(strategy_constraints=None, *, use_forced=False):
    options: list[ChoiceTypeT] = ["boolean", "integer", "float", "bytes", "string"]
    return st.one_of(
        st.tuples(
            st.just(name),
            constraints_strategy(name, strategy_constraints, use_forced=use_forced),
        )
        for name in options
    )


def _assert_conforming(choice: Any, choice_type: ChoiceTypeT, constraints: Any) -> None:
    expected_type = _PYTHON_TYPES[choice_type]
    assert isinstance(choice, expected_type), (
        f"expected {choice_type} draw to return a {expected_type.__name__}, "
        f"got {choice!r} of type {type(choice).__name__}"
    )
    if choice_type == "integer":
        assert not isinstance(
            choice, bool
        ), f"expected integer draw to return an int, got bool {choice!r}"
    assert choice_permitted(cast(ChoiceT, choice), constraints), (
        f"drew {choice_type} {choice!r} which is not permitted by "
        f"constraints {constraints}"
    )


def _integer_constr(min_value=None, max_value=None, *, weights=None):
    return {
        "min_value": min_value,
        "max_value": max_value,
        "weights": weights,
        "shrink_towards": 0,
    }


def _float_constr(min_value=-math.inf, max_value=math.inf, *, allow_nan=True):
    return {
        "min_value": min_value,
        "max_value": max_value,
        "allow_nan": allow_nan,
        "smallest_nonzero_magnitude": SMALLEST_SUBNORMAL,
    }


def _collection_constr(min_size=0, max_size=10):
    return {"min_size": min_size, "max_size": max_size}


def _findability_cases() -> Iterable[tuple[ChoiceTypeT, dict, str, Callable]]:
    # (choice_type, constraints, description, predicate) tuples such that some
    # provider input should produce a value satisfying the predicate. We stick
    # to targets that any reasonable provider hits with probability at least
    # ~1/500 per test case, so a bounded search is reliable.
    cases: list[tuple[ChoiceTypeT, dict, str, Callable]] = [
        ("boolean", {"p": 0.5}, "True", lambda v: v is True),
        ("boolean", {"p": 0.5}, "False", lambda v: v is False),
        ("integer", _integer_constr(), "a negative value", lambda v: v < 0),
        ("integer", _integer_constr(), "a positive value", lambda v: v > 0),
        ("float", _float_constr(), "a negative value", lambda v: v < 0),
        ("float", _float_constr(), "a positive value", lambda v: v > 0),
        (
            "float",
            _float_constr(-10.0, 10.0, allow_nan=False),
            "a negative value",
            lambda v: v < 0,
        ),
        (
            "float",
            _float_constr(-10.0, 10.0, allow_nan=False),
            "a positive value",
            lambda v: v > 0,
        ),
    ]
    for target in range(-5, 6):
        cases.append(
            ("integer", _integer_constr(-5, 5), str(target), lambda v, t=target: v == t)
        )
        cases.append(
            (
                "integer",
                _integer_constr(-5, 5, weights={0: 0.25}),
                f"{target} (with weights)",
                lambda v, t=target: v == t,
            )
        )
    for target in range(-10, -2):
        cases.append(
            (
                "integer",
                _integer_constr(-10, -3),
                str(target),
                lambda v, t=target: v == t,
            )
        )
    for target in [3, 10]:
        cases.append(
            ("integer", _integer_constr(3, 10), str(target), lambda v, t=target: v == t)
        )

    string_constr = {"intervals": IntervalSet.from_string("ab"), **_collection_constr()}
    cases += [
        ("string", string_constr, "the empty string", lambda v: v == ""),
        ("string", string_constr, 'a string containing "a"', lambda v: "a" in v),
        ("string", string_constr, 'a string containing "b"', lambda v: "b" in v),
        ("string", string_constr, "a string of length >= 2", lambda v: len(v) >= 2),
        (
            "string",
            {"intervals": IntervalSet(()), **_collection_constr()},
            "the empty string (from an empty alphabet)",
            lambda v: v == "",
        ),
        ("bytes", _collection_constr(), "empty bytes", lambda v: v == b""),
        ("bytes", _collection_constr(), "nonempty bytes", lambda v: v != b""),
        (
            "bytes",
            _collection_constr(),
            "a byte >= 128",
            lambda v: any(b >= 128 for b in v),
        ),
    ]
    return cases


def _run_one_test_case(
    provider: PrimitiveProvider,
    data: ConjectureData | None,
    choice_type: ChoiceTypeT,
    constraints: dict,
    n_draws: int,
    context_manager_exceptions: tuple[type[BaseException], ...],
) -> list[Any]:
    values: list[Any] = []
    cm = provider.per_test_case_context_manager()
    try:
        cm.__enter__()
    except BackendCannotProceed:
        # the provider is done with this test function, e.g. exhausted
        return []
    exception = None
    try:
        for _ in range(n_draws):
            values.append(getattr(provider, f"draw_{choice_type}")(**constraints))
    except StopTest as e:
        if data is None or e.testcounter != data.testcounter:  # pragma: no cover
            raise
        exception = e
    except BackendCannotProceed as e:
        exception = e
    except context_manager_exceptions as e:
        exception = e

    try:
        if exception is None:
            cm.__exit__(None, None, None)
        else:
            cm.__exit__(type(exception), exception, exception.__traceback__)
    except BackendCannotProceed:
        pass

    realize_exceptions: tuple[type[BaseException], ...] = (
        BackendCannotProceed,
        *context_manager_exceptions,
    )
    realized = []
    try:
        for value in values:
            realized.append(provider.realize(value))
    except realize_exceptions:
        pass
    return realized


def _run_findability_tests(
    Provider: type[PrimitiveProvider],
    provider_kw_strategy: SearchStrategy[dict[str, Any]],
    context_manager_exceptions: tuple[type[BaseException], ...],
    *,
    find_settings: Settings = Settings(max_examples=500),
) -> None:
    # For each case, check that *some* input to the provider - constructor
    # arguments, randomness, or number of draws - produces a value satisfying
    # the predicate, by asking Hypothesis to search for one with `find`. This
    # catches providers which are sound but cannot generate whole classes of
    # values, like a provider which never returns negative integers.

    @st.composite
    def drawn_values(draw, choice_type, constraints):
        values = []
        provider = None
        if Provider.lifetime != "test_case":
            provider = Provider(None, **draw(provider_kw_strategy))
        for _ in range(draw(st.integers(1, 25))):
            data = None
            if Provider.lifetime == "test_case":
                data = ConjectureData(
                    random=Random(draw(st.integers(0, 2**64 - 1))),
                    provider=Provider,
                    provider_kw=draw(provider_kw_strategy),
                )
                provider = data.provider
            values.extend(
                _run_one_test_case(
                    provider,
                    data,
                    choice_type,
                    constraints,
                    n_draws=draw(st.integers(1, 5)),
                    context_manager_exceptions=context_manager_exceptions,
                )
            )
        return values

    find_settings = Settings(
        find_settings,
        database=None,
        phases=[Phase.generate],
        verbosity=Verbosity.quiet,
        deadline=None,
    )
    missing = []
    for choice_type, constraints, description, predicate in _findability_cases():
        expected_type = _PYTHON_TYPES[choice_type]

        def condition(values, expected_type=expected_type, predicate=predicate):
            return any(isinstance(v, expected_type) and predicate(v) for v in values)

        try:
            find(
                drawn_values(choice_type, constraints),
                condition,
                settings=find_settings,
            )
        except NoSuchExample:
            missing.append(f"* {choice_type} {description}, from {constraints}")
        except FlakyFailure as e:  # pragma: no cover  # tested in nocover
            # providers drawing from real entropy may not reproduce the
            # discovered example on replay - but it was still found once.
            if not all(isinstance(sub, Found) for sub in e.exceptions):
                raise

    assert not missing, (
        f"{Provider.__name__} could not generate the following values, "
        "no matter what input we gave it:\n" + "\n".join(missing)
    )


class _ActionTreeNode:
    """
    A tree of conformance-test actions, where each node records the action
    taken at that point of a test case - a draw (with its constraints), a span
    call, or ending the test case - and draw nodes branch on the drawn value.

    Providers like hypothesis-crosshair require successive test cases of one
    test function to be deterministic: to make the same sequence of provider
    calls, up to control flow which branches on previously-drawn values. Real
    test functions have this property by construction. We enforce it by
    recording the first test case to reach each point in the tree, and
    replaying the recorded action for later test cases - which still explore
    new behavior whenever they draw a value we haven't seen at that point.
    """

    def __init__(self):
        self.action = None
        # the single successor, for span actions
        self.child = None
        # (value, successor) pairs, for concrete-valued draw actions
        self.branches = []


def run_conformance_test(
    Provider: type[PrimitiveProvider],
    *,
    provider_kw: dict[str, SearchStrategy[Any]] | None = None,
    context_manager_exceptions: Collection[type[BaseException]] = (),
    settings: Settings | None = None,
    check_findability: bool = True,
    _realize_objects: SearchStrategy[Any] = (
        st.from_type(object) | st.from_type(type).flatmap(st.from_type)
    ),
) -> None:
    """
    Test that the given ``Provider`` class conforms to the |PrimitiveProvider|
    interface.

    For instance, this tests that ``Provider`` does not return out of bounds
    choices from any of the ``draw_*`` methods, or violate other invariants
    which Hypothesis depends on. It also checks that the provider is able to
    generate a range of representative values for each choice type; for
    example, a provider whose ``draw_integer`` can never return a negative
    integer is not conformant.

    This function is intended to be called at test-time, not at runtime. It is
    provided by Hypothesis to make it easy for third-party backend authors to
    test their provider. Backend authors wishing to test their provider should
    include a test similar to the following in their test suite:

    .. code-block:: python

        from hypothesis.internal.conjecture.provider_conformance import run_conformance_test

        def test_conformance():
            run_conformance_test(MyProvider)

    If your provider takes required arguments in ``__init__`` besides the
    standard ``conjecturedata`` argument, pass ``provider_kw`` as a dictionary
    mapping each argument name to a strategy for values of that argument. For
    instance, ``BytestringProvider`` is tested with
    ``provider_kw={"bytestring": st.binary()}``.

    If your provider can raise control flow exceptions inside one of the five
    ``draw_*`` methods that are handled by your provider's
    ``per_test_case_context_manager``, pass a list of these exceptions types to
    ``context_manager_exceptions``. Otherwise, ``run_conformance_test`` will
    treat those exceptions as fatal errors. A provider may also raise
    ``StopTest`` by calling ``mark_overrun`` or ``mark_invalid`` on its own
    ``ConjectureData`` instance, for example if it has run out of entropy; this
    is always treated as expected control flow which ends the test case.

    Successive test cases in one run of the conformance state machine make the
    same sequence of provider calls, up to control flow which branches on
    previously-drawn values - mirroring the determinism of a real test
    function. Providers may rely on this, as e.g. hypothesis-crosshair does.

    Pass ``check_findability=False`` to disable checking that the provider can
    generate representative values. This is intended for unusual providers for
    which searching over instantiations is not meaningful, such as symbolic
    providers; most providers should leave it enabled.
    """
    context_manager_exceptions = tuple(context_manager_exceptions)
    realize_exceptions: tuple[type[BaseException], ...] = (
        BackendCannotProceed,
        *context_manager_exceptions,
    )
    provider_kw_strategy = st.fixed_dictionaries(provider_kw or {})

    class CopiesRealizationProvider(HypothesisProvider):
        avoid_realization = Provider.avoid_realization

    with with_register_backend("copies_realization", CopiesRealizationProvider):

        @Settings(
            settings,
            suppress_health_check=[HealthCheck.too_slow],
            backend="copies_realization",
        )
        class ProviderConformanceTest(RuleBasedStateMachine):
            @initialize(random=st.randoms(), kw=provider_kw_strategy)
            def setup(self, random, kw):
                self.provider = None
                self.data = None
                self._exhausted = False
                self._tree = _ActionTreeNode()
                self._start_test_case(random, kw)

            def _start_test_case(self, random, kw):
                if Provider.lifetime == "test_case":
                    self.data = ConjectureData(
                        random=random, provider=Provider, provider_kw=kw
                    )
                    self.provider = self.data.provider
                    self._instrument_draws()
                elif self.provider is None:
                    # test_function providers are instantiated once, and used
                    # for many test cases.
                    self.provider = Provider(None, **kw)
                    self._instrument_draws()

                self._nested_draws = 0
                self._draw_budget = math.inf
                self._drawn = []
                self._span_depth = 0
                self._node = self._tree
                self.context_manager = self.provider.per_test_case_context_manager()
                self.frozen = True
                try:
                    self.context_manager.__enter__()
                except BackendCannotProceed:
                    # the provider is done with this test function - for
                    # instance, a symbolic provider may have exhausted its
                    # search space - so don't start any more test cases.
                    self._exhausted = True
                    return
                self.frozen = False

            def _instrument_draws(self):
                # Count nested draws made by each top-level draw, so a provider
                # which loops forever drawing collection elements fails instead
                # of hanging. (Only draws which recurse via ConjectureData can
                # be counted; a spin which never draws is still a hang.)
                for name in _PYTHON_TYPES:
                    inner = getattr(self.provider, f"draw_{name}")

                    def wrapped(*args, _inner=inner, **kwargs):
                        self._nested_draws += 1
                        assert self._nested_draws <= self._draw_budget, (
                            f"made {self._nested_draws} nested draws during a "
                            "single top-level draw, which strongly suggests an "
                            "unbounded drawing loop in the provider"
                        )
                        return _inner(*args, **kwargs)

                    setattr(self.provider, f"draw_{name}", wrapped)

            def _step(self, requested):
                try:
                    self._perform(requested)
                except BaseException as e:
                    if not self.frozen:
                        # as in the engine, an exception escaping the test body
                        # propagates through per_test_case_context_manager
                        self._end_test_case(e, expected=False)
                    raise

            def _perform(self, requested):
                # Perform one action of the current test case. The first test
                # case to reach this point in the action tree records the
                # requested action; later test cases replay the recorded
                # action instead, so that the provider sees a deterministic
                # "test function" (see _ActionTreeNode).
                node = self._node
                if node.action is None:
                    if requested[0] == "draw":
                        _, choice_type, constraints = requested
                        constraints = dict(constraints)
                        del constraints["forced"]
                        requested = ("draw", choice_type, constraints)
                    node.action = requested
                kind = node.action[0]
                if kind == "freeze":
                    self._end_test_case()
                elif kind in ("span_start", "span_end"):
                    if kind == "span_start":
                        self._span_depth += 1
                        self.provider.span_start(node.action[1])
                    else:
                        self._span_depth -= 1
                        self.provider.span_end(node.action[1])
                    if node.child is None:
                        node.child = _ActionTreeNode()
                    self._node = node.child
                else:
                    assert kind == "draw"
                    choice = self._draw(*node.action[1:])
                    if self.frozen:
                        return
                    if Provider.avoid_realization:
                        # any comparison of a symbolic value is itself a
                        # solver-visible operation, so branching on drawn
                        # values would be nondeterministic across test cases.
                        # Follow a single straight-line schedule instead.
                        if node.child is None:
                            node.child = _ActionTreeNode()
                        self._node = node.child
                        return
                    for branch in node.branches:
                        if choice_equal(choice, branch[0]):
                            self._node = branch[1]
                            return
                    branch = (choice, _ActionTreeNode())
                    node.branches.append(branch)
                    self._node = branch[1]

            def _end_test_case(self, exception=None, *, expected=True):
                self.frozen = True
                if exception is None:
                    # mimicking the engine, spans are closed by data.freeze()
                    # before the context manager exits.
                    self._close_spans()
                    self.context_manager.__exit__(None, None, None)
                    self._check_realized_draws()
                    return

                if isinstance(exception, StopTest):
                    # data.freeze() has already closed our spans by the time
                    # StopTest propagates into the context manager.
                    self._close_spans()

                try:
                    suppressed = self.context_manager.__exit__(
                        type(exception), exception, exception.__traceback__
                    )
                except BackendCannotProceed:
                    suppressed = True

                if not expected:
                    # An exception the provider did not declare - such as a
                    # failing test, or one of our conformance checks - must
                    # propagate; suppressing it would hide failures from users.
                    assert not suppressed, (
                        f"{exception!r} was suppressed by "
                        "per_test_case_context_manager, which would hide "
                        "failing tests from users"
                    )
                    return

                # The engine handles StopTest and BackendCannotProceed itself,
                # so the context manager is free to pass them through - but an
                # exception the provider promised its context manager would
                # handle must not escape.
                if not isinstance(exception, (StopTest, BackendCannotProceed)):
                    assert suppressed, (
                        f"{exception!r} was in context_manager_exceptions, but "
                        "escaped per_test_case_context_manager unhandled"
                    )
                    # for exceptions other than StopTest, the engine calls
                    # data.freeze() - closing any open spans - after the
                    # context manager has exited.
                    self._close_spans()
                self._check_realized_draws()

            def _close_spans(self):
                while self._span_depth > 0:
                    self.provider.span_end(False)
                    self._span_depth -= 1

            def _check_realized_draws(self):
                # anything drawn during a test case must still conform after
                # being realized - this is the check that matters for providers
                # which draw symbolic values.
                for choice, choice_type, constraints in self._drawn:
                    try:
                        realized = self.provider.realize(choice)
                    except realize_exceptions:
                        continue
                    _assert_conforming(realized, choice_type, constraints)
                self._drawn = []

            def _draw(self, choice_type, constraints):
                weights = constraints.get("weights")
                weights_snapshot = None if weights is None else dict(weights)

                self._nested_draws = 0
                if choice_type in ("string", "bytes"):
                    # a conforming provider makes at most a few nested draws
                    # per collection element, plus slack for rejection sampling.
                    self._draw_budget = 3 * min(constraints["max_size"], 10_000) + 100
                else:
                    self._draw_budget = 100

                draw_func = getattr(self.provider, f"draw_{choice_type}")
                try:
                    choice = draw_func(**constraints)
                except StopTest as e:
                    # Providers may raise StopTest by concluding their own
                    # ConjectureData, e.g. via mark_overrun if they run out of
                    # entropy - but only their own, and only having concluded it.
                    if self.data is None or e.testcounter != self.data.testcounter:
                        raise  # pragma: no cover
                    assert (
                        self.data.frozen
                    ), "raised StopTest without concluding its ConjectureData"
                    assert self.data.status in (Status.OVERRUN, Status.INVALID)
                    note(f"provider concluded the test case ({self.data.status})")
                    self._end_test_case(e)
                    return None
                except BackendCannotProceed as e:
                    note("caught BackendCannotProceed")
                    self._end_test_case(e)
                    return None
                except context_manager_exceptions as e:
                    note(f"caught exception in context_manager_exceptions: {e!r}")
                    self._end_test_case(e)
                    return None

                if Provider.avoid_realization:
                    # repr of a symbolic value would realize it mid-test-case
                    note(f"drew {choice_type} <symbolic>")
                else:
                    note(f"drew {choice_type} {choice!r}")
                if not Provider.avoid_realization:
                    # symbolic providers may return proxy objects from draws;
                    # for everyone else, check the raw value immediately.
                    _assert_conforming(choice, choice_type, constraints)
                assert (
                    constraints.get("weights") == weights_snapshot
                ), "draw_integer mutated its weights argument"
                self._drawn.append((choice, choice_type, constraints))
                return choice

            @precondition(lambda self: not self.frozen)
            @rule(constraints=integer_constraints())
            def draw_integer(self, constraints):
                self._step(("draw", "integer", constraints))

            @precondition(lambda self: not self.frozen)
            @rule(constraints=float_constraints())
            def draw_float(self, constraints):
                self._step(("draw", "float", constraints))

            @precondition(lambda self: not self.frozen)
            @rule(constraints=bytes_constraints())
            def draw_bytes(self, constraints):
                self._step(("draw", "bytes", constraints))

            @precondition(lambda self: not self.frozen)
            @rule(constraints=string_constraints())
            def draw_string(self, constraints):
                self._step(("draw", "string", constraints))

            @precondition(lambda self: not self.frozen)
            @rule(constraints=boolean_constraints())
            def draw_boolean(self, constraints):
                self._step(("draw", "boolean", constraints))

            @precondition(lambda self: not self.frozen)
            @rule(label=st.integers())
            def span_start(self, label):
                self._step(("span_start", label))

            @precondition(lambda self: not self.frozen and self._span_depth > 0)
            @rule(discard=st.booleans())
            def span_end(self, discard):
                self._step(("span_end", discard))

            @precondition(lambda self: not self.frozen)
            @rule()
            def freeze(self):
                # phase-transition, mimicking data.freeze() at the end of a test case.
                self._step(("freeze",))

            @precondition(lambda self: self.frozen and not self._exhausted)
            @rule(random=st.randoms(), kw=provider_kw_strategy)
            def start_test_case(self, random, kw):
                # mimicking the engine starting another test case for the same
                # test function.
                self._start_test_case(random, kw)

            @precondition(lambda self: self.frozen)
            @rule(value=_realize_objects)
            def realize(self, value):
                # filter out nans and weirder things
                try:
                    assume(value == value)
                except Exception:
                    # e.g. value = Decimal('-sNaN')
                    assume(False)

                # if `value` is non-symbolic, the provider should return it
                # as-is - though it may raise BackendCannotProceed instead.
                try:
                    realized = self.provider.realize(value)
                except BackendCannotProceed:
                    return
                assert realized == value, (
                    f"realize({value!r}) returned {realized!r}, but non-symbolic "
                    "values must be returned as-is"
                )

            @precondition(lambda self: self.frozen)
            @rule(
                choices=st.lists(
                    st.booleans()
                    | st.integers()
                    | st.floats()
                    | st.text()
                    | st.binary()
                )
            )
            def replay_choices(self, choices):
                assert self.provider.replay_choices(tuple(choices)) is None

            @precondition(lambda self: self.frozen)
            @rule()
            def observe_test_case(self):
                observations = self.provider.observe_test_case()
                assert isinstance(observations, dict)
                # must be json-encodable (and therefore non-symbolic)
                json.dumps(observations)

            @precondition(lambda self: self.frozen)
            @rule(lifetime=st.sampled_from(["test_function", "test_case"]))
            def observe_information_messages(self, lifetime):
                observations = self.provider.observe_information_messages(
                    lifetime=lifetime
                )
                for observation in observations:
                    assert isinstance(observation, dict)
                    assert observation["type"] in ("info", "alert", "error")
                    assert isinstance(observation["title"], str)
                    assert isinstance(observation["content"], (str, dict))

            def teardown(self):
                if not hasattr(self, "frozen"):
                    # setup did not complete
                    return
                # finish any in-progress test case along its recorded path, so
                # that the provider sees a deterministic end to every test case
                while not self.frozen and self._node.action is not None:
                    self._step(self._node.action)
                if not self.frozen:
                    self._step(("freeze",))

        ProviderConformanceTest.TestCase().runTest()

    if check_findability:
        _run_findability_tests(
            Provider, provider_kw_strategy, context_manager_exceptions
        )
