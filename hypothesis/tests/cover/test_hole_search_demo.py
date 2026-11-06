# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""A deliberately minimal demonstration of the hole-filling search that the
inversion design enables, expected to be replaced by a real search pass.

The design contributes the starting skeletons: ``_invert`` returns an
encoding whose concrete choices pin down structure, with holes (and their
candidate partial fills) where a value could not be encoded. The search
evaluates candidates only by running them through a draw - the claim site
degrades unresolved holes to misalignments, so even a hole-bearing prefix
yields a full concrete choice sequence and value from one test invocation -
and hillclimbs single-choice mutations on a crude repr distance.
"""

import difflib
import itertools
from random import Random

from hypothesis import strategies as st
from hypothesis.control import BuildContext
from hypothesis.errors import StopTest
from hypothesis.internal.conjecture.choice import Impossible, ValueHole
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.conjecture.junkdrawer import equal_values


def _run(strategy, prefix, rng):
    """One test invocation: draw the strategy from prefix, and return the
    value produced along with the concrete choices which produced it."""
    data = ConjectureData(random=Random(rng.getrandbits(64)), prefix=tuple(prefix))
    try:
        with BuildContext(data, wrapped_test=lambda: None):
            value = data.draw(strategy)
    except (StopTest, Exception):
        # overruns, invalid data, or a mutated choice the strategy rejects
        return None
    return value, data.choices


def _skeletons(encoding):
    """Every way of splicing candidate partial fills into holes, recursively.
    A hole may also stay put, degrading to a misalignment when run."""
    options = [
        (
            [(c,), *(s for candidate in c.candidates for s in _skeletons(candidate))]
            if isinstance(c, ValueHole)
            else [(c,)]
        )
        for c in encoding
    ]
    return [
        tuple(itertools.chain.from_iterable(combo))
        for combo in itertools.product(*options)
    ]


def _mutate(choices, rng):
    i = rng.randrange(len(choices))
    c = choices[i]
    if isinstance(c, bool):
        new = not c
    elif isinstance(c, int):
        new = rng.choice(
            [c - 10, c - 2, c - 1, c + 1, c + 2, c + 10, rng.randrange(-127, 128)]
        )
    elif isinstance(c, float):
        new = c + rng.choice([-1.0, -0.5, 0.5, 1.0])
    elif isinstance(c, str):
        j = rng.randrange(len(c) + 1)
        new = c[:j] + chr(rng.randrange(32, 127)) + c[j + 1 :]
    else:
        assert isinstance(c, bytes)
        new = bytes(_mutate(list(c), rng))
    return (*choices[:i], new, *choices[i + 1 :])


def search(strategy, target, *, seed=0, max_steps=5000):
    """Choices making strategy produce target, or None if the search fails."""
    encoding = strategy._invert(target)
    if isinstance(encoding, Impossible):
        return None
    rng = Random(seed)

    def score(value):
        matcher = difflib.SequenceMatcher(None, repr(value), repr(target))
        return 1.0 - matcher.ratio()

    best = None
    for skeleton in _skeletons(encoding):
        if (result := _run(strategy, skeleton, rng)) is None:
            continue
        value, choices = result
        if equal_values(value, target):
            return choices
        if best is None or score(value) < best[0]:
            best = (score(value), choices)
    if best is None:
        return None
    best_score, best_choices = best
    for _ in range(max_steps):
        if (result := _run(strategy, _mutate(best_choices, rng), rng)) is None:
            continue
        value, choices = result
        if equal_values(value, target):
            return choices
        # accept improvements, and sideways moves to drift across the
        # plateaus of a very crude score
        if score(value) <= best_score:
            best_score, best_choices = score(value), choices
    return None


def _assert_searchable(strategy, target):
    choices = search(strategy, target)
    assert choices is not None
    replayed, _ = _run(strategy, choices, Random(0))
    assert equal_values(replayed, target)


def test_search_fills_an_unanalysable_map_hole():
    _assert_searchable(st.integers().map(lambda x: x * 2 + 1), 41)


def test_search_seeds_from_one_of_branch_candidates():
    # the union's hole carries the list branch's partial encoding, handing
    # the search a skeleton with the list structure already concrete
    strategy = st.booleans() | st.lists(st.integers().map(lambda x: x * 3))
    _assert_searchable(strategy, [9, 12])


def test_search_fills_a_hole_inside_concrete_structure():
    _assert_searchable(st.tuples(st.booleans(), st.integers().map(chr)), (True, "K"))
