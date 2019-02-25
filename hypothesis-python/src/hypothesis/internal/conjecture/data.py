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

from enum import IntEnum

import attr

from hypothesis.errors import Frozen, InvalidArgument, StopTest
from hypothesis.internal.compat import (
    benchmark_time,
    bit_length,
    hbytes,
    hrange,
    int_from_bytes,
    int_to_bytes,
    text_type,
    unicode_safe_repr,
)
from hypothesis.internal.conjecture.utils import calc_label_from_name
from hypothesis.internal.escalation import mark_for_escalation
from hypothesis.utils.conventions import UniqueIdentifier

TOP_LABEL = calc_label_from_name("top")
DRAW_BYTES_LABEL = calc_label_from_name("draw_bytes() in ConjectureData")


class ExtraInformation(object):
    """A class for holding shared state on a ``ConjectureData`` that should
    be added to the final ``ConjectureResult``."""

    def __repr__(self):
        return "ExtraInformation(%s)" % (
            ", ".join(["%s=%r" % (k, v) for k, v in self.__dict__.items()]),
        )

    def has_information(self):
        return bool(self.__dict__)


class Status(IntEnum):
    OVERRUN = 0
    INVALID = 1
    VALID = 2
    INTERESTING = 3

    def __repr__(self):
        return "Status.%s" % (self.name,)


@attr.s(slots=True)
class Example(object):
    """Examples track the hierarchical structure of draws from the byte stream,
    within a single test run.

    Examples are created to mark regions of the byte stream that might be
    useful to the shrinker, such as:
    - The bytes used by a single draw from a strategy.
    - Useful groupings within a strategy, such as individual list elements.
    - Strategy-like helper functions that aren't first-class strategies.
    - Each lowest-level draw of bits or bytes from the byte stream.
    - A single top-level example that spans the entire input.

    Example-tracking allows the shrinker to try "high-level" transformations,
    such as rearranging or deleting the elements of a list, without having
    to understand their exact representation in the byte stream.
    """

    # Depth of this example in the example tree. The top-level example has a
    # depth of 0.
    depth = attr.ib(repr=False)

    # A label is an opaque value that associates each example with its
    # approximate origin, such as a particular strategy class or a particular
    # kind of draw.
    label = attr.ib()

    # Index of this example inside the overall list of examples.
    index = attr.ib()

    # Index of the parent of this example, or None if this is the root.
    parent = attr.ib()

    start = attr.ib()
    end = attr.ib(default=None)

    # An example is "trivial" if it only contains forced bytes and zero bytes.
    # All examples start out as trivial, and then get marked non-trivial when
    # we see a byte that is neither forced nor zero.
    trivial = attr.ib(default=True, repr=False)

    # True if we believe that the shrinker should be able to delete this
    # example completely, without affecting the value produced by its enclosing
    # strategy. Typically set when a rejection sampler decides to reject a
    # generated value and try again.
    discarded = attr.ib(default=None, repr=False)

    # List of child examples, represented as indices into the example list.
    children = attr.ib(default=attr.Factory(list), repr=False)

    # We access length a lot, and Python is annoyingly bad at basic integer
    # arithmetic, so it makes sense to cache this on a field for speed
    # reasons. It also reduces allocation, though most of the integers
    # allocated from this should be easily collected garbage and/or
    # small enough to be interned.
    length = attr.ib(init=False, repr=False)


@attr.s(slots=True, frozen=True)
class Block(object):
    """Blocks track the flat list of lowest-level draws from the byte stream,
    within a single test run.

    Block-tracking allows the shrinker to try "low-level"
    transformations, such as minimizing the numeric value of an
    individual call to ``draw_bits``.
    """

    start = attr.ib()
    end = attr.ib()

    # Index of this block inside the overall list of blocks.
    index = attr.ib()

    # True if this block's byte values were forced by a write operation.
    # As long as the bytes before this block remain the same, modifying this
    # block's bytes will have no effect.
    forced = attr.ib(repr=False)

    # True if this block's byte values are all 0. Reading this flag can be
    # more convenient than explicitly checking a slice for non-zero bytes.
    all_zero = attr.ib(repr=False)

    @property
    def bounds(self):
        return (self.start, self.end)

    @property
    def length(self):
        return self.end - self.start

    @property
    def trivial(self):
        return self.forced or self.all_zero


class _Overrun(object):
    status = Status.OVERRUN

    def __repr__(self):
        return "Overrun"


Overrun = _Overrun()

global_test_counter = 0


MAX_DEPTH = 100


def calc_examples(self):
    """Build the list of examples from either a ``ConjectureResult``
    or a ``ConjectureData`` object by interpreting the recorded
    example boundaries and parsing them into a tree of ``Example``
    objects, returning the resulting list.

    This is needed because we want to calculate these lazily.
    The ``Example`` tree is fairly memory hungry and mildly
    expensive to compute and, especially during generation, we
    will often not need it, so we only want to compute it on
    demand."""
    assert self.example_boundaries

    example_stack = []
    examples = []

    non_trivial_block_starts = {
        b.start for b in self.blocks if not (b.all_zero or b.forced)
    }

    for index, labels in self.example_boundaries:
        for label in labels:
            if label in (Stop, StopDiscard):
                discard = label is StopDiscard
                k = example_stack.pop()
                ex = examples[k]
                ex.end = index
                ex.length = ex.end - ex.start

                if ex.length == 0:
                    ex.trivial = True

                if example_stack and not ex.trivial:
                    examples[example_stack[-1]].trivial = False

                ex.discarded = discard
            else:
                i = len(examples)
                ex = Example(
                    index=i,
                    depth=len(example_stack),
                    label=label,
                    start=index,
                    trivial=index not in non_trivial_block_starts,
                    parent=example_stack[-1] if example_stack else None,
                )
                examples.append(ex)
                if example_stack:
                    p = example_stack[-1]
                    examples[p].children.append(ex)
                example_stack.append(i)
    for ex in examples:
        assert ex.end is not None

    assert examples
    return examples


@attr.s(slots=True)
class ConjectureResult(object):
    """Result class storing the parts of ConjectureData that we
    will care about after the original ConjectureData has outlived its
    usefulness."""

    status = attr.ib()
    interesting_origin = attr.ib()
    buffer = attr.ib()
    blocks = attr.ib()
    example_boundaries = attr.ib()
    output = attr.ib()
    extra_information = attr.ib()
    has_discards = attr.ib()
    __examples = attr.ib(init=False, default=None)

    index = attr.ib(init=False)

    def __attrs_post_init__(self):
        self.index = len(self.buffer)

    @property
    def examples(self):
        if self.__examples is None:
            self.__examples = calc_examples(self)
            self.example_boundaries = None

        assert self.example_boundaries is None
        return self.__examples


# Special "labels" used to indicate the end of example boundaries
Stop = UniqueIdentifier("Stop")
StopDiscard = UniqueIdentifier("StopDiscard")


class ConjectureData(object):
    @classmethod
    def for_buffer(self, buffer):
        buffer = hbytes(buffer)
        return ConjectureData(
            max_length=len(buffer),
            draw_bytes=lambda data, n: hbytes(buffer[data.index : data.index + n]),
        )

    def __init__(self, max_length, draw_bytes):
        self.max_length = max_length
        self.is_find = False
        self._draw_bytes = draw_bytes
        self.block_starts = {}
        self.blocks = []
        self.buffer = bytearray()
        self.index = 0
        self.output = u""
        self.status = Status.VALID
        self.frozen = False
        global global_test_counter
        self.testcounter = global_test_counter
        global_test_counter += 1
        self.start_time = benchmark_time()
        self.events = set()
        self.forced_indices = set()
        self.masked_indices = {}
        self.interesting_origin = None
        self.draw_times = []
        self.max_depth = 0
        self.has_discards = False

        self.example_boundaries = []

        self.__result = None

        # Normally unpopulated but we need this in the niche case
        # that self.as_result() is Overrun but we still want the
        # examples for reporting purposes.
        self.__examples = None

        # We want the top level example to have depth 0, so we start
        # at -1.
        self.depth = -1

        self.start_example(TOP_LABEL)
        self.extra_information = ExtraInformation()

    def __repr__(self):
        return "ConjectureData(%s, %d bytes%s)" % (
            self.status.name,
            len(self.buffer),
            ", frozen" if self.frozen else "",
        )

    def as_result(self):
        """Convert the result of running this test into
        either an Overrun object or a ConjectureResult."""

        assert self.frozen
        if self.status == Status.OVERRUN:
            return Overrun
        if self.__result is None:
            self.__result = ConjectureResult(
                status=self.status,
                interesting_origin=self.interesting_origin,
                buffer=self.buffer,
                example_boundaries=self.example_boundaries,
                blocks=self.blocks,
                output=self.output,
                extra_information=self.extra_information
                if self.extra_information.has_information()
                else None,
                has_discards=self.has_discards,
            )
        return self.__result

    def __assert_not_frozen(self, name):
        if self.frozen:
            raise Frozen("Cannot call %s on frozen ConjectureData" % (name,))

    def note(self, value):
        self.__assert_not_frozen("note")
        if not isinstance(value, text_type):
            value = unicode_safe_repr(value)
        self.output += value

    def draw(self, strategy, label=None):
        if self.is_find and not strategy.supports_find:
            raise InvalidArgument(
                (
                    "Cannot use strategy %r within a call to find (presumably "
                    "because it would be invalid after the call had ended)."
                )
                % (strategy,)
            )

        if strategy.is_empty:
            self.mark_invalid()

        if self.depth >= MAX_DEPTH:
            self.mark_invalid()

        return self.__draw(strategy, label=label)

    def __draw(self, strategy, label):
        at_top_level = self.depth == 0
        if label is None:
            label = strategy.label
        self.start_example(label=label)
        try:
            if not at_top_level:
                return strategy.do_draw(self)
            else:
                try:
                    strategy.validate()
                    start_time = benchmark_time()
                    try:
                        return strategy.do_draw(self)
                    finally:
                        self.draw_times.append(benchmark_time() - start_time)
                except BaseException as e:
                    mark_for_escalation(e)
                    raise
        finally:
            self.stop_example()

    def current_example_labels(self):
        if not self.example_boundaries or self.example_boundaries[-1][0] < self.index:
            self.example_boundaries.append((self.index, []))
        return self.example_boundaries[-1][-1]

    def start_example(self, label):
        self.__assert_not_frozen("start_example")
        self.current_example_labels().append(label)
        self.depth += 1
        self.max_depth = max(self.max_depth, self.depth)

    def stop_example(self, discard=False):
        if self.frozen:
            return
        if discard:
            self.has_discards = True
        self.current_example_labels().append(StopDiscard if discard else Stop)
        self.depth -= 1
        assert self.depth >= -1

    def note_event(self, event):
        self.events.add(event)

    @property
    def examples(self):
        result = self.as_result()
        if result is Overrun:
            if self.__examples is None:
                self.__examples = calc_examples(self)
            return self.__examples
        else:
            return result.examples

    def freeze(self):
        if self.frozen:
            assert isinstance(self.buffer, hbytes)
            return
        self.finish_time = benchmark_time()
        assert len(self.buffer) == self.index

        # Always finish by closing all remaining examples so that we have a
        # valid tree.
        while self.depth >= 0:
            self.stop_example()

        self.frozen = True

        self.buffer = hbytes(self.buffer)
        self.events = frozenset(self.events)
        del self._draw_bytes

    def draw_bits(self, n, forced=None):
        """Return an ``n``-bit integer from the underlying source of
        bytes. If ``forced`` is set to an integer will instead
        ignore the underlying source and simulate a draw as if it had
        returned that integer."""
        self.__assert_not_frozen("draw_bits")
        if n == 0:
            return 0
        assert n > 0
        n_bytes = bits_to_bytes(n)
        self.__check_capacity(n_bytes)

        if forced is not None:
            buf = bytearray(int_to_bytes(forced, n_bytes))
        else:
            buf = bytearray(self._draw_bytes(self, n_bytes))
        assert len(buf) == n_bytes

        # If we have a number of bits that is not a multiple of 8
        # we have to mask off the high bits.
        if n % 8 != 0:
            mask = (1 << (n % 8)) - 1
            assert mask != 0
            buf[0] &= mask
            self.masked_indices[self.index] = mask
        buf = hbytes(buf)
        result = int_from_bytes(buf)

        self.start_example(DRAW_BYTES_LABEL)
        initial = self.index

        block = Block(
            start=initial,
            end=initial + n_bytes,
            index=len(self.blocks),
            forced=forced is not None,
            all_zero=result == 0,
        )

        if block.forced:
            self.forced_indices.update(hrange(block.start, block.end))
        self.block_starts.setdefault(n_bytes, []).append(block.start)
        self.blocks.append(block)
        assert self.blocks[block.index] is block
        assert self.index == initial
        self.buffer.extend(buf)
        self.index = len(self.buffer)
        self.stop_example()

        assert bit_length(result) <= n
        return result

    def draw_bytes(self, n):
        """Draw n bytes from the underlying source."""
        return int_to_bytes(self.draw_bits(8 * n), n)

    def write(self, string):
        """Write ``string`` to the output buffer."""
        self.__assert_not_frozen("write")
        string = hbytes(string)
        if not string:
            return
        self.draw_bits(len(string) * 8, forced=int_from_bytes(string))
        return self.buffer[-len(string) :]

    def __check_capacity(self, n):
        if self.index + n > self.max_length:
            self.mark_overrun()

    def conclude_test(self, status, interesting_origin=None):
        assert (interesting_origin is None) or (status == Status.INTERESTING)
        self.__assert_not_frozen("conclude_test")
        self.interesting_origin = interesting_origin
        self.status = status
        self.freeze()
        raise StopTest(self.testcounter)

    def mark_interesting(self, interesting_origin=None):
        self.conclude_test(Status.INTERESTING, interesting_origin)

    def mark_invalid(self):
        self.conclude_test(Status.INVALID)

    def mark_overrun(self):
        self.conclude_test(Status.OVERRUN)


def bits_to_bytes(n):
    n_bytes = n // 8
    if n % 8 != 0:
        n_bytes += 1
    return n_bytes
