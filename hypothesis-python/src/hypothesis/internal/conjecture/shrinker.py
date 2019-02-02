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
from functools import total_ordering

import attr

from hypothesis.internal.compat import hbytes, hrange, int_from_bytes, int_to_bytes
from hypothesis.internal.conjecture.data import Overrun, Status
from hypothesis.internal.conjecture.floats import (
    DRAW_FLOAT_LABEL,
    float_to_lex,
    lex_to_float,
)
from hypothesis.internal.conjecture.shrinking import Float, Integer, Lexical, Ordering
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
    each individual byte (this isn't an especially good choice,
    but it leads to a simple illustrative example), we might do it
    by iterating over the buffer like so:

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
      it succeeds can be quite annoying.
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

    def default_passes(self):
        """Returns the list of shrink passes that are always safe to run,
        in a good order to run them in.

        These mostly have time
        complexity that is at most O(n log(n)) in the size of the underlying
        buffer. pass_to_descendant is an exception in that it technically
        has worst case complexity O(n^2), but it is rare for it to hit
        that case and generally runs very few operations at all.
        """
        return [
            "alphabet_minimize",
            "pass_to_descendant",
            "zero_examples",
            "adaptive_example_deletion",
            "reorder_examples",
            "minimize_floats",
            "minimize_duplicated_blocks",
            "minimize_individual_blocks",
        ]

    def emergency_passes(self):
        """Returns the list of emergency shrink passes,
        in a good order to run them in.

        Emergency passes are ones that we hope don't do anything
        very useful. The ideal scenario is that we run all of our
        default passes to a fixed point, then we run all of the
        emergency passes and they do nothing and we're finished.
        This is because they're either a bit weird and designed to
        handle some special case that doesn't come up very often,
        or because they're very expensive, or both.
        """
        return [
            block_program("-XX"),
            block_program("XX"),
            "example_deletion_with_block_lowering",
        ]

    def derived_value(fn):
        """It's useful during shrinking to have access to derived values of
        the current shrink target.

        This decorator allows you to define these as cached properties. They
        are calculated once, then cached until the shrink target changes, then
        recalculated the next time they are used."""

        def accept(self):
            try:
                return self.__derived_values[fn.__name__]
            except KeyError:
                return self.__derived_values.setdefault(fn.__name__, fn(self))

        accept.__name__ = fn.__name__
        return property(accept)

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
        self.__derived_values = {}

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

        self.current_pass_depth = 0
        self.passes_by_name = {}
        self.clear_passes()

        for p in self.default_passes():
            self.add_new_pass(p)

        for p in self.emergency_passes():
            self.add_new_pass(p, classification=PassClassification.AVOID)

        self.add_new_pass(
            "lower_common_block_offset", classification=PassClassification.SPECIAL
        )

    def clear_passes(self):
        """Reset all passes on the shrinker, leaving it in a blank state.

        This is mostly useful for testing.
        """
        # Note that we deliberately do not clear passes_by_name. This means
        # that we can still look up and explicitly run the standard passes,
        # they just won't be avaiable by default.

        self.passes = []
        self.passes_awaiting_requeue = []
        self.pass_queues = {c: [] for c in PassClassification}

        self.known_programs = set()

    def add_new_pass(self, run, classification=None):
        """Creates a shrink pass corresponding to calling ``run(self)``"""
        if classification is None:
            classification = PassClassification.CANDIDATE
        if isinstance(run, str):
            run = getattr(Shrinker, run)
        p = ShrinkPass(
            pass_function=run, index=len(self.passes), classification=classification
        )
        if hasattr(run, "command"):
            self.known_programs.add(run.command)
        self.passes.append(p)
        self.passes_awaiting_requeue.append(p)
        self.passes_by_name[p.name] = p
        return p

    def shrink_pass(self, name):
        """Return the ShrinkPass object for the pass with the given name."""
        if hasattr(Shrinker, name) and name not in self.passes_by_name:
            self.add_new_pass(name, classification=PassClassification.SPECIAL)
        return self.passes_by_name[name]

    def requeue_passes(self):
        """Move all passes from passes_awaiting_requeue to their relevant
        queues."""
        while self.passes_awaiting_requeue:
            p = self.passes_awaiting_requeue.pop()
            heapq.heappush(self.pass_queues[p.classification], p)

    def has_queued_passes(self, classification):
        """Checks if any shrink passes are currently enqued under this
        classification (note that there may be passes with this classification
        currently awaiting requeue)."""
        return len(self.pass_queues[classification]) > 0

    def pop_queued_pass(self, classification):
        """Pop and run a single queued pass with this classification."""
        sp = heapq.heappop(self.pass_queues[classification])
        self.passes_awaiting_requeue.append(sp)
        self.run_shrink_pass(sp)

    def run_queued_until_change(self, classification):
        """Run passes with this classification until there are no more or one
        of them succeeds in shrinking the target."""
        initial = self.shrink_target
        while self.has_queued_passes(classification) and self.shrink_target is initial:
            self.pop_queued_pass(classification)
        return self.shrink_target is not initial

    def run_one_queued_pass(self, classification):
        """Run a single queud pass with this classification (if there are
        any)."""
        if self.has_queued_passes(classification):
            self.pop_queued_pass(classification)

    def run_queued_passes(self, classification):
        """Run all queued passes with this classification."""
        while self.has_queued_passes(classification):
            self.pop_queued_pass(classification)

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
            self.__shrinking_block_cache = {}
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

    def run_shrink_pass(self, sp):
        """Runs the function associated with ShrinkPass sp and updates the
        relevant metadata.

        Note that sp may or may not be a pass currently associated with
        this shrinker. This does not handle any requeing that is
        required.
        """
        if isinstance(sp, str):
            sp = self.shrink_pass(sp)

        self.debug("Shrink Pass %s" % (sp.name,))

        initial_shrinks = self.shrinks
        initial_calls = self.calls
        size = len(self.shrink_target.buffer)
        try:
            sp.pass_function(self)
        finally:
            calls = self.calls - initial_calls
            shrinks = self.shrinks - initial_shrinks
            deletions = size - len(self.shrink_target.buffer)

            sp.calls += calls
            sp.shrinks += shrinks
            sp.deletions += deletions
            sp.runs += 1
            self.debug("Shrink Pass %s completed." % (sp.name,))

        # Complex state machine alert! A pass run can either succeed (we made
        # at least one shrink) or fail (we didn't). This changes the pass's
        # current classification according to the following possible
        # transitions:
        #
        # CANDIDATE -------> HOPEFUL
        #     |                 ^
        #     |                 |
        #     v                 v
        #   AVOID ---------> DUBIOUS
        #
        # From best to worst we want to run HOPEFUL, CANDIDATE, DUBIOUS, AVOID.
        # We will try any one of them if we have to but we want to prioritise.
        #
        # When a run succeeds, a pass will follow an arrow to a better class.
        # When it fails, it will follow an arrow to a worse one.
        # If no such arrow is available, it stays where it is.
        #
        # We also have the classification SPECIAL for passes that do not get
        # run as part of the normal process.
        previous = sp.classification

        # If the pass didn't actually do anything we don't reclassify it. This
        # is for things like remove_discarded which often are inapplicable.
        if calls > 0 and sp.classification != PassClassification.SPECIAL:
            if shrinks == 0:
                if sp.successes > 0:
                    sp.classification = PassClassification.DUBIOUS
                else:
                    sp.classification = PassClassification.AVOID
            else:
                sp.successes += 1
                if sp.classification == PassClassification.AVOID:
                    sp.classification = PassClassification.DUBIOUS
                else:
                    sp.classification = PassClassification.HOPEFUL
            if previous != sp.classification:
                self.debug(
                    "Reclassified %s from %s to %s"
                    % (sp.name, previous.name, sp.classification.name)
                )

    def shrink(self):
        """Run the full set of shrinks and update shrink_target.

        This method is "mostly idempotent" - calling it twice is unlikely to
        have any effect, though it has a non-zero probability of doing so.
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
                        self.passes,
                        key=lambda t: (-t.calls, -t.runs, t.deletions, t.shrinks),
                    ):
                        if p.calls == 0:
                            continue
                        if (p.shrinks != 0) != useful:
                            continue

                        self.debug(
                            (
                                "  * %s ran %d time%s, making %d call%s of which "
                                "%d shrank, deleting %d byte%s."
                            )
                            % (
                                p.name,
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
        while self.single_greedy_shrink_iteration():
            self.run_shrink_pass("lower_common_block_offset")

    def single_greedy_shrink_iteration(self):
        """Performs a single run through each greedy shrink pass, but does not
        loop to achieve a fixed point."""
        initial = self.shrink_target

        # What follows is a slightly delicate dance. What we want to do is try
        # to ensure that:
        #
        # 1. If it is possible for us to be deleting data, we should be.
        # 2. We do not end up repeating a lot of passes uselessly.
        # 3. We do not want to run expensive or useless passes if we can
        #    possibly avoid doing so.

        self.requeue_passes()

        self.run_shrink_pass("remove_discarded")

        # First run the entire set of solid passes (ones that have previously
        # made changes). It's important that we run all of them, not just one,
        # as typically each pass may unlock others.
        self.run_queued_passes(PassClassification.HOPEFUL)

        # While our solid passes are successfully shrinking the buffer, we can
        # just keep doing that (note that this is a stronger condition than
        # just making shrinks - it's a much better sense of progress. We can
        # make only O(n) length reductions but we can make exponentially many
        # shrinks).
        if len(self.buffer) < len(initial.buffer):
            return True

        # If we're stuck on length reductions then we pull in one candiate pass
        # (if there are any).
        # This should hopefully help us unlock any local minima that were
        # starting to reduce the utility of the previous solid passes.
        self.run_one_queued_pass(PassClassification.CANDIDATE)

        # We've pulled in a new candidate pass (or have no candidate passes
        # left) and are making shrinks with the solid passes, so lets just
        # keep on doing that.
        if self.shrink_target is not initial:
            return True

        # We're a bit stuck, so it's time to try some new passes.
        for classification in [
            # First we try rerunning every pass we've previously seen succeed.
            PassClassification.DUBIOUS,
            # If that didn't work, we pull in some new candidate passes.
            PassClassification.CANDIDATE,
            # If that still didn't work, we now pull out all the stops and
            # bring in the desperation passes. These are either passes that
            # started as CANDIDATE but we have never seen work, or ones that
            # are so expensive that they begin life as AVOID.
            PassClassification.AVOID,
        ]:
            if self.run_queued_until_change(classification):
                return True

        assert self.shrink_target is initial

        return False

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

    def pass_to_descendant(self):
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
        for ex in self.each_non_trivial_example():
            st = self.shrink_target
            descendants = sorted(
                set(
                    st.buffer[d.start : d.end]
                    for d in self.shrink_target.examples
                    if d.start >= ex.start
                    and d.end <= ex.end
                    and d.length < ex.length
                    and d.label == ex.label
                ),
                key=sort_key,
            )

            for d in descendants:
                if self.incorporate_new_buffer(
                    self.buffer[: ex.start] + d + self.buffer[ex.end :]
                ):
                    break

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
        self.__derived_values = {}

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
            n = min(self.blocks[block].length, len(b))
            initial_attempt[v - n : v] = b[-n:]

        start = self.shrink_target.blocks[blocks[0]].start
        end = self.shrink_target.blocks[blocks[-1]].end

        initial_data = self.cached_test_function(initial_attempt)

        if initial_data.status == Status.INTERESTING:
            return initial_data is self.shrink_target

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
                return True
        return False

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

    def each_non_trivial_example(self):
        """Iterates over all non-trivial examples in the current shrink target,
        with care taken to ensure that every example yielded is current.

        Makes the assumption that no modifications will be made to the
        shrink target prior to the currently yielded example. If this
        assumption is violated this will probably raise an error, so
        don't do that.
        """
        stack = [0]

        while stack:
            target = stack.pop()
            if isinstance(target, tuple):
                parent, i = target
                parent = self.shrink_target.examples[parent]
                example_index = parent.children[i].index
            else:
                example_index = target

            ex = self.shrink_target.examples[example_index]

            if ex.trivial:
                continue

            yield ex

            ex = self.shrink_target.examples[example_index]

            if ex.trivial:
                continue

            for i in range(len(ex.children)):
                stack.append((example_index, i))

    def example_wise_shrink(self, shrinker, **kwargs):
        """Runs a sequence shrinker on the children of each example."""
        for ex in self.each_non_trivial_example():
            st = self.shrink_target
            pieces = [st.buffer[c.start : c.end] for c in ex.children]
            if not pieces:
                pieces = [st.buffer[ex.start : ex.end]]
            prefix = st.buffer[: ex.start]
            suffix = st.buffer[ex.end :]
            shrinker.shrink(
                pieces,
                lambda ls: self.incorporate_new_buffer(
                    prefix + hbytes().join(ls) + suffix
                ),
                random=self.random,
                **kwargs
            )

    @derived_value
    def endpoints_by_depth(self):
        """Defines a series of increasingly fine grained boundaries
        to partition the current buffer, based on the depth of examples.
        Each element of the result is the set of endpoints of examples
        less than or equal to some depth (less than or equal to account
        for the fact that there might be blocks below that depth and if
        we ignore those we'll get bad boundaries).

        This is primarily useful for adaptive_example_deletion."""
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
        return [sorted(endpoints) for endpoints in distinct_partitions[1:]]

    def adaptive_example_deletion(self):
        """Attempts to delete every example from the test case.

        That is, it is logically equivalent to trying ``self.buffer[:ex.start] +
        self.buffer[ex.end:]`` for every example ``ex``. The order in which
        examples are tried is randomized, and when deletion is successful it
        will attempt to adapt to delete more than one example at a time.
        """
        indices = [
            (i, j)
            for i, ls in enumerate(self.endpoints_by_depth)
            for j in hrange(len(ls))
        ]
        self.random.shuffle(indices)

        for i, j in indices:
            if i >= len(self.endpoints_by_depth):
                continue
            partition = self.endpoints_by_depth[i]
            # No point in trying to delete the last element because that will always
            # give us a prefix.
            if j >= len(partition) - 1:
                continue

            def delete_region(a, b):
                assert a <= j <= b
                if a < 0 or b >= len(partition) - 1:
                    return False
                return self.consider_new_buffer(
                    self.buffer[: partition[a]] + self.buffer[partition[b] :]
                )

            to_right = find_integer(lambda n: delete_region(j, j + n))

            if to_right > 0:
                find_integer(lambda n: delete_region(j - n, j + to_right))

    def zero_examples(self):
        """Attempt to replace each example with a minimal version of itself."""
        for ex in self.each_non_trivial_example():
            u = ex.start
            v = ex.end
            attempt = self.cached_test_function(
                self.buffer[:u] + hbytes(v - u) + self.buffer[v:]
            )

            if attempt is Overrun:
                continue

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

    def minimize_duplicated_blocks(self):
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

        def canon(b):
            i = 0
            while i < len(b) and b[i] == 0:
                i += 1
            return b[i:]

        counts = Counter(
            canon(self.shrink_target.buffer[u:v]) for u, v in self.all_block_bounds()
        )
        counts.pop(hbytes(), None)
        blocks = [buffer for buffer, count in counts.items() if count > 1]

        blocks.sort(reverse=True)
        blocks.sort(key=lambda b: counts[b] * len(b), reverse=True)
        for block in blocks:
            targets = [
                i
                for i, (u, v) in enumerate(self.all_block_bounds())
                if canon(self.shrink_target.buffer[u:v]) == block
            ]
            # This can happen if some blocks have been lost in the previous
            # shrinking.
            if len(targets) <= 1:
                continue

            Lexical.shrink(
                block,
                lambda b: self.try_shrinking_blocks(targets, b),
                random=self.random,
                full=False,
            )

    def minimize_floats(self):
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
        i = 0
        while i < len(self.shrink_target.examples):
            ex = self.shrink_target.examples[i]
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
            i += 1

    def minimize_individual_blocks(self):
        """Attempt to minimize each block in sequence.

        This is the pass that ensures that e.g. each integer we draw is a
        minimum value. So it's the part that guarantees that if we e.g. do

        x = data.draw(integers())
        assert x < 10

        then in our shrunk example, x = 10 rather than say 97.
        """
        i = len(self.blocks) - 1
        while i >= 0:
            u, v = self.blocks[i].bounds
            Lexical.shrink(
                self.shrink_target.buffer[u:v],
                lambda b: self.try_shrinking_blocks((i,), b),
                random=self.random,
                full=False,
            )
            i -= 1

    def example_deletion_with_block_lowering(self):
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
        i = 0
        while i < len(self.shrink_target.blocks):
            if not self.is_shrinking_block(i):
                i += 1
                continue

            u, v = self.blocks[i].bounds

            j = 0
            while j < len(self.shrink_target.examples):
                n = int_from_bytes(self.shrink_target.buffer[u:v])
                if n == 0:
                    break
                ex = self.shrink_target.examples[j]
                if ex.start < v or ex.length == 0:
                    j += 1
                    continue

                buf = bytearray(self.shrink_target.buffer)
                buf[u:v] = int_to_bytes(n - 1, v - u)
                del buf[ex.start : ex.end]
                if not self.incorporate_new_buffer(buf):
                    j += 1

            i += 1

    def reorder_examples(self):
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
        self.example_wise_shrink(Ordering, key=sort_key)

    def alphabet_minimize(self):
        """Attempts to minimize the "alphabet" - the set of bytes that
        are used in the representation of the current buffer. The main
        benefit of this is that it significantly increases our cache hit rate
        by making things that are equivalent more likely to have the same
        representation, but it's also generally a rather effective "fuzzing"
        step that gives us a lot of good opportunities to slip to a smaller
        representation of the same bug.
        """

        # We perform our normalization in a random order. This helps give
        # us a good mix of likely to succeed (e.g. rare bytes) vs likely
        # to have a large impact (e.g. common bytes) without having to
        # have any idea which bytes are which.
        all_bytes = list(hrange(256))
        self.random.shuffle(all_bytes)

        for c in all_bytes:
            buf = self.buffer

            if c not in buf:
                continue

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
                                hbytes(
                                    [d if should_replace_byte(b) else b for b in buf]
                                )
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
                continue

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

    def run(self):
        n = len(description)
        i = 0
        while i + n <= len(self.shrink_target.blocks):
            attempt = bytearray(self.shrink_target.buffer)
            failed = False
            for k, d in reversed(list(enumerate(description))):
                j = i + k
                block = self.blocks[j]
                u, v = block.bounds
                if d == "-":
                    value = int_from_bytes(attempt[u:v])
                    if value == 0:
                        failed = True
                        break
                    else:
                        attempt[u:v] = int_to_bytes(value - 1, block.length)
                elif d == "X":
                    del attempt[u:v]
                else:  # pragma: no cover
                    assert False, "Unrecognised command %r" % (d,)
            if failed or not self.incorporate_new_buffer(attempt):
                i += 1

    run.command = description
    run.__name__ = "block_program(%r)" % (description,)
    return run


class PassClassification(Enum):
    CANDIDATE = 0
    HOPEFUL = 1
    DUBIOUS = 2
    AVOID = 3
    SPECIAL = 4


@total_ordering
@attr.s(slots=True, cmp=False)
class ShrinkPass(object):
    pass_function = attr.ib()
    index = attr.ib()

    classification = attr.ib(default=PassClassification.CANDIDATE)

    successes = attr.ib(default=0)
    runs = attr.ib(default=0)
    calls = attr.ib(default=0)
    shrinks = attr.ib(default=0)
    deletions = attr.ib(default=0)

    @property
    def failures(self):
        return self.runs - self.successes

    @property
    def name(self):
        return self.pass_function.__name__

    def __eq__(self, other):
        return self.index == other.index

    def __hash__(self):
        return hash(self.index)

    def __lt__(self, other):
        return self.key() < other.key()

    def key(self):
        # Smaller is better.
        return (self.runs, self.failures, self.calls, self.index)
