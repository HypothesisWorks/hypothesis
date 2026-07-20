# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Search for choices to fill ValueHoles which inversion could not resolve.

When ``SearchStrategy._invert_with_holes`` leaves holes in a choice-sequence
prefix - for values from ``.map()``, ``@composite``, and other strategies
which cannot invert - the caller replays the prefix once to collect a
``HoleRecord`` per hole, then asks ``fill_candidates`` for candidate fills.
Each candidate is a list of one choice tuple per hole, proposed for all holes
simultaneously, so evaluating it costs a single test-function execution.

Two fillers sit behind that interface: a symbolic-execution probe using the
crosshair backend when it is installed, and a distance-guided search which
draws and mutates values cheaply (no test execution), scoring them by edit
distance between the canonical ``to_jsonable`` forms of the drawn value and
the hole's target value.
"""

import json
import math
from collections.abc import Iterator, Sequence
from difflib import SequenceMatcher
from random import Random
from typing import Any

from hypothesis._settings import HealthCheck, Phase, settings as Settings
from hypothesis.control import BuildContext
from hypothesis.errors import StopTest
from hypothesis.internal.conjecture.choice import (
    ChoiceT,
    HoleRecord,
    ValueHole,
    choices_key,
)
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.conjecture.engine import ConjectureRunner
from hypothesis.internal.conjecture.junkdrawer import deep_equal
from hypothesis.internal.conjecture.providers import AVAILABLE_PROVIDERS
from hypothesis.internal.escalation import InterestingOrigin
from hypothesis.strategies._internal.utils import to_jsonable

FillsT = list[tuple[ChoiceT, ...]]

# cheap candidate draws per hole per yielded fill-set
DRAWS_PER_ROUND = 16
# best candidates retained per hole
POOL_SIZE = 5
# stop after this many rounds which produced no new fill-set
BARREN_ROUNDS_LIMIT = 5
CROSSHAIR_MAX_EXAMPLES = 32


def fill_prefix(
    prefix: Sequence[ChoiceT | ValueHole], fills: FillsT
) -> tuple[ChoiceT, ...]:
    """Return ``prefix`` with each ValueHole replaced by the next fill."""
    it = iter(fills)
    out: list[ChoiceT] = []
    for choice in prefix:
        if isinstance(choice, ValueHole):
            out.extend(next(it))
        else:
            out.append(choice)
    return tuple(out)


def fill_candidates(
    records: Sequence[HoleRecord], random: Random, *, backend: str
) -> Iterator[FillsT]:
    """Yield candidate fills for all of ``records`` at once, best-first-ish.

    The caller owns execution: it splices each candidate into its prefix, runs
    the test function once, and stops on the first candidate that reproduces
    the failure it is looking for. Crosshair fills are attempted only when the
    test has opted into the crosshair backend - merely having it installed
    does not change behavior.
    """
    if backend == "crosshair":
        yield from crosshair_fills(records)
    yield from distance_fills(records, random)


def _canon(value: Any) -> str:
    try:
        return json.dumps(
            to_jsonable(value, avoid_realization=False), sort_keys=True, default=repr
        )
    except Exception:
        return repr(value)


def _distance(a: str, b: str) -> float:
    return 0.0 if a == b else 1.0 - SequenceMatcher(None, a, b).ratio()


def _coercions(value: Any) -> Iterator[ChoiceT]:
    """Plausible single-choice encodings of ``value``, as seed candidates."""
    if isinstance(value, (bool, int, float, str, bytes)):
        yield value
    for convert in (int, float, str):
        try:
            coerced = convert(value)  # type: ignore  # deliberately duck-typed
        except Exception:
            continue
        if not isinstance(coerced, bool):
            yield coerced


def _mutate_choice(value: ChoiceT, random: Random, hint: str) -> ChoiceT:
    """Return a small perturbation of a single choice. ``hint`` is the
    canonical form of the target value, used as an alphabet for string
    edits."""
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        delta = random.choice((random.randrange(1, 10), 1 << random.randrange(10)))
        return random.choice((value + delta, value - delta, value // 2, -value))
    if isinstance(value, float):
        if not math.isfinite(value):
            return 0.0
        delta = 2.0 ** random.randrange(-4, 10)
        return random.choice((value + delta, value - delta, value / 2, -value))
    if isinstance(value, str):
        # include case-swapped hint characters, for maps like str.upper
        alphabet = (hint + hint.swapcase()) or "0"
        if not value:
            return random.choice(alphabet)
        i = random.randrange(len(value))
        op = random.randrange(3)
        if op == 0:
            return value[:i] + random.choice(alphabet) + value[i:]
        if op == 1:
            return value[:i] + value[i + 1 :]
        return value[:i] + random.choice(alphabet) + value[i + 1 :]
    assert isinstance(value, bytes)
    if not value:
        return bytes([random.randrange(256)])
    i = random.randrange(len(value))
    return value[:i] + bytes([random.randrange(256)]) + value[i + 1 :]


class _HoleSearch:
    """Per-hole candidate pool for the distance-guided search."""

    def __init__(self, record: HoleRecord, random: Random) -> None:
        self.record = record
        self.random = random
        self.target = _canon(record.value)
        # (distance, choice count, insertion order, choices), kept sorted
        self.pool: list[tuple[float, int, int, tuple[ChoiceT, ...]]] = []
        self.seen: set[Any] = set()
        self.counter = 0
        # Seed with a partial claim of the target: an inner strategy may
        # invert the hole's value directly (e.g. the integers() inside
        # integers().map(f)), which often lands close to the target. Keep it
        # as a permanent mutation base so ties can't crowd it out of the pool.
        self.claim: tuple[ChoiceT, ...] | None = None
        self.consider(prefix=(ValueHole(record.value),))
        if self.pool:
            self.claim = self.pool[0][3]
        # Also seed coercions of the target to each choice type, which pays
        # off whenever the strategy transforms a single underlying choice
        # (e.g. integers().map(str) inverting "7" seeds the choice 7).
        for coerced in _coercions(record.value):
            self.consider(prefix=(coerced,))

    def consider(self, prefix: tuple[ChoiceT | ValueHole, ...] = ()) -> None:
        data = ConjectureData(random=self.random, prefix=prefix or None)
        try:
            with BuildContext(data, wrapped_test=lambda: None):
                value = data.draw(self.record.strategy)
        except (StopTest, Exception):
            # candidate generation is best-effort: a failed draw - whether an
            # unsatisfied filter, an overrun, or a strategy that cannot draw
            # outside a test - just contributes no candidate
            return
        choices = data.choices
        key = choices_key(choices)
        if key in self.seen:
            return
        self.seen.add(key)
        if deep_equal(value, self.record.value):
            distance = 0.0
        else:
            distance = _distance(_canon(value), self.target)
        self.counter += 1
        self.pool.append((distance, len(choices), self.counter, choices))
        # Prefer newer candidates among equal distances - a lateral move, as
        # the edit distance often can't order the approach path (e.g. [1, 4]
        # is no closer to [3, 4] than [0, 4] is) - and cap same-distance ties
        # so they can't crowd out diverse candidates. Since already-seen
        # candidates are never reconsidered, lateral drift cannot cycle.
        self.pool.sort(key=lambda entry: (entry[0], entry[1], -entry[2]))
        counts: dict[float, int] = {}
        kept = []
        for entry in self.pool:
            counts[entry[0]] = counts.get(entry[0], 0) + 1
            if counts[entry[0]] <= 2:
                kept.append(entry)
        self.pool = kept[:POOL_SIZE]

    def improve(self) -> None:
        # a systematic +-1 sweep around the current best candidate, so that
        # near-misses in numeric lattices converge deterministically
        if self.pool:
            base = self.pool[0][3]
            for i in range(min(len(base), 16)):
                value = base[i]
                if isinstance(value, bool):
                    neighbors: tuple[ChoiceT, ...] = (not value,)
                elif isinstance(value, (int, float)):
                    neighbors = (value + 1, value - 1)
                else:
                    continue
                for mutated in neighbors:
                    self.consider((*base[:i], mutated, *base[i + 1 :]))
        # then random exploration: fresh draws, and mutations of pool entries
        bases = [choices for *_, choices in self.pool if choices]
        if self.claim:
            bases.append(self.claim)
        for _ in range(DRAWS_PER_ROUND):
            prefix: tuple[ChoiceT | ValueHole, ...] = ()
            if bases and self.random.random() < 0.5:
                base = self.random.choice(bases)
                i = self.random.randrange(len(base))
                mutated = _mutate_choice(base[i], self.random, self.target)
                prefix = (*base[:i], mutated, *base[i + 1 :])
            self.consider(prefix)


def _combos(searches: Sequence[_HoleSearch]) -> Iterator[tuple[int, ...]]:
    # The per-hole best fills first, then single-hole deviations in order of
    # the deviating candidate's distance.
    yield (0,) * len(searches)
    bumps = sorted(
        (search.pool[j][0], i, j)
        for i, search in enumerate(searches)
        for j in range(1, len(search.pool))
    )
    for _, i, j in bumps:
        combo = [0] * len(searches)
        combo[i] = j
        yield tuple(combo)


def distance_fills(records: Sequence[HoleRecord], random: Random) -> Iterator[FillsT]:
    """Yield fill-sets from the distance-guided search, improving the per-hole
    candidate pools between yields, until we run out of new combinations."""
    searches = [_HoleSearch(record, random) for record in records]
    yielded: set[Any] = set()
    barren = 0
    while barren < BARREN_ROUNDS_LIMIT:
        for search in searches:
            search.improve()
        if any(not search.pool for search in searches):
            barren += 1
            continue
        for combo in _combos(searches):
            fills = [
                search.pool[j][3] for search, j in zip(searches, combo, strict=True)
            ]
            key = tuple(map(choices_key, fills))
            if key not in yielded:
                yielded.add(key)
                barren = 0
                yield fills
                break
        else:
            barren += 1


def crosshair_fills(records: Sequence[HoleRecord]) -> Iterator[FillsT]:
    """Yield at most one fill-set, found by drawing each hole's strategy
    symbolically under the crosshair backend and conditioning on equality
    with the hole's target value. Degrades silently to nothing when crosshair
    is unavailable or fails."""
    if "crosshair" not in AVAILABLE_PROVIDERS:
        return
    try:
        fills = _crosshair_probe(records)
    except (StopTest, Exception):
        return
    if fills is not None:
        yield fills


_PROBE_ORIGIN = InterestingOrigin(AssertionError, __file__, 0, (), ())


def _crosshair_probe(records: Sequence[HoleRecord]) -> FillsT | None:
    def probe(data: ConjectureData) -> None:
        matched = True
        # symbolic draws require the provider's own context, which the engine
        # leaves to the (usually user-test-executing) test function
        with (
            data.provider.per_test_case_context_manager(),
            BuildContext(data, wrapped_test=lambda: None),
        ):
            for record in records:
                # under crosshair this comparison conditions the path
                if data.draw(record.strategy) != record.value:
                    matched = False
                    break
        if matched:
            data.mark_interesting(_PROBE_ORIGIN)
        data.mark_invalid()

    runner = ConjectureRunner(
        probe,
        settings=Settings(
            backend="crosshair",
            database=None,
            deadline=None,
            max_examples=CROSSHAIR_MAX_EXAMPLES,
            phases=[Phase.generate],
            suppress_health_check=list(HealthCheck),
        ),
        random=Random(0),
    )
    runner.run()
    result = runner.interesting_examples.get(_PROBE_ORIGIN)
    if result is None:
        return None
    # Split the realized choices per hole by replaying them locally.
    data = ConjectureData.for_choices(result.choices)
    fills: FillsT = []
    with BuildContext(data, wrapped_test=lambda: None):
        for record in records:
            start = len(data.nodes)
            data.draw(record.strategy)
            fills.append(tuple(node.value for node in data.nodes[start:]))
    return fills
