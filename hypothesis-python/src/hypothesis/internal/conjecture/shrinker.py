# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
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

from __future__ import absolute_import, division, print_function

import heapq
from collections import Counter, defaultdict
from enum import Enum
from functools import partial
import math

import attr

from hypothesis.internal.compat import hbytes, hrange, int_from_bytes, int_to_bytes
from hypothesis.internal.conjecture.data import Overrun, Status
from hypothesis.internal.conjecture.floats import (
    DRAW_FLOAT_LABEL,
    float_to_lex,
    lex_to_float,
)
from hypothesis.internal.conjecture.shrinking import (
    Float,
    Integer,
    Length,
    Lexical,
    Ordering,
)
from hypothesis.internal.conjecture.shrinking.common import find_integer


def sort_key(buffer):
    """Returns a sort key such that "simpler" buffers are smaller than
    "more complicated" ones.

    We define sort_key so that x is simpler than y if x is shorter than y or if
    they have the same length and x < y lexicographically. This is called the
    shortlex order.

    The reason for using the shortlex order is:

    1. If x is shorter than y then that means we had to make fewer decisions
       in constructing the test case when we ran x than we did when we ran y.
    2. If x is the same length as y then replacing a byte with a lower byte
       corresponds to reducing the value of an integer we drew with draw_bits
       towards zero.
    3. We want a total order, and given (2) the natural choices for things of
       the same size are either the lexicographic or colexicographic orders
       (the latter being the lexicographic order of the reverse of the string).
       Because values drawn early in generation potentially get used in more
       places they potentially have a more significant impact on the final
       result, so it makes sense to prioritise reducing earlier values over
       later ones. This makes the lexicographic order the more natural choice.
    """
    return (len(buffer), buffer)


@attr.s(slots=True, cmp=False)
class ShrinkPass(object):
    generate_arguments = attr.ib()
    run_step = attr.ib()
    index = attr.ib()

    @property
    def name(self):
        return self.run_step.__name__


def derived_value(fn):
    """Decorator defining a property whose value is calculated from the
    current shrink target. Its results will be cached until the shrink target
    changes and recalculated the first time it is used with a new shrink target."""

    def calc(self):
        try:
            return self.value_cache[fn.__name__]
        except KeyError:
            return self.value_cache.setdefault(fn.__name__, fn(self))

    calc.__name__ = fn.__name__
    return property(calc)


def defines_shrink_pass(generate_arguments=lambda self: ((),)):
    def accept(fn):
        sp = ShrinkPass(
            generate_arguments=generate_arguments,
            run_step=fn,
            index=len(ALL_SHRINK_PASSES),
        )
        ALL_SHRINK_PASSES.append(sp)
        SHRINK_PASSES_BY_NAME[sp.name] = sp

        def run(self):
            self.run_shrink_pass(sp)

        run.__name__ = fn.__name__
        return run

    return accept


ALL_SHRINK_PASSES = []
SHRINK_PASSES_BY_NAME = {}


class Shrinker(object):
    """A shrinker is a child object of a ConjectureRunner which is designed to
    manage the associated state of a particular shrink problem. That is, we
    have some initial ConjectureData object and some property of interest
    that it satisfies, and we want to find a ConjectureData object with a
    shortlex (see sort_key above) smaller buffer that exhibits the same
    property.

    Currently the only property of interest we use is that the status is
    INTERESTING and the interesting_origin takes on some fixed value, but we
    may potentially be interested in other use cases later.
    However we assume that data with a status < VALID never satisfies the predicate.

    The shrinker keeps track of a value shrink_target which represents the
    current best known ConjectureData object satisfying the predicate.
    It refines this value by repeatedly running *shrink passes*, which are
    methods that perform a series of transformations to the current shrink_target
    and evaluate the underlying test function to find new ConjectureData
    objects. If any of these satisfy the predicate, the shrink_target
    is updated automatically. Shrinking runs until no shrink pass can
    improve the shrink_target, at which point it stops. It may also be
    terminated if the underlying engine throws RunIsComplete, but that
    is handled by the calling code rather than the Shrinker.

    =======================
    Designing Shrink Passes
    =======================

    Generally a shrink pass is just any function that calls
    cached_test_function and/or incorporate_new_buffer a number of times,
    but there are a couple of useful things to bear in mind.

    A shrink pass *makes progress* if running it changes self.shrink_target
    (i.e. it tries a shortlex smaller ConjectureData object satisfying
    the predicate). The desired end state of shrinking is to find a
    value such that no shrink pass can make progress, i.e. that we
    are at a local minimum for each shrink pass.

    In aid of this goal, the main invariant that a shrink pass much
    satisfy is that whether it makes progress must be deterministic.
    It is fine (encouraged even) for the specific progress it makes
    to be non-deterministic, but if you run a shrink pass, it makes
    no progress, and then you immediately run it again, it should
    never succeed on the second time. This allows us to stop as soon
    as we have run each shrink pass and seen no progress on any of
    them.

    This means that e.g. it's fine to try each of N deletions
    or replacements in a random order, but it's not OK to try N random
    deletions (unless you have already shrunk at least once, though we
    don't currently take advantage of this loophole).

    Shrink passes need to be written so as to be robust against
    change in the underlying shrink target. It is generally safe
    to assume that the shrink target does not change prior to the
    point of first modification - e.g. if you change no bytes at
    index ``i``, all examples whose start is ``<= i`` still exist,
    as do all blocks, and the data object is still of length
    ``>= i + 1``. This can only be violated by bad user code which
    relies on an external source of non-determinism.

    When the underlying shrink_target changes, shrink
    passes should not run substantially more test_function calls
    on success than they do on failure. Say, no more than a constant
    factor more. In particular shrink passes should not iterate to a
    fixed point.

    This means that shrink passes are often written with loops that
    are carefully designed to do the right thing in the case that no
    shrinks occurred and try to adapt to any changes to do a reasonable
    job. e.g. say we wanted to write a shrink pass that tried deleting
    each individual byte (this isn't an especially good choice and if
    we did we should use :class:`hypothesis.internal.conjecture.shrinking.Length`
    to do it anyway, but it leads to a simple illustrative example),
    we might do it by iterating over the buffer like so:

    .. code-block:: python

        i = 0
        while i < len(self.shrink_target.buffer):
            if not self.incorporate_new_buffer(
                self.shrink_target.buffer[: i] +
                self.shrink_target.buffer[i + 1 :]
            ):
                i += 1

    The reason for writing the loop this way is that i is always a
    valid index into the current buffer, even if the current buffer
    changes as a result of our actions. When the buffer changes,
    we leave the index where it is rather than restarting from the
    beginning, and carry on. This means that the number of steps we
    run in this case is always bounded above by the number of steps
    we would run if nothing works.

    Another thing to bear in mind about shrink pass design is that
    they should prioritise *progress*. If you have N operations that
    you need to run, you should try to order them in such a way as
    to avoid stalling, where you have long periods of test function
    invocations where no shrinks happen. This is bad because whenever
    we shrink we reduce the amount of work the shrinker has to do
    in future, and often speed up the test function, so we ideally
    wanted those shrinks to happen much earlier in the process.

    Sometimes stalls are inevitable of course - e.g. if the pass
    makes no progress, then the entire thing is just one long stall,
    but it's helpful to design it so that stalls are less likely
    in typical behaviour.

    The two easiest ways to do this are:

    * Just run the N steps in random order. As long as a
      reasonably large proportion of the operations suceed, this
      guarantees the expected stall length is quite short. The
      book keeping for making sure this does the right thing when
      it succeeds can be quite annoying. If you want this approach
      it may be useful to see if you can build it on top of
      :class:`~hypothesis.internal.conjecture.shrinking.Length`,
      which already does the right book keeping for you (as well
      as the adaptive logic below).
    * When you have any sort of nested loop, loop in such a way
      that both loop variables change each time. This prevents
      stalls which occur when one particular value for the outer
      loop is impossible to make progress on, rendering the entire
      inner loop into a stall.

    However, although progress is good, too much progress can be
    a bad sign! If you're *only* seeing successful reductions,
    that's probably a sign that you are making changes that are
    too timid. Two useful things to offset this:

    * It's worth writing shrink passes which are *adaptive*, in
      the sense that when operations seem to be working really
      well we try to bundle multiple of them together. This can
      often be used to turn what would be O(m) successful calls
      into O(log(m)).
    * It's often worth trying one or two special minimal values
      before trying anything more fine grained (e.g. replacing
      the whole thing with zero).

    """

    def __init__(self, engine, initial, predicate):
        """Create a shrinker for a particular engine, with a given starting
        point and predicate. When shrink() is called it will attempt to find an
        example for which predicate is True and which is strictly smaller than
        initial.

        Note that initial is a ConjectureData object, and predicate
        takes ConjectureData objects.
        """
        self.__engine = engine
        self.__predicate = predicate
        self.discarding_failed = False
        self.__shrinking_prefixes = set()
        self.value_cache = {}

        self.initial_size = len(initial.buffer)

        # We add a second level of caching local to the shrinker. This is a bit
        # of a hack. Ideally we'd be able to rely on the engine's functionality
        # for this. Doing it this way has two benefits: Firstly, the engine
        # does not currently cache overruns (and probably shouldn't, but could
        # recreate them on demand if necessary), and secondly Python dicts are
        # much faster than our pure Python tree-based lookups.
        self.__test_function_cache = {}

        # We keep track of the current best example on the shrink_target
        # attribute.
        self.shrink_target = None
        self.update_shrink_target(initial)
        self.shrinks = 0

        self.initial_calls = self.__engine.call_count
        self.pass_state_by_name = {}

    def pass_state(self, sp):
        sp = self.shrink_pass(sp)
        try:
            return self.pass_state_by_name[sp.name]
        except KeyError:
            pass

        return self.pass_state_by_name.setdefault(sp.name, (PassState(self, sp)))

    @property
    def calls(self):
        """Return the number of calls that have been made to the underlying
        test function."""
        return self.__engine.call_count

    def consider_new_buffer(self, buffer):
        """Returns True if after running this buffer the result would be
        the current shrink_target."""
        buffer = hbytes(buffer)
        return buffer.startswith(self.buffer) or self.incorporate_new_buffer(buffer)

    def incorporate_new_buffer(self, buffer):
        """Either runs the test function on this buffer and returns True if
        that changed the shrink_target, or determines that doing so would
        be useless and returns False without running it."""

        buffer = hbytes(buffer[: self.shrink_target.index])
        # Sometimes an attempt at lexicographic minimization will do the wrong
        # thing because the buffer has changed under it (e.g. something has
        # turned into a write, the bit size has changed). The result would be
        # an invalid string, but it's better for us to just ignore it here as
        # it turns out to involve quite a lot of tricky book-keeping to get
        # this right and it's better to just handle it in one place.
        if sort_key(buffer) >= sort_key(self.shrink_target.buffer):
            return False

        if self.shrink_target.buffer.startswith(buffer):
            return False

        previous = self.shrink_target
        self.cached_test_function(buffer)
        return previous is not self.shrink_target

    def incorporate_test_data(self, data):
        """Takes a ConjectureData or Overrun object updates the current
        shrink_target if this data represents an improvement over it,
        returning True if it is."""
        if data is Overrun or data is self.shrink_target:
            return
        if self.__predicate(data) and sort_key(data.buffer) < sort_key(
            self.shrink_target.buffer
        ):
            self.update_shrink_target(data)
            return True
        return False

    def cached_test_function(self, buffer):
        """Returns a cached version of the underlying test function, so
        that the result is either an Overrun object (if the buffer is
        too short to be a valid test case) or a ConjectureData object
        with status >= INVALID that would result from running this buffer."""

        buffer = hbytes(buffer)
        result = self.__engine.cached_test_function(buffer)
        self.incorporate_test_data(result)
        return result

    def debug(self, msg):
        self.__engine.debug(msg)

    @property
    def random(self):
        return self.__engine.random

    def shrink_pass(self, sp):
        if hasattr(sp, __name__):
            sp = sp.__name__
        if isinstance(sp, str):
            sp = SHRINK_PASSES_BY_NAME[sp]
        assert isinstance(sp, ShrinkPass)
        return sp

    def run_shrink_pass(self, sp):
        """Runs the function associated with ShrinkPass to a fixed point.

        Note that we only really use this for testing purposes at present."""
        sp = self.shrink_pass(sp)
        runner = PassState(self, sp)
        while runner.step():
            pass

    def shrink(self):
        """Run the full set of shrinks and update shrink_target.
        """
        # We assume that if an all-zero block of bytes is an interesting
        # example then we're not going to do better than that.
        # This might not technically be true: e.g. for integers() | booleans()
        # the simplest example is actually [1, 0]. Missing this case is fairly
        # harmless and this allows us to make various simplifying assumptions
        # about the structure of the data (principally that we're never
        # operating on a block of all zero bytes so can use non-zeroness as a
        # signpost of complexity).
        if not any(self.shrink_target.buffer) or self.incorporate_new_buffer(
            hbytes(len(self.shrink_target.buffer))
        ):
            return

        try:
            self.greedy_shrink()
        finally:
            if self.__engine.report_debug_info:

                def s(n):
                    return "s" if n != 1 else ""

                total_deleted = self.initial_size - len(self.shrink_target.buffer)

                self.debug("---------------------")
                self.debug("Shrink pass profiling")
                self.debug("---------------------")
                self.debug("")
                calls = self.__engine.call_count - self.initial_calls
                self.debug(
                    (
                        "Shrinking made a total of %d call%s "
                        "of which %d shrank. This deleted %d byte%s out of %d."
                    )
                    % (
                        calls,
                        s(calls),
                        self.shrinks,
                        total_deleted,
                        s(total_deleted),
                        self.initial_size,
                    )
                )
                for useful in [True, False]:
                    self.debug("")
                    if useful:
                        self.debug("Useful passes:")
                    else:
                        self.debug("Useless passes:")
                    self.debug("")
                    for p in sorted(
                        self.pass_state_by_name.values(),
                        key=lambda t: (-t.deletions, -t.shrinks, -t.calls, -t.runs, t.name),
                    ):
                        if p.calls == 0:
                            continue
                        if (p.shrinks != 0) != useful:
                            continue

                        steps = p.successes + p.failures

                        self.debug(
                            (
                                "  * %s ran %d step%s in %d run%s, making %d call%s of which "
                                "%d shrank, deleting %d byte%s."
                            )
                            % (
                                p.name,
                                steps,
                                s(steps),
                                p.runs,
                                s(p.runs),
                                p.calls,
                                s(p.calls),
                                p.shrinks,
                                p.deletions,
                                s(p.deletions),
                            )
                        )
                self.debug("")

    def greedy_shrink(self):
        """Run a full set of greedy shrinks (that is, ones that will only ever
        move to a better target) and update shrink_target appropriately.

        This method iterates to a fixed point and so is idempontent - calling
        it twice will have exactly the same effect as calling it once.
        """
        # Initial set of passes that are designed primarily to normalize the
        # shrink target. After this has run the same things should be
        # represented by the same bytes to a fairly large degree, and useful
        # values should ideally be repeated in many places. This increases the
        # cache hit rate and hopefully makes it easier for us to shrink later.
        main_passes = [
            "remove_discarded",
            "alphabet_minimize",
            "adaptive_example_deletion",
            "pass_to_descendant",
            "zero_examples",
            "propagate_examples",
            "reorder_examples",
            "minimize_duplicated_blocks",
            "minimize_floats",
            "minimize_individual_blocks",
            block_program("XX"),
            block_program("-XX"),
        ]

        self.fixate_passes(main_passes)

        # Passes that we hope don't do anything, because of some combination of
        # cost of running them and the fact that they're not usually that
        # useful.
        emergency_passes = [
            "minimize_block_pairs_retaining_sum",
            "shrink_offset_pairs",
            "example_deletion_with_block_lowering",
        ]
        self.fixate_passes(main_passes + emergency_passes)

    def fixate_passes(self, passes):
        """Run all of ``passes`` until none of them are able to make any
        progress."""
        states = [self.pass_state(sp) for sp in passes]
        runs = 0

        initial = self.shrink_target
        # We start by just round robinning between the shrink passes until
        # something works or all of the shrink passes are completed. This is
        # both much cheaper than running the full Thompson sampling and by
        # starting by running each shrink pass at least once we get to "prime
        # the pump" and give us some data on its behaviour.
        while self.shrink_target is initial:
            any_available = False
            for sp in states:
                if not sp.available:
                    continue
                any_available = True
                self.run_once(sp)

            if not any_available:
                return

        failures_to_reduce_length = 0

        while True:
            runs += 1

            # What follows is a slightly ersatz variant of Thompson sampling.
            # The idea of Thompson sampling is that you build up a Bayesian
            # model of the probability of success from pulling one of N levers,
            # and at each step draw a sample from your current posterior
            # distribution of the parameters and pick the lever with the
            # highest expected value given that parameter sample.
            
            # Applying this directly is complicated by the fact that we have a
            # rather more complex notion of success, and the cost of pulling
            # the lever is variable. So we adapt it in a couple not entirely
            # principled ways.

            initial = self.shrink_target

            candidates = [sp for sp in states if sp.available]

            if not candidates:
                return

            if not any(sp.successes > 0 for sp in candidates) or len(candidates) == 1:
                for sp in candidates:
                    self.run_once(sp)
                continue

            # If a pass is likely to delete data we just want to straight up
            # run it. Conceptually what's going on here is that we treat 
            # whether a pass deletes data as a Bernoulli distribution and give
            # it a a Beta(0.5, 0.5) prior, take the posterior based on our
            # previous runs, and draw a value p from that posterior. We then
            # simulate a Bernoulli(p) value. If it returns True, that's a
            # success in our simulated model, so we run the real model to see
            # if we actually get one.
            #
            # If we don't run the shrink pass in this step, we enqueue it for
            # consideration by the main Thompson sampling.

            scores = []

            for sp in candidates:
                p_shrink = self.random.betavariate(sp.param_lexical + sp.param_length, sp.param_fail)
                p_shrink_length = self.random.betavariate(sp.param_length, sp.param_lexical)
                scores.append(p_shrink * (
                    1 - p_shrink_length + 10 * math.log(len(self.buffer)) * p_shrink_length
                ))

            scored_pairs = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)

            self.debug("Scores: %s" % (', '.join("%s -> %r" % (sp.name, score) for score, sp in scored_pairs),))

            for _, sp in scored_pairs:
                calls = self.calls
                self.run_once(sp)
                if calls != self.calls:
                    break

    def run_once(self, sp):
        if not sp.available:
            return
        self.debug("Running %s" % (sp.name,))
        initial_calls = self.calls
        while self.calls == initial_calls:
            # If step returns False then we have run every possible
            # operation for this shrink pass since the last time the
            # shrink target has changed and there is thus nothing left
            # to do.
            if not sp.step():
                break

    @property
    def buffer(self):
        return self.shrink_target.buffer

    @property
    def blocks(self):
        return self.shrink_target.blocks

    @property
    def examples(self):
        return self.shrink_target.examples

    def all_block_bounds(self):
        return self.shrink_target.all_block_bounds()

    def pairs_for_intermingle(self):
        return [
            (i, j)
            for i in hrange(len(self.examples_by_type))
            for j in hrange(len(self.examples_by_type[i]))
        ] + [(i, None) for i in hrange(len(self.examples_by_type))]

    @defines_shrink_pass(pairs_for_intermingle)
    def reorder_examples(self, i, j):
        """This pass allows us to reorder the children of each example.

        For example, consider the following:

        .. code-block:: python

            import hypothesis.strategies as st
            from hypothesis import given

            @given(st.text(), st.text())
            def test_not_equal(x, y):
                assert x != y

        Without the ability to reorder x and y this could fail either with
        ``x=""``, ``y="0"``, or the other way around. With reordering it will
        reliably fail with ``x=""``, ``y="0"``.
        """
        self.intermingle_examples(
            i, j, lambda values: sorted(values, key=sort_key)
        )

    @defines_shrink_pass(pairs_for_intermingle)
    def propagate_examples(self, i, j):
        """Attempts to replace nearby larger examples with the value at i."""
        self.intermingle_examples(
            i, j, lambda values: [min(values, key=sort_key)] * len(values)
        )
        

    def intermingle_examples(self, i, j, calc_replacements):
        if i >= len(self.examples_by_type):
            return

        examples = self.examples_by_type[i]

        original = self.shrink_target
        values = [original.buffer[ex.start:ex.end] for ex in examples]

        def can_intermingle(a, b):
            if b > len(examples) or a < 0:
                return False
            replacements = calc_replacements(values[a:b])
            assert len(replacements) == b - a
            return self.consider_new_buffer(replace_all(
                original.buffer, [
                (ex.start, ex.end, r) for ex, r in zip(
                    examples[a:b], replacements
                )
            ]))

        if j is None:
            can_intermingle(0, len(examples))
            return

        if j >= len(self.examples_by_type[i]):
            return
        to_right = find_integer(lambda n: can_intermingle(j, j + n))
        assert to_right > 0
        if to_right > 1:
            to_left = find_integer(lambda n: can_intermingle(j - n, j + to_right))

    def descendant_pairs(self):
        examples_by_label = defaultdict(list)
        for ex in self.examples:
            examples_by_label[ex.label].append(ex)

        result = []
        for ex in self.examples:
            equivalent = examples_by_label[ex.label]
            if equivalent[-1] is ex:
                continue
            i = 0
            hi = len(equivalent) - 1
            while i + 1 < hi and equivalent[i] is not ex:
                mid = (i + hi) // 2
                ex2 = equivalent[mid]
                if ex2.index > ex.index:
                    hi = mid
                else:
                    i = mid
            for ex2 in equivalent[i + 1:]:
                if ex2.start >= ex.end:
                    break
                result.append((ex.index, ex2.index))
        return result

    @derived_value
    def descents(self):
        examples_by_label = defaultdict(list)
        for ex in self.examples:
            examples_by_label[ex.label].append(ex.index)

        result = []

        for ls in examples_by_label.values():
            if len(ls) <= 1:
                continue

            for i, exi in enumerate(ls[:-1]):
                ex = self.examples[exi]
                hi = len(ls) 
                lo = i + 1
                if self.examples[ls[lo]].start >= ex.end:
                    continue
                while lo + 1 < hi:
                    mid = (lo + hi) // 2
                    if self.examples[ls[mid]].start >= ex.end:
                        hi = mid
                    else:
                        lo = mid
                descents = ls[i + 1:hi]
                if descents:
                    result.append((exi, descents))
        return result

    @defines_shrink_pass(
        lambda self: [(i, j) for i, ls in enumerate(self.descents) for j in hrange(len(ls))]
    )
    def pass_to_descendant(self, a, b):
        """Attempt to replace each example with a descendant example.

        This is designed to deal with strategies that call themselves
        recursively. For example, suppose we had:

        binary_tree = st.deferred(
            lambda: st.one_of(
                st.integers(), st.tuples(binary_tree, binary_tree)))

        This pass guarantees that we can replace any binary tree with one of
        its subtrees - each of those will create an interval that the parent
        could validly be replaced with, and this pass will try doing that.

        This is pretty expensive - it takes O(len(intervals)^2) - so we run it
        late in the process when we've got the number of intervals as far down
        as possible.
        """

        try:
            i = self.descents[a][0]
            j = self.descents[a][1][b]
        except IndexError:
            return

        assert i < j
        ancestor = self.examples[i]
        descendant = self.examples[j]
        assert ancestor.label == descendant.label
        assert ancestor.start <= descendant.start <= descendant.end <= ancestor.end
        if ancestor.trivial:
            return
        self.incorporate_new_buffer(
            self.buffer[: ancestor.start]
            + self.buffer[descendant.start : descendant.end]
            + self.buffer[ancestor.end :]
        )

    def is_shrinking_block(self, i):
        """Checks whether block i has been previously marked as a shrinking
        block.

        If the shrink target has changed since i was last checked, will
        attempt to calculate if an equivalent block in a previous shrink
        target was marked as shrinking.
        """
        if not self.__shrinking_prefixes:
            return False
        try:
            return self.__shrinking_block_cache[i]
        except KeyError:
            pass
        t = self.shrink_target
        return self.__shrinking_block_cache.setdefault(
            i, t.buffer[: t.blocks[i].start] in self.__shrinking_prefixes
        )

    def is_payload_block(self, i):
        """A block is payload if it is entirely non-structural: We can tinker
        with its value freely and this will not affect the shape of the input
        language.

        This is mostly a useful concept when we're doing lexicographic
        minimimization on multiple blocks at once - by restricting ourself to
        payload blocks, we expect the shape of the language to not change
        under us (but must still guard against it doing so).
        """
        return not (self.is_shrinking_block(i) or self.shrink_target.blocks[i].forced)

    def lower_common_block_offset(self):
        """Sometimes we find ourselves in a situation where changes to one part
        of the byte stream unlock changes to other parts. Sometimes this is
        good, but sometimes this can cause us to exhibit exponential slow
        downs!

        e.g. suppose we had the following:

        m = draw(integers(min_value=0))
        n = draw(integers(min_value=0))
        assert abs(m - n) > 1

        If this fails then we'll end up with a loop where on each iteration we
        reduce each of m and n by 2 - m can't go lower because of n, then n
        can't go lower because of m.

        This will take us O(m) iterations to complete, which is exponential in
        the data size, as we gradually zig zag our way towards zero.

        This can only happen if we're failing to reduce the size of the byte
        stream: The number of iterations that reduce the length of the byte
        stream is bounded by that length.

        So what we do is this: We keep track of which blocks are changing, and
        then if there's some non-zero common offset to them we try and minimize
        them all at once by lowering that offset.

        This may not work, and it definitely won't get us out of all possible
        exponential slow downs (an example of where it doesn't is where the
        shape of the blocks changes as a result of this bouncing behaviour),
        but it fails fast when it doesn't work and gets us out of a really
        nastily slow case when it does.
        """
        if len(self.__changed_blocks) <= 1:
            return

        current = self.shrink_target

        blocked = [current.buffer[u:v] for u, v in current.all_block_bounds()]

        changed = [
            i
            for i in sorted(self.__changed_blocks)
            if not self.shrink_target.blocks[i].trivial
        ]

        if not changed:
            return

        ints = [int_from_bytes(blocked[i]) for i in changed]
        offset = min(ints)
        assert offset > 0

        for i in hrange(len(ints)):
            ints[i] -= offset

        def reoffset(o):
            new_blocks = list(blocked)
            for i, v in zip(changed, ints):
                new_blocks[i] = int_to_bytes(v + o, len(blocked[i]))
            return self.incorporate_new_buffer(hbytes().join(new_blocks))

        new_offset = Integer.shrink(offset, reoffset, random=self.random)
        if new_offset == offset:
            self.clear_change_tracking()

    @defines_shrink_pass(
        lambda self: [
            (i, j)
            for i in hrange(len(self.blocks))
            for j in hrange(i + 1, len(self.blocks))
        ]
    )
    def shrink_offset_pairs(self, i, j):
        """Lowers pairs of blocks that need to maintain a constant difference
        between their respective values.

        Before this shrink pass, two blocks explicitly offset from each
        other would not get minimized properly:
         >>> b = st.integers(0, 255)
         >>> find(st.tuples(b, b), lambda x: x[0] == x[1] + 1)
        (149,148)

        This expensive (O(n^2)) pass goes through every pair of non-zero
        blocks in the current shrink target and sees if the shrink
        target can be improved by applying a negative offset to both of them.
        """
        assert i < j
        if j >= len(self.blocks) or not (
            self.is_payload_block(i) and self.is_payload_block(j)
        ):
            return

        block_i = self.blocks[i]
        block_j = self.blocks[j]

        def is_non_zero_payload(block):
            return not block.all_zero and self.is_payload_block(block.index)

        if not (is_non_zero_payload(block_i) and is_non_zero_payload(block_j)):
            return

        def int_from_block(i):
            u, v = self.blocks[i].bounds
            block_bytes = self.shrink_target.buffer[u:v]
            return int_from_bytes(block_bytes)

        def block_len(i):
            return self.blocks[i].length

        # Try reoffseting every pair
        def reoffset_pair(pair, o):
            n = len(self.blocks)
            # Number of blocks may have changed, need to validate
            valid_pair = [
                p
                for p in pair
                if p < n and int_from_block(p) > 0 and self.is_payload_block(p)
            ]

            if len(valid_pair) < 2:
                return

            m = min([int_from_block(p) for p in valid_pair])

            new_blocks = [
                self.shrink_target.buffer[u:v]
                for u, v in self.shrink_target.all_block_bounds()
            ]
            for i in valid_pair:
                new_blocks[i] = int_to_bytes(int_from_block(i) + o - m, block_len(i))
            buffer = hbytes().join(new_blocks)
            return self.consider_new_buffer(buffer)

        value_i = int_from_block(i)
        value_j = int_from_block(j)

        offset = min(value_i, value_j)
        if reoffset_pair((i, j), 0):
            return
        find_integer(lambda n: n <= offset and reoffset_pair((i, j), offset - n))

    def mark_shrinking(self, blocks):
        """Mark each of these blocks as a shrinking block: That is, lowering
        its value lexicographically may cause less data to be drawn after."""
        t = self.shrink_target
        for i in blocks:
            if self.__shrinking_block_cache.get(i) is True:
                continue
            self.__shrinking_block_cache[i] = True
            prefix = t.buffer[: t.blocks[i].start]
            self.__shrinking_prefixes.add(prefix)

    def clear_change_tracking(self):
        self.__changed_blocks.clear()

    def mark_changed(self, i):
        self.__changed_blocks.add(i)

    def update_shrink_target(self, new_target):
        assert new_target.frozen
        if self.shrink_target is not None:
            current = self.shrink_target.buffer
            new = new_target.buffer
            assert sort_key(new) < sort_key(current)
            self.shrinks += 1
            if (
                len(new_target.blocks) != len(self.shrink_target.blocks)
                or new_target.all_block_bounds()
                != self.shrink_target.all_block_bounds()
            ):
                self.clear_change_tracking()
            else:
                for i, (u, v) in enumerate(self.shrink_target.all_block_bounds()):
                    if i not in self.__changed_blocks and current[u:v] != new[u:v]:
                        self.mark_changed(i)
        else:
            self.__changed_blocks = set()

        self.shrink_target = new_target
        self.__shrinking_block_cache = {}
        self.value_cache = {}

    def try_shrinking_blocks(self, blocks, b):
        """Attempts to replace each block in the blocks list with b. Returns
        True if it succeeded (which may include some additional modifications
        to shrink_target).

        May call mark_shrinking with b if this causes a reduction in size.

        In current usage it is expected that each of the blocks currently have
        the same value, although this is not essential. Note that b must be
        < the block at min(blocks) or this is not a valid shrink.

        This method will attempt to do some small amount of work to delete data
        that occurs after the end of the blocks. This is useful for cases where
        there is some size dependency on the value of a block.
        """
        initial_attempt = bytearray(self.shrink_target.buffer)
        for i, block in enumerate(blocks):
            if block >= len(self.blocks):
                blocks = blocks[:i]
                break
            u, v = self.blocks[block].bounds
            n = min(v - u, len(b))
            try:
                initial_attempt[v - n : v] = b[-n:]
            except IndexError:
                print(u, v, n, b)
                raise

        start = self.shrink_target.blocks[blocks[0]].start
        end = self.shrink_target.blocks[blocks[-1]].end

        initial_data = self.cached_test_function(initial_attempt)

        if initial_data is self.shrink_target:
            self.lower_common_block_offset()
            return True

        # If this produced something completely invalid we ditch it
        # here rather than trying to persevere.
        if initial_data.status < Status.VALID:
            return False

        # We've shrunk inside our group of blocks, so we have no way to
        # continue. (This only happens when shrinking more than one block at
        # a time).
        if len(initial_data.buffer) < v:
            return False

        lost_data = len(self.shrink_target.buffer) - len(initial_data.buffer)

        # If this did not in fact cause the data size to shrink we
        # bail here because it's not worth trying to delete stuff from
        # the remainder.
        if lost_data <= 0:
            return False

        self.mark_shrinking(blocks)

        # We now look for contiguous regions to delete that might help fix up
        # this failed shrink. We only look for contiguous regions of the right
        # lengths because doing anything more than that starts to get very
        # expensive. See example_deletion_with_block_lowering for where we
        # try to be more aggressive.
        regions_to_delete = {(end, end + lost_data)}

        for j in (blocks[-1] + 1, blocks[-1] + 2):
            if j >= min(len(initial_data.blocks), len(self.blocks)):
                continue
            # We look for a block very shortly after the last one that has
            # lost some of its size, and try to delete from the beginning so
            # that it retains the same integer value. This is a bit of a hyper
            # specific trick designed to make our integers() strategy shrink
            # well.
            r1, s1 = self.shrink_target.blocks[j].bounds
            r2, s2 = initial_data.blocks[j].bounds
            lost = (s1 - r1) - (s2 - r2)
            # Apparently a coverage bug? An assert False in the body of this
            # will reliably fail, but it shows up as uncovered.
            if lost <= 0 or r1 != r2:  # pragma: no cover
                continue
            regions_to_delete.add((r1, r1 + lost))

        for ex in self.shrink_target.examples:
            if ex.start > start:
                continue
            if ex.end <= end:
                continue

            replacement = initial_data.examples[ex.index]

            in_original = [c for c in ex.children if c.start >= end]

            in_replaced = [c for c in replacement.children if c.start >= end]

            if len(in_replaced) >= len(in_original) or not in_replaced:
                continue

            # We've found an example where some of the children went missing
            # as a result of this change, and just replacing it with the data
            # it would have had and removing the spillover didn't work. This
            # means that some of its children towards the right must be
            # important, so we try to arrange it so that it retains its
            # rightmost children instead of its leftmost.
            regions_to_delete.add(
                (in_original[0].start, in_original[-len(in_replaced)].start)
            )

        for u, v in sorted(regions_to_delete, key=lambda x: x[1] - x[0], reverse=True):
            try_with_deleted = bytearray(initial_attempt)
            del try_with_deleted[u:v]
            if self.incorporate_new_buffer(try_with_deleted):
                self.lower_common_block_offset()
                return True
        return False

    @defines_shrink_pass(lambda self: [()] if self.shrink_target.has_discards else [])
    def remove_discarded(self):
        """Try removing all bytes marked as discarded.

        This pass is primarily to deal with data that has been ignored while
        doing rejection sampling - e.g. as a result of an integer range, or a
        filtered strategy.

        Such data will also be handled by the adaptive_example_deletion pass,
        but that pass is necessarily more conservative and will try deleting
        each interval individually. The common case is that all data drawn and
        rejected can just be thrown away immediately in one block, so this pass
        will be much faster than trying each one individually when it works.
        """
        while self.shrink_target.has_discards:
            discarded = []

            for ex in self.shrink_target.examples:
                if ex.discarded and (not discarded or ex.start >= discarded[-1][-1]):
                    discarded.append((ex.start, ex.end))

            assert discarded

            attempt = bytearray(self.shrink_target.buffer)
            for u, v in reversed(discarded):
                del attempt[u:v]

            if not self.incorporate_new_buffer(attempt):
                break

    def run_shrinker_on_children(self, i, shrinker, **kwargs):
        """Run a Shrinker class on the children of each non-trivial
        example.
        """
        if i >= len(self.examples):
            return
        ex = self.examples[i]
        if ex.trivial:
            return
        st = self.shrink_target
        pieces = [st.buffer[c.start : c.end] for c in ex.children]
        if not pieces:
            pieces = [st.buffer[ex.start : ex.end]]
        prefix = st.buffer[: ex.start]
        suffix = st.buffer[ex.end :]
        shrinker.shrink(
            pieces,
            lambda ls: self.incorporate_new_buffer(prefix + hbytes().join(ls) + suffix),
            random=self.random,
            **kwargs
        )

    def example_indices(self):
        return [(i,) for i in hrange(len(self.examples))]

    @derived_value
    def example_partitions(self):
        endpoints_at_depth = defaultdict(set)
        max_depth = 0
        for ex in self.examples:
            endpoints_at_depth[ex.depth].add(ex.start)
            endpoints_at_depth[ex.depth].add(ex.end)
            max_depth = max(max_depth, ex.depth)
        distinct_partitions = [{0, len(self.buffer)}]
        for d in hrange(max_depth + 1):
            prev = distinct_partitions[-1]
            if not endpoints_at_depth[d].issubset(prev):
                distinct_partitions.append(prev | endpoints_at_depth[d])
        return [sorted(endpoints) for endpoints in distinct_partitions]

    @derived_value
    def examples_by_type(self):
        parts = defaultdict(list)
        for ex in self.shrink_target.examples:
            parts[(ex.depth, ex.label)].append(ex)
        result = [ls for ls in parts.values() if len(ls) > 1]
        result.sort(key=len, reverse=True)
        return result

    @defines_shrink_pass(
        lambda self: [
            (i, j)
            for i, ls in enumerate(self.example_partitions)
            for j in hrange(len(ls) - 1)
        ]
    )
    def adaptive_example_deletion(self, i, j):
        """Recursive deletion pass that tries to make the example located at
        example_index as small as possible. This is the main point at which we
        try to lower the size of the data.

        First attempts to replace the example with its minimal possible version
        using zero_example. If the example is trivial (either because of that
        or because it was anyway) then we assume there's nothing we can
        usefully do here and return early. Otherwise, we attempt to minimize it
        by deleting its children.

        If we do not make any successful changes, we recurse to the example's
        children and attempt the same there.
        """
        if i >= len(self.example_partitions) or j + 1 >= len(
            self.example_partitions[i]
        ):
            return
        buf = self.buffer
        endpoints = self.example_partitions[i]

        to_right = find_integer(
            lambda n: j + n < len(endpoints)
            and self.consider_new_buffer(buf[: endpoints[j]] + buf[endpoints[j + n] :])
        )

        if to_right > 0:
            to_right = find_integer(
                lambda n: n <= j
                and self.consider_new_buffer(
                    buf[: endpoints[j - n]] + buf[endpoints[j + to_right] :]
                )
            )

    @defines_shrink_pass(example_indices)
    def zero_examples(self, i):
        """Attempts to replace each example with an all-zero (and thus hopefully minimal)
        version of itself."""

        if i >= len(self.shrink_target.examples):
            return

        ex = self.shrink_target.examples[i]

        if ex.trivial:
            return
        u = ex.start
        v = ex.end
        attempt = self.cached_test_function(
            self.buffer[:u] + hbytes(v - u) + self.buffer[v:]
        )

        if attempt is Overrun:
            return

        in_replacement = attempt.examples[ex.index]
        used = in_replacement.length

        if (
            not self.__predicate(attempt)
            and in_replacement.end < len(attempt.buffer)
            and used < ex.length
        ):
            self.incorporate_new_buffer(
                self.buffer[:u] + hbytes(used) + self.buffer[v:]
            )

    def replace_examples(self, examples, replacements):
        replacements = list(replacements)
        assert len(examples) == len(replacements)
        

    def all_duplicated_blocks(self):
        """Returns all non zero suffixes of blocks that appear more than once
        in the current shrink target."""

        counts = Counter(
            non_zero_suffix(self.shrink_target.buffer[u:v])
            for u, v in self.all_block_bounds()
        )
        counts.pop(hbytes(), None)
        return [(block,) for block, count in counts.items() if count > 1]

    @defines_shrink_pass(all_duplicated_blocks)
    def minimize_duplicated_blocks(self, block):
        """Find blocks that have been duplicated in multiple places and attempt
        to minimize all of the duplicates simultaneously.

        This lets us handle cases where two values can't be shrunk
        independently of each other but can easily be shrunk together.
        For example if we had something like:

        ls = data.draw(lists(integers()))
        y = data.draw(integers())
        assert y not in ls

        Suppose we drew y = 3 and after shrinking we have ls = [3]. If we were
        to replace both 3s with 0, this would be a valid shrink, but if we were
        to replace either 3 with 0 on its own the test would start passing.

        It is also useful for when that duplication is accidental and the value
        of the blocks doesn't matter very much because it allows us to replace
        more values at once.
        """

        targets = [
            i
            for i, (u, v) in enumerate(self.all_block_bounds())
            if non_zero_suffix(self.shrink_target.buffer[u:v]) == block
        ]
        # This can happen if some blocks have been lost in the previous
        # shrinking.
        if len(targets) <= 1:
            return
        Lexical.shrink(
            block,
            lambda b: self.try_shrinking_blocks(targets, b),
            random=self.random,
            full=False,
        )

    def block_indices(self):
        return [(i,) for i in hrange(len(self.blocks))]


    @derived_value
    def float_examples(self):
        return [
            ex for ex in self.shrink_target.examples
            if (
                ex.label == DRAW_FLOAT_LABEL
                and len(ex.children) == 2
                and ex.children[0].length == 8
            )
        ]

    @defines_shrink_pass(lambda self: [(i,) for i in hrange(len(self.float_examples))])
    def minimize_floats(self, i):
        """Some shrinks that we employ that only really make sense for our
        specific floating point encoding that are hard to discover from any
        sort of reasonable general principle. This allows us to make
        transformations like replacing a NaN with an Infinity or replacing
        a float with its nearest integers that we would otherwise not be
        able to due to them requiring very specific transformations of
        the bit sequence.

        We only apply these transformations to blocks that "look like" our
        standard float encodings because they are only really meaningful
        there. The logic for detecting this is reasonably precise, but
        it doesn't matter if it's wrong. These are always valid
        transformations to make, they just don't necessarily correspond to
        anything particularly meaningful for non-float values.
        """
        if i >= len(self.float_examples):
            return
        ex = self.float_examples[i]
        if (
            ex.label == DRAW_FLOAT_LABEL
            and len(ex.children) == 2
            and ex.children[0].length == 8
        ):
            u = ex.children[0].start
            v = ex.children[0].end
            buf = self.shrink_target.buffer
            b = buf[u:v]
            f = lex_to_float(int_from_bytes(b))
            b2 = int_to_bytes(float_to_lex(f), 8)
            if b == b2 or self.consider_new_buffer(buf[:u] + b2 + buf[v:]):
                Float.shrink(
                    f,
                    lambda x: self.consider_new_buffer(
                        self.shrink_target.buffer[:u]
                        + int_to_bytes(float_to_lex(x), 8)
                        + self.shrink_target.buffer[v:]
                    ),
                    random=self.random,
                )

    @defines_shrink_pass(block_indices)
    def minimize_individual_blocks(self, i):
        """Attempt to minimize each block in sequence.

        This is the pass that ensures that e.g. each integer we draw is a
        minimum value. So it's the part that guarantees that if we e.g. do

        x = data.draw(integers())
        assert x < 10

        then in our shrunk example, x = 10 rather than say 97.
        """
        if i >= len(self.blocks):
            return
        u, v = self.blocks[i].bounds
        Lexical.shrink(
            self.shrink_target.buffer[u:v],
            lambda b: self.try_shrinking_blocks((i,), b),
            random=self.random,
            full=False,
        )

    def block_pairs(self):
        return [
            (i, j)
            for i in hrange(len(self.blocks))
            for j in hrange(i + 1, len(self.blocks))
        ]

    @defines_shrink_pass(
        lambda self: [
            (i, j)
            for i in hrange(len(self.shrink_target.blocks))
            for j in hrange(len(self.shrink_target.examples))
        ]
    )
    def example_deletion_with_block_lowering(self, i, j):
        """Sometimes we get stuck where there is data that we could easily
        delete, but it changes the number of examples generated, so we have to
        change that at the same time.

        We handle most of the common cases in try_shrinking_blocks which is
        pretty good at clearing out large contiguous blocks of dead space,
        but it fails when there is data that has to stay in particular places
        in the list.

        This pass exists as an emergency procedure to get us unstuck. For every
        example and every block not inside that example it tries deleting the
        example and modifying the block's value by one in either direction.
        """

        """Single step for example_deletion_with_block_lowering."""
        if i >= len(self.blocks) or j >= len(self.examples):
            return

        if not self.is_shrinking_block(i):
            return

        u, v = self.blocks[i].bounds

        n = int_from_bytes(self.shrink_target.buffer[u:v])
        if n == 0:
            return

        ex = self.shrink_target.examples[j]
        if ex.start < v or ex.length == 0:
            return

        buf = bytearray(self.shrink_target.buffer)
        buf[u:v] = int_to_bytes(n - 1, v - u)
        del buf[ex.start : ex.end]
        self.incorporate_new_buffer(buf)

    @defines_shrink_pass(block_pairs)
    def minimize_block_pairs_retaining_sum(self, i, j):
        """This pass minimizes pairs of blocks subject to the constraint that
        their sum when interpreted as integers remains the same. This allow us
        to normalize a number of examples that we would otherwise struggle on.
        e.g. consider the following:

        m = data.draw_bits(8)
        n = data.draw_bits(8)
        if m + n >= 256:
            data.mark_interesting()

        The ideal example for this is m=1, n=255, but we will almost never
        find that without a pass like this - we would only do so if we
        happened to draw n=255 by chance.

        This kind of scenario comes up reasonably often in the context of e.g.
        triggering overflow behaviour.
        """
        assert i < j
        if (
            j >= len(self.blocks)
            or not (self.is_payload_block(i) and self.is_payload_block(j))
            or self.blocks[i].all_zero
        ):
            return
        block_i = self.blocks[i]
        block_j = self.blocks[j]
        if block_i.length != block_j.length:
            return

        u, v = block_i.bounds
        r, s = block_j.bounds

        m = int_from_bytes(self.shrink_target.buffer[u:v])
        n = int_from_bytes(self.shrink_target.buffer[r:s])

        def trial(x, y):
            if s > len(self.shrink_target.buffer):
                return False
            attempt = bytearray(self.shrink_target.buffer)
            try:
                attempt[u:v] = int_to_bytes(x, v - u)
                attempt[r:s] = int_to_bytes(y, s - r)
            except OverflowError:
                return False
            return self.consider_new_buffer(attempt)

        # We first attempt to move 1 from m to n. If that works
        # then we treat that as a sign that it's worth trying
        # a more expensive minimization. But if m was already 1
        # (we know it's > 0) then there's no point continuing
        # because the value there is now zero.
        if trial(m - 1, n + 1) and m > 1:
            m = int_from_bytes(self.shrink_target.buffer[u:v])
            n = int_from_bytes(self.shrink_target.buffer[r:s])

            tot = m + n
            find_integer(lambda k: k <= m and trial(m - k, m + k))


    @defines_shrink_pass(lambda self: [(c,) for c in sorted(set(self.buffer))])
    def alphabet_minimize(self, c):
        """Attempts to minimize the "alphabet" - the set of bytes that
        are used in the representation of the current buffer. The main
        benefit of this is that it significantly increases our cache hit rate
        by making things that are equivalent more likely to have the same
        representation, but it's also generally a rather effective "fuzzing"
        step that gives us a lot of good opportunities to slip to a smaller
        representation of the same bug.
        """

        buf = self.buffer

        if c not in buf:
            return

        def can_replace_with(d):
            if d < 0:
                return False

            if self.consider_new_buffer(hbytes([d if b == c else b for b in buf])):
                if d <= 1:
                    # For small values of d if this succeeds we take this
                    # as evidence that it is worth doing a a bulk replacement
                    # where we replace all values which are close
                    # to c but smaller with d as well. This helps us substantially
                    # in cases where we have a lot of "dead" bytes that don't really do
                    # much, as it allows us to replace many of them in one go rather
                    # than one at a time. An example of where this matters is
                    # test_minimize_multiple_elements_in_silly_large_int_range_min_is_not_dupe
                    # in test_shrink_quality.py
                    def replace_range(k):
                        if k > c:
                            return False

                        def should_replace_byte(b):
                            return c - k <= b <= c and d < b

                        return self.consider_new_buffer(
                            hbytes([d if should_replace_byte(b) else b for b in buf])
                        )

                    find_integer(replace_range)
                return True

        if (
            # If we cannot replace the current byte with its predecessor,
            # assume it is already minimal and continue on. This ensures
            # we make no more than one call per distinct byte value in the
            # event that no shrinks are possible here.
            not can_replace_with(c - 1)
            # We next try replacing with 0 or 1. If this works then
            # there is nothing else to do here.
            or can_replace_with(0)
            or can_replace_with(1)
            # Finally we try to replace with c - 2 before going on to the
            # binary search so that in cases which were already nearly
            # minimal we don't do log(n) extra work.
            or not can_replace_with(c - 2)
        ):
            return

        # Now binary search to find a small replacement.

        # Invariant: We cannot replace with lo, we can replace with hi.
        lo = 1
        hi = c - 2
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if can_replace_with(mid):
                hi = mid
            else:
                lo = mid


BLOCK_PROGRAMS = {}


def block_program(description):
    """Mini-DSL for block rewriting. A sequence of commands that will be run
    over all contiguous sequences of blocks of the description length in order.
    Commands are:

        * ".", keep this block unchanged
        * "-", subtract one from this block.
        * "0", replace this block with zero
        * "X", delete this block

    If a command does not apply (currently only because it's - on a zero
    block) the block will be silently skipped over. As a side effect of
    running a block program its score will be updated.
    """
    try:
        return BLOCK_PROGRAMS[description]
    except KeyError:
        pass

    def run(self, i):
        n = len(description)
        if i + n > len(self.blocks):
            return
        attempt = bytearray(self.shrink_target.buffer)
        for k, d in reversed(list(enumerate(description))):
            j = i + k
            u, v = self.blocks[j].bounds
            if d == "-":
                value = int_from_bytes(attempt[u:v])
                if value == 0:
                    return
                else:
                    attempt[u:v] = int_to_bytes(value - 1, v - u)
            elif d == "X":
                del attempt[u:v]
            else:  # pragma: no cover
                assert False, "Unrecognised command %r" % (d,)
        self.incorporate_new_buffer(attempt)

    run.command = description
    run.__name__ = "block_program(%r)" % (description,)
    defines_shrink_pass(Shrinker.block_indices)(run)

    return BLOCK_PROGRAMS.setdefault(description, run.__name__)


def non_zero_suffix(b):
    i = 0
    while i < len(b) and b[i] == 0:
        i += 1
    return b[i:]


class PassState(object):
    """Wraps a single shrink pass and manages the state required to run it.

    In particular tracks:

        * Remaining steps to run.
        * Information that allows it to determine that it's not worth running
          more steps because the current shrink target is a fixed point of this
          pass.
        * Statistics about the total effect of running this shrink pass so far,
          used for reporting at the end.
    """

    def __init__(self, shrinker, shrink_pass):
        self.__prev = None
        self.__queue = []
        self.shrink_pass = shrink_pass
        self.__shrinker = shrinker

        self.successes = 0
        self.failures = 0
        self.runs = 0
        self.calls = 0
        self.shrinks = 0
        self.deletions = 0
        self.steps = 0
        self.length_reducing_steps = 0
        self.fractional_reductions = []
        self.lexical_reducing_steps = 0
        self.successful_this_run = False

        self.param_length = 1.0
        self.param_lexical = 1.0
        self.param_fail = 1.0
        self.normalize_parameters()

    def __repr__(self):
        return "PassState(%s)" % (self.shrink_pass.name,)

    @property
    def name(self):
        return self.shrink_pass.name

    @property
    def available(self):
        self.__refill_if_necessary()
        return len(self.__queue) > 0

    def __refill_if_necessary(self):
        if not self.__queue and self.__prev is not self.__shrinker.shrink_target:
            self.runs += 1
            self.__prev = self.__shrinker.shrink_target
            self.__queue = list(self.shrink_pass.generate_arguments(self.__shrinker))
            self.__shrinker.random.shuffle(self.__queue)
            self.successful_this_run = False
            self.normalize_parameters()

    def normalize_parameters(self):
        tot = self.param_length + self.param_lexical + self.param_fail
        self.param_length /= tot
        self.param_lexical /= tot
        self.param_fail /= tot
        
    def step(self):
        """Either run a single step of the shrink pass and return True,
        or return False if the current shrink target is a fixed point for this
        pass."""
        self.__refill_if_necessary()

        if self.__queue:
            args = self.__queue.pop()
            self.__shrinker.debug("%s(%s)" % (self.name, ", ".join(map(repr, args))))
            initial = self.__shrinker.shrink_target
            initial_shrinks = self.__shrinker.shrinks
            initial_calls = self.__shrinker.calls
            size = len(self.__shrinker.shrink_target.buffer)
            try:
                self.shrink_pass.run_step(self.__shrinker, *args)
            finally:
                calls = self.__shrinker.calls - initial_calls
                if calls > 0:
                    self.steps += 1
                    if initial is self.__shrinker.shrink_target:
                        self.failures += 1
                        self.param_fail += 1
                    else:
                        self.successful_this_run = True
                        self.successes += 1
                        if len(initial.buffer) > len(self.__shrinker.shrink_target.buffer):
                            self.length_reducing_steps += 1
                            self.fractional_reductions.append((len(initial.buffer) - len(self.__shrinker.shrink_target.buffer)) / len(initial.buffer))
                            self.param_length += 1
                        else:
                            self.lexical_reducing_steps += 1
                            self.param_lexical += 1
                shrinks = self.__shrinker.shrinks - initial_shrinks
                deletions = size - len(self.__shrinker.shrink_target.buffer)

                self.calls += calls
                self.shrinks += shrinks
                self.deletions += deletions
            return True
        else:
            return False


def replace_all(buffer, replacements):
    prev = 0
    result = bytearray()
    for u, v, r in replacements:
        result.extend(buffer[prev:u])
        result.extend(r)
        prev = v
    result.extend(buffer[prev:])
    return result


def interleave(ls):
    iters = list(map(iter, ls))

    result = []
    while iters:
        next_iters = []
        for it in iters:
            try:
                result.append(next(it))
                next_iters.append(it)
            except StopIteration:
                pass
        iters = next_iters
    return result
