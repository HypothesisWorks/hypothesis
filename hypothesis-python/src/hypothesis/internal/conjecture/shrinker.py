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
from collections import Counter
from enum import Enum
from functools import total_ordering

import attr

from hypothesis.internal.compat import hbytes, hrange, int_from_bytes, int_to_bytes
from hypothesis.internal.conjecture.data import Overrun, Status
from hypothesis.internal.conjecture.shrinking import Integer, Length, Lexical, Ordering
from hypothesis.internal.conjecture.shrinking.common import find_integer


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
                u, v = self.blocks[j].bounds
                if d == "-":
                    value = int_from_bytes(attempt[u:v])
                    if value == 0:
                        failed = True
                        break
                    else:
                        attempt[u:v] = int_to_bytes(value - 1, v - u)
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


class Shrinker(object):
    """A shrinker is a child object of a ConjectureRunner which is designed to
    manage the associated state of a particular shrink problem.

    Currently the only shrink problem we care about is "interesting and with a
    particular interesting_origin", but this is abstracted into a general
    purpose predicate for more flexibility later - e.g. we are likely to want
    to shrink with respect to a particular coverage target later.

    Data with a status < VALID may be assumed not to satisfy the predicate.

    The expected usage pattern is that this is only ever called from within the
    engine.
    """

    DEFAULT_PASSES = [
        "alphabet_minimize",
        "pass_to_descendant",
        "zero_examples",
        "adaptive_example_deletion",
        "reorder_examples",
        "minimize_duplicated_blocks",
        "minimize_individual_blocks",
    ]

    EMERGENCY_PASSES = [
        block_program("-XX"),
        block_program("XX"),
        "example_deletion_with_block_lowering",
        "shrink_offset_pairs",
        "minimize_block_pairs_retaining_sum",
    ]

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

        for p in Shrinker.DEFAULT_PASSES:
            self.add_new_pass(p)

        for p in Shrinker.EMERGENCY_PASSES:
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

    def add_new_pass(self, run, classification=PassClassification.CANDIDATE):
        """Creates a shrink pass corresponding to calling ``run(self)``"""
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
        return self.__engine.call_count

    def consider_new_buffer(self, buffer):
        buffer = hbytes(buffer)
        return buffer.startswith(self.buffer) or self.incorporate_new_buffer(buffer)

    def incorporate_new_buffer(self, buffer):
        buffer = hbytes(buffer[: self.shrink_target.index])
        try:
            existing = self.__test_function_cache[buffer]
        except KeyError:
            pass
        else:
            return self.incorporate_test_data(existing)

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
        if data is Overrun:
            return
        self.__test_function_cache[data.buffer] = data
        if self.__predicate(data) and sort_key(data.buffer) < sort_key(
            self.shrink_target.buffer
        ):
            self.update_shrink_target(data)
            self.__shrinking_block_cache = {}
            return True
        return False

    def cached_test_function(self, buffer):
        buffer = hbytes(buffer)
        try:
            return self.__test_function_cache[buffer]
        except KeyError:
            pass
        result = self.__engine.cached_test_function(buffer)
        self.incorporate_test_data(result)
        self.__test_function_cache[buffer] = result
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

    def all_block_bounds(self):
        return self.shrink_target.all_block_bounds()

    def each_pair_of_blocks(self, accept_first, accept_second):
        """Yield each pair of blocks ``(a, b)``, such that ``a.index <
        b.index``, but only if ``accept_first(a)`` and ``accept_second(b)`` are
        both true."""

        # Iteration order here is significant: Rather than fixing i and looping
        # over each j, then doing the same, etc. we iterate over the gap between
        # i and j and then over i. The reason for this is that it ensures that
        # we try a different value for i and j on each iteration of the inner
        # loop. This stops us from stalling if we happen to hit on a value of i
        # where nothing useful can be done.
        #
        # In the event that nothing works, this doesn't help and we still make
        # the same number of calls, but by ensuring that we make progress we
        # have more opportunities to make shrinks that speed up the tests or
        # that reduce the number of viable shrinks at the next gap size because
        # we've lowered some values.
        offset = 1
        while offset < len(self.blocks):
            i = 0
            while i + offset < len(self.blocks):
                j = i + offset
                block_i = self.blocks[i]
                block_j = self.blocks[j]
                if accept_first(block_i) and accept_second(block_j):
                    yield (block_i, block_j)
                i += 1
            offset += 1

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

    def shrink_offset_pairs(self):
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
            return self.incorporate_new_buffer(buffer)

        def is_non_zero_payload(block):
            return not block.all_zero and self.is_payload_block(block.index)

        for block_i, block_j in self.each_pair_of_blocks(
            is_non_zero_payload, is_non_zero_payload
        ):
            i = block_i.index
            j = block_j.index

            value_i = int_from_block(i)
            value_j = int_from_block(j)

            offset = min(value_i, value_j)
            Integer.shrink(
                offset, lambda o: reoffset_pair((i, j), o), random=self.random
            )

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

    def adaptive_example_deletion(self):
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
        self.example_wise_shrink(Length)

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

    def minimize_block_pairs_retaining_sum(self):
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
        for block_i, block_j in self.each_pair_of_blocks(
            lambda block: (self.is_payload_block(block.index) and not block.all_zero),
            lambda block: self.is_payload_block(block.index),
        ):
            if block_i.length != block_j.length:
                continue

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
                return self.incorporate_new_buffer(attempt)

            # We first attempt to move 1 from m to n. If that works
            # then we treat that as a sign that it's worth trying
            # a more expensive minimization. But if m was already 1
            # (we know it's > 0) then there's no point continuing
            # because the value there is now zero.
            if trial(m - 1, n + 1) and m > 1:
                m = int_from_bytes(self.shrink_target.buffer[u:v])
                n = int_from_bytes(self.shrink_target.buffer[r:s])

                tot = m + n
                Integer.shrink(m, lambda x: trial(x, tot - x), random=self.random)

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
        for c in range(255, 0, -1):
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


def sort_key(buffer):
    return (len(buffer), buffer)
