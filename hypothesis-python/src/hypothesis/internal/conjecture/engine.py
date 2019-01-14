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

from enum import Enum
from random import Random, getrandbits
from weakref import WeakKeyDictionary

import attr

from hypothesis import HealthCheck, Phase, Verbosity, settings as Settings
from hypothesis._settings import local_settings
from hypothesis.internal.compat import (
    Counter,
    benchmark_time,
    ceil,
    hbytes,
    hrange,
    int_from_bytes,
    int_to_bytes,
    to_bytes_sequence,
)
from hypothesis.internal.conjecture.data import (
    MAX_DEPTH,
    ConjectureData,
    Overrun,
    Status,
    StopTest,
)
from hypothesis.internal.conjecture.datatree import DataTree
from hypothesis.internal.conjecture.shrinker import Shrinker, sort_key
from hypothesis.internal.healthcheck import fail_health_check
from hypothesis.reporting import debug_report

# Tell pytest to omit the body of this module from tracebacks
# https://docs.pytest.org/en/latest/example/simple.html#writing-well-integrated-assertion-helpers
__tracebackhide__ = True


HUNG_TEST_TIME_LIMIT = 5 * 60
MAX_SHRINKS = 500

CACHE_RESET_FREQUENCY = 1000
MUTATION_POOL_SIZE = 100


@attr.s
class HealthCheckState(object):
    valid_examples = attr.ib(default=0)
    invalid_examples = attr.ib(default=0)
    overrun_examples = attr.ib(default=0)
    draw_times = attr.ib(default=attr.Factory(list))


class ExitReason(Enum):
    max_examples = 0
    max_iterations = 1
    max_shrinks = 3
    finished = 4
    flaky = 5


class RunIsComplete(Exception):
    pass


class ConjectureRunner(object):
    def __init__(self, test_function, settings=None, random=None, database_key=None):
        self._test_function = test_function
        self.settings = settings or Settings()
        self.shrinks = 0
        self.call_count = 0
        self.event_call_counts = Counter()
        self.valid_examples = 0
        self.start_time = benchmark_time()
        self.random = random or Random(getrandbits(128))
        self.database_key = database_key
        self.status_runtimes = {}

        self.all_drawtimes = []
        self.all_runtimes = []

        self.events_to_strings = WeakKeyDictionary()

        self.target_selector = TargetSelector(self.random)

        self.interesting_examples = {}
        self.covering_examples = {}

        self.shrunk_examples = set()

        self.health_check_state = None

        self.used_examples_from_database = False
        self.reset_tree_to_empty()

    def reset_tree_to_empty(self):
        self.tree = DataTree(cap=self.cap)

    def __tree_is_exhausted(self):
        return self.tree.is_exhausted

    def test_function(self, data):
        if benchmark_time() - self.start_time >= HUNG_TEST_TIME_LIMIT:
            fail_health_check(
                self.settings,
                (
                    "Your test has been running for at least five minutes. This "
                    "is probably not what you intended, so by default Hypothesis "
                    "turns it into an error."
                ),
                HealthCheck.hung_test,
            )

        self.call_count += 1
        try:
            self._test_function(data)
            data.freeze()
        except StopTest as e:
            if e.testcounter != data.testcounter:
                self.save_buffer(data.buffer)
                raise
        except BaseException:
            self.save_buffer(data.buffer)
            raise
        finally:
            data.freeze()
            self.note_details(data)

        self.target_selector.add(data)

        self.debug_data(data)

        if data.status == Status.VALID:
            self.valid_examples += 1

        # Record the test result in the tree, to avoid unnecessary work in
        # the future.

        # The tree has two main uses:

        # 1. It is mildly useful in some cases during generation where there is
        #    a high probability of duplication but it is possible to generate
        #    many examples. e.g. if we had input of the form none() | text()
        #    then we would generate duplicates 50% of the time, and would
        #    like to avoid that and spend more time exploring the text() half
        #    of the search space. The tree allows us to predict in advance if
        #    the test would lead to a duplicate and avoid that.
        # 2. When shrinking it is *extremely* useful to be able to anticipate
        #    duplication, because we try many similar and smaller test cases,
        #    and these will tend to have a very high duplication rate. This is
        #    where the tree usage really shines.
        #
        # Unfortunately, as well as being the less useful type of tree usage,
        # the first type is also the most expensive! Once we've entered shrink
        # mode our time remaining is essentially bounded - we're just here
        # until we've found the minimal example. In exploration mode, we might
        # be early on in a very long-running processs, and keeping everything
        # we've ever seen lying around ends up bloating our memory usage
        # substantially by causing us to use O(max_examples) memory.
        #
        # As a compromise, what we do is reset the cache every so often. This
        # keeps our memory usage bounded. It has a few unfortunate failure
        # modes in that it means that we can't always detect when we should
        # have stopped - if we are exploring a language which has only slightly
        # more than cache reset frequency number of members, we will end up
        # exploring indefinitely when we could have stopped. However, this is
        # a fairly unusual case - thanks to exponential blow-ups in language
        # size, most languages are either very large (possibly infinite) or
        # very small. Nevertheless we want CACHE_RESET_FREQUENCY to be quite
        # high to avoid this case coming up in practice.
        if (
            self.call_count % CACHE_RESET_FREQUENCY == 0
            and not self.interesting_examples
        ):
            self.reset_tree_to_empty()

        self.tree.add(data)

        if data.status == Status.INTERESTING:
            key = data.interesting_origin
            changed = False
            try:
                existing = self.interesting_examples[key]
            except KeyError:
                changed = True
            else:
                if sort_key(data.buffer) < sort_key(existing.buffer):
                    self.shrinks += 1
                    self.downgrade_buffer(existing.buffer)
                    changed = True

            if changed:
                self.save_buffer(data.buffer)
                self.interesting_examples[key] = data
                self.shrunk_examples.discard(key)

            if self.shrinks >= MAX_SHRINKS:
                self.exit_with(ExitReason.max_shrinks)

        if not self.interesting_examples:
            if self.valid_examples >= self.settings.max_examples:
                self.exit_with(ExitReason.max_examples)
            if self.call_count >= max(
                self.settings.max_examples * 10,
                # We have a high-ish default max iterations, so that tests
                # don't become flaky when max_examples is too low.
                1000,
            ):
                self.exit_with(ExitReason.max_iterations)

        if self.__tree_is_exhausted():
            self.exit_with(ExitReason.finished)

        self.record_for_health_check(data)

    def generate_novel_prefix(self):
        """Uses the tree to proactively generate a starting sequence of bytes
        that we haven't explored yet for this test.

        When this method is called, we assume that there must be at
        least one novel prefix left to find. If there were not, then the
        test run should have already stopped due to tree exhaustion.
        """
        return self.tree.generate_novel_prefix(self.random)

    @property
    def cap(self):
        return self.settings.buffer_size // 2

    def record_for_health_check(self, data):
        # Once we've actually found a bug, there's no point in trying to run
        # health checks - they'll just mask the actually important information.
        if data.status == Status.INTERESTING:
            self.health_check_state = None

        state = self.health_check_state

        if state is None:
            return

        state.draw_times.extend(data.draw_times)

        if data.status == Status.VALID:
            state.valid_examples += 1
        elif data.status == Status.INVALID:
            state.invalid_examples += 1
        else:
            assert data.status == Status.OVERRUN
            state.overrun_examples += 1

        max_valid_draws = 10
        max_invalid_draws = 50
        max_overrun_draws = 20

        assert state.valid_examples <= max_valid_draws

        if state.valid_examples == max_valid_draws:
            self.health_check_state = None
            return

        if state.overrun_examples == max_overrun_draws:
            fail_health_check(
                self.settings,
                (
                    "Examples routinely exceeded the max allowable size. "
                    "(%d examples overran while generating %d valid ones)"
                    ". Generating examples this large will usually lead to"
                    " bad results. You could try setting max_size parameters "
                    "on your collections and turning "
                    "max_leaves down on recursive() calls."
                )
                % (state.overrun_examples, state.valid_examples),
                HealthCheck.data_too_large,
            )
        if state.invalid_examples == max_invalid_draws:
            fail_health_check(
                self.settings,
                (
                    "It looks like your strategy is filtering out a lot "
                    "of data. Health check found %d filtered examples but "
                    "only %d good ones. This will make your tests much "
                    "slower, and also will probably distort the data "
                    "generation quite a lot. You should adapt your "
                    "strategy to filter less. This can also be caused by "
                    "a low max_leaves parameter in recursive() calls"
                )
                % (state.invalid_examples, state.valid_examples),
                HealthCheck.filter_too_much,
            )

        draw_time = sum(state.draw_times)

        if draw_time > 1.0:
            fail_health_check(
                self.settings,
                (
                    "Data generation is extremely slow: Only produced "
                    "%d valid examples in %.2f seconds (%d invalid ones "
                    "and %d exceeded maximum size). Try decreasing "
                    "size of the data you're generating (with e.g."
                    "max_size or max_leaves parameters)."
                )
                % (
                    state.valid_examples,
                    draw_time,
                    state.invalid_examples,
                    state.overrun_examples,
                ),
                HealthCheck.too_slow,
            )

    def save_buffer(self, buffer):
        if self.settings.database is not None:
            key = self.database_key
            if key is None:
                return
            self.settings.database.save(key, hbytes(buffer))

    def downgrade_buffer(self, buffer):
        if self.settings.database is not None and self.database_key is not None:
            self.settings.database.move(self.database_key, self.secondary_key, buffer)

    @property
    def secondary_key(self):
        return b".".join((self.database_key, b"secondary"))

    @property
    def covering_key(self):
        return b".".join((self.database_key, b"coverage"))

    def note_details(self, data):
        runtime = max(data.finish_time - data.start_time, 0.0)
        self.all_runtimes.append(runtime)
        self.all_drawtimes.extend(data.draw_times)
        self.status_runtimes.setdefault(data.status, []).append(runtime)
        for event in set(map(self.event_to_string, data.events)):
            self.event_call_counts[event] += 1

    def debug(self, message):
        with local_settings(self.settings):
            debug_report(message)

    @property
    def report_debug_info(self):
        return self.settings.verbosity >= Verbosity.debug

    def debug_data(self, data):
        if not self.report_debug_info:
            return

        stack = [[]]

        def go(ex):
            if ex.length == 0:
                return
            if len(ex.children) == 0:
                stack[-1].append(int_from_bytes(data.buffer[ex.start : ex.end]))
            else:
                node = []
                stack.append(node)

                for v in ex.children:
                    go(v)
                stack.pop()
                if len(node) == 1:
                    stack[-1].extend(node)
                else:
                    stack[-1].append(node)

        go(data.examples[0])
        assert len(stack) == 1

        status = repr(data.status)

        if data.status == Status.INTERESTING:
            status = "%s (%r)" % (status, data.interesting_origin)

        self.debug(
            "%d bytes %r -> %s, %s" % (data.index, stack[0], status, data.output)
        )

    def run(self):
        with local_settings(self.settings):
            try:
                self._run()
            except RunIsComplete:
                pass
            for v in self.interesting_examples.values():
                self.debug_data(v)
            self.debug(
                u"Run complete after %d examples (%d valid) and %d shrinks"
                % (self.call_count, self.valid_examples, self.shrinks)
            )

    def _new_mutator(self):
        target_data = [None]

        def draw_new(data, n):
            return uniform(self.random, n)

        def draw_existing(data, n):
            return target_data[0].buffer[data.index : data.index + n]

        def draw_smaller(data, n):
            existing = target_data[0].buffer[data.index : data.index + n]
            r = uniform(self.random, n)
            if r <= existing:
                return r
            return _draw_predecessor(self.random, existing)

        def draw_larger(data, n):
            existing = target_data[0].buffer[data.index : data.index + n]
            r = uniform(self.random, n)
            if r >= existing:
                return r
            return _draw_successor(self.random, existing)

        def reuse_existing(data, n):
            choices = data.block_starts.get(n, [])
            if choices:
                i = self.random.choice(choices)
                return hbytes(data.buffer[i : i + n])
            else:
                result = uniform(self.random, n)
                assert isinstance(result, hbytes)
                return result

        def flip_bit(data, n):
            buf = bytearray(target_data[0].buffer[data.index : data.index + n])
            i = self.random.randint(0, n - 1)
            k = self.random.randint(0, 7)
            buf[i] ^= 1 << k
            return hbytes(buf)

        def draw_zero(data, n):
            return hbytes(b"\0" * n)

        def draw_max(data, n):
            return hbytes([255]) * n

        def draw_constant(data, n):
            return hbytes([self.random.randint(0, 255)]) * n

        def redraw_last(data, n):
            u = target_data[0].blocks[-1].start
            if data.index + n <= u:
                return target_data[0].buffer[data.index : data.index + n]
            else:
                return uniform(self.random, n)

        options = [
            draw_new,
            redraw_last,
            redraw_last,
            reuse_existing,
            reuse_existing,
            draw_existing,
            draw_smaller,
            draw_larger,
            flip_bit,
            draw_zero,
            draw_max,
            draw_zero,
            draw_max,
            draw_constant,
        ]

        bits = [self.random.choice(options) for _ in hrange(3)]

        prefix = [None]

        def mutate_from(origin):
            target_data[0] = origin
            prefix[0] = self.generate_novel_prefix()
            return draw_mutated

        def draw_mutated(data, n):
            if data.index + n > len(target_data[0].buffer):
                result = uniform(self.random, n)
            else:
                result = self.random.choice(bits)(data, n)
            p = prefix[0]
            if data.index < len(p):
                start = p[data.index : data.index + n]
                result = start + result[len(start) :]
            return self.__zero_bound(data, result)

        return mutate_from

    def __rewrite(self, data, result):
        return self.__zero_bound(data, result)

    def __zero_bound(self, data, result):
        """This tries to get the size of the generated data under control by
        replacing the result with zero if we are too deep or have already
        generated too much data.

        This causes us to enter "shrinking mode" there and thus reduce
        the size of the generated data.
        """
        initial = len(result)
        if data.depth * 2 >= MAX_DEPTH or data.index >= self.cap:
            data.forced_indices.update(hrange(data.index, data.index + initial))
            data.hit_zero_bound = True
            result = hbytes(initial)
        elif data.index + initial >= self.cap:
            data.hit_zero_bound = True
            n = self.cap - data.index
            data.forced_indices.update(hrange(self.cap, data.index + initial))
            result = result[:n] + hbytes(initial - n)
        assert len(result) == initial
        return result

    @property
    def database(self):
        if self.database_key is None:
            return None
        return self.settings.database

    def has_existing_examples(self):
        return self.database is not None and Phase.reuse in self.settings.phases

    def reuse_existing_examples(self):
        """If appropriate (we have a database and have been told to use it),
        try to reload existing examples from the database.

        If there are a lot we don't try all of them. We always try the
        smallest example in the database (which is guaranteed to be the
        last failure) and the largest (which is usually the seed example
        which the last failure came from but we don't enforce that). We
        then take a random sampling of the remainder and try those. Any
        examples that are no longer interesting are cleared out.
        """
        if self.has_existing_examples():
            self.debug("Reusing examples from database")
            # We have to do some careful juggling here. We have two database
            # corpora: The primary and secondary. The primary corpus is a
            # small set of minimized examples each of which has at one point
            # demonstrated a distinct bug. We want to retry all of these.

            # We also have a secondary corpus of examples that have at some
            # point demonstrated interestingness (currently only ones that
            # were previously non-minimal examples of a bug, but this will
            # likely expand in future). These are a good source of potentially
            # interesting examples, but there are a lot of them, so we down
            # sample the secondary corpus to a more manageable size.

            corpus = sorted(
                self.settings.database.fetch(self.database_key), key=sort_key
            )
            desired_size = max(2, ceil(0.1 * self.settings.max_examples))

            for extra_key in [self.secondary_key, self.covering_key]:
                if len(corpus) < desired_size:
                    extra_corpus = list(self.settings.database.fetch(extra_key))

                    shortfall = desired_size - len(corpus)

                    if len(extra_corpus) <= shortfall:
                        extra = extra_corpus
                    else:
                        extra = self.random.sample(extra_corpus, shortfall)
                    extra.sort(key=sort_key)
                    corpus.extend(extra)

            self.used_examples_from_database = len(corpus) > 0

            for existing in corpus:
                last_data = ConjectureData.for_buffer(existing)
                try:
                    self.test_function(last_data)
                finally:
                    if last_data.status != Status.INTERESTING:
                        self.settings.database.delete(self.database_key, existing)
                        self.settings.database.delete(self.secondary_key, existing)

    def exit_with(self, reason):
        self.exit_reason = reason
        raise RunIsComplete()

    def generate_new_examples(self):
        if Phase.generate not in self.settings.phases:
            return

        zero_data = self.cached_test_function(hbytes(self.settings.buffer_size))
        if zero_data.status == Status.OVERRUN or (
            zero_data.status == Status.VALID
            and len(zero_data.buffer) * 2 > self.settings.buffer_size
        ):
            fail_health_check(
                self.settings,
                "The smallest natural example for your test is extremely "
                "large. This makes it difficult for Hypothesis to generate "
                "good examples, especially when trying to reduce failing ones "
                "at the end. Consider reducing the size of your data if it is "
                "of a fixed size. You could also fix this by improving how "
                "your data shrinks (see https://hypothesis.readthedocs.io/en/"
                "latest/data.html#shrinking for details), or by introducing "
                "default values inside your strategy. e.g. could you replace "
                "some arguments with their defaults by using "
                "one_of(none(), some_complex_strategy)?",
                HealthCheck.large_base_example,
            )

        if zero_data is not Overrun:
            # If the language starts with writes of length >= cap then there is
            # only one string in it: Everything after cap is forced to be zero (or
            # to be whatever value is written there). That means that once we've
            # tried the zero value, there's nothing left for us to do, so we
            # exit early here.
            for i in hrange(self.cap):
                if i not in zero_data.forced_indices:
                    break
            else:
                self.exit_with(ExitReason.finished)

        self.health_check_state = HealthCheckState()

        count = 0
        while not self.interesting_examples and (
            count < 10 or self.health_check_state is not None
        ):
            prefix = self.generate_novel_prefix()

            def draw_bytes(data, n):
                if data.index < len(prefix):
                    result = prefix[data.index : data.index + n]
                    if len(result) < n:
                        result += uniform(self.random, n - len(result))
                else:
                    result = uniform(self.random, n)
                return self.__zero_bound(data, result)

            targets_found = len(self.covering_examples)

            last_data = ConjectureData(
                max_length=self.settings.buffer_size, draw_bytes=draw_bytes
            )
            self.test_function(last_data)
            last_data.freeze()

            count += 1

        mutations = 0
        mutator = self._new_mutator()

        zero_bound_queue = []

        while not self.interesting_examples:
            if zero_bound_queue:
                # Whenever we generated an example and it hits a bound
                # which forces zero blocks into it, this creates a weird
                # distortion effect by making certain parts of the data
                # stream (especially ones to the right) much more likely
                # to be zero. We fix this by redistributing the generated
                # data by shuffling it randomly. This results in the
                # zero data being spread evenly throughout the buffer.
                # Hopefully the shrinking this causes will cause us to
                # naturally fail to hit the bound.
                # If it doesn't then we will queue the new version up again
                # (now with more zeros) and try again.
                overdrawn = zero_bound_queue.pop()
                buffer = bytearray(overdrawn.buffer)

                # These will have values written to them that are different
                # from what's in them anyway, so the value there doesn't
                # really "count" for distributional purposes, and if we
                # leave them in then they can cause the fraction of non
                # zero bytes to increase on redraw instead of decrease.
                for i in overdrawn.forced_indices:
                    buffer[i] = 0

                self.random.shuffle(buffer)
                buffer = hbytes(buffer)

                def draw_bytes(data, n):
                    result = buffer[data.index : data.index + n]
                    if len(result) < n:
                        result += hbytes(n - len(result))
                    return self.__rewrite(data, result)

                data = ConjectureData(
                    draw_bytes=draw_bytes, max_length=self.settings.buffer_size
                )
                self.test_function(data)
                data.freeze()
            else:
                origin = self.target_selector.select()
                mutations += 1
                targets_found = len(self.covering_examples)
                data = ConjectureData(
                    draw_bytes=mutator(origin), max_length=self.settings.buffer_size
                )
                self.test_function(data)
                data.freeze()
                if (
                    data.status > origin.status
                    or len(self.covering_examples) > targets_found
                ):
                    mutations = 0
                elif data.status < origin.status or mutations >= 10:
                    # Cap the variations of a single example and move on to
                    # an entirely fresh start.  Ten is an entirely arbitrary
                    # constant, but it's been working well for years.
                    mutations = 0
                    mutator = self._new_mutator()
            if getattr(data, "hit_zero_bound", False):
                zero_bound_queue.append(data)
            mutations += 1

    def _run(self):
        self.start_time = benchmark_time()

        self.reuse_existing_examples()
        self.generate_new_examples()
        self.shrink_interesting_examples()

        self.exit_with(ExitReason.finished)

    def shrink_interesting_examples(self):
        """If we've found interesting examples, try to replace each of them
        with a minimal interesting example with the same interesting_origin.

        We may find one or more examples with a new interesting_origin
        during the shrink process. If so we shrink these too.
        """
        if Phase.shrink not in self.settings.phases or not self.interesting_examples:
            return

        for prev_data in sorted(
            self.interesting_examples.values(), key=lambda d: sort_key(d.buffer)
        ):
            assert prev_data.status == Status.INTERESTING
            data = ConjectureData.for_buffer(prev_data.buffer)
            self.test_function(data)
            if data.status != Status.INTERESTING:
                self.exit_with(ExitReason.flaky)

        self.clear_secondary_key()

        while len(self.shrunk_examples) < len(self.interesting_examples):
            target, example = min(
                [
                    (k, v)
                    for k, v in self.interesting_examples.items()
                    if k not in self.shrunk_examples
                ],
                key=lambda kv: (sort_key(kv[1].buffer), sort_key(repr(kv[0]))),
            )
            self.debug("Shrinking %r" % (target,))

            def predicate(d):
                if d.status < Status.INTERESTING:
                    return False
                return d.interesting_origin == target

            self.shrink(example, predicate)

            self.shrunk_examples.add(target)

    def clear_secondary_key(self):
        if self.has_existing_examples():
            # If we have any smaller examples in the secondary corpus, now is
            # a good time to try them to see if they work as shrinks. They
            # probably won't, but it's worth a shot and gives us a good
            # opportunity to clear out the database.

            # It's not worth trying the primary corpus because we already
            # tried all of those in the initial phase.
            corpus = sorted(
                self.settings.database.fetch(self.secondary_key), key=sort_key
            )
            for c in corpus:
                primary = {v.buffer for v in self.interesting_examples.values()}

                cap = max(map(sort_key, primary))

                if sort_key(c) > cap:
                    break
                else:
                    self.cached_test_function(c)
                    # We unconditionally remove c from the secondary key as it
                    # is either now primary or worse than our primary example
                    # of this reason for interestingness.
                    self.settings.database.delete(self.secondary_key, c)

    def shrink(self, example, predicate):
        s = self.new_shrinker(example, predicate)
        s.shrink()
        return s.shrink_target

    def new_shrinker(self, example, predicate):
        return Shrinker(self, example, predicate)

    def cached_test_function(self, buffer):
        """Checks the tree to see if we've tested this buffer, and returns the
        previous result if we have.

        Otherwise we call through to ``test_function``, and return a
        fresh result.
        """
        result = self.tree.lookup(buffer)
        if result is not None:
            return result

        # We didn't find a match in the tree, so we need to run the test
        # function normally. Note that test_function will automatically
        # add this to the tree so we don't need to update the cache.
        result = ConjectureData.for_buffer(buffer)
        self.test_function(result)
        if result.status == Status.OVERRUN:
            return Overrun
        return result

    def event_to_string(self, event):
        if isinstance(event, str):
            return event
        try:
            return self.events_to_strings[event]
        except KeyError:
            pass
        result = str(event)
        self.events_to_strings[event] = result
        return result


def _draw_predecessor(rnd, xs):
    r = bytearray()
    any_strict = False
    for x in to_bytes_sequence(xs):
        if not any_strict:
            c = rnd.randint(0, x)
            if c < x:
                any_strict = True
        else:
            c = rnd.randint(0, 255)
        r.append(c)
    return hbytes(r)


def _draw_successor(rnd, xs):
    r = bytearray()
    any_strict = False
    for x in to_bytes_sequence(xs):
        if not any_strict:
            c = rnd.randint(x, 255)
            if c > x:
                any_strict = True
        else:
            c = rnd.randint(0, 255)
        r.append(c)
    return hbytes(r)


def uniform(random, n):
    return int_to_bytes(random.getrandbits(n * 8), n)


def pop_random(random, values):
    """Remove a random element of values, possibly changing the ordering of its
    elements."""

    # We pick the element at a random index. Rather than removing that element
    # from the list (which would be an O(n) operation), we swap it to the end
    # and return the last element of the list. This changes the order of
    # the elements, but as long as these elements are only accessed through
    # random sampling that doesn't matter.
    i = random.randrange(0, len(values))
    values[i], values[-1] = values[-1], values[i]
    return values.pop()


class TargetSelector(object):
    """Data structure for selecting targets to use for mutation.

    The main purpose of the TargetSelector is to maintain a pool of "reasonably
    useful" examples, while keeping the pool of bounded size.

    In particular it ensures:

    1. We only retain examples of the best status we've seen so far (not
       counting INTERESTING, which is special).
    2. We preferentially return examples we've never returned before when
       select() is called.
    3. The number of retained examples is never more than self.pool_size, with
       past examples discarded automatically, preferring ones that we have
       already explored from.

    These invariants are fairly heavily prone to change - they're not
    especially well validated as being optimal, and are mostly just a decent
    compromise between diversity and keeping the pool size bounded.
    """

    def __init__(self, random, pool_size=MUTATION_POOL_SIZE):
        self.random = random
        self.best_status = Status.OVERRUN
        self.pool_size = pool_size
        self.reset()

    def __len__(self):
        return len(self.fresh_examples) + len(self.used_examples)

    def reset(self):
        self.fresh_examples = []
        self.used_examples = []

    def add(self, data):
        if data.status == Status.INTERESTING:
            return
        if data.status < self.best_status:
            return
        if data.status > self.best_status:
            self.best_status = data.status
            self.reset()

        # Note that technically data could be a duplicate. This rarely happens
        # (only if we've exceeded the CACHE_RESET_FREQUENCY number of test
        # function calls), but it's certainly possible. This could result in
        # us having the same example multiple times, possibly spread over both
        # lists. We could check for this, but it's not a major problem so we
        # don't bother.
        self.fresh_examples.append(data)
        if len(self) > self.pool_size:
            pop_random(self.random, self.used_examples or self.fresh_examples)
            assert self.pool_size == len(self)

    def select(self):
        if self.fresh_examples:
            result = pop_random(self.random, self.fresh_examples)
            self.used_examples.append(result)
            return result
        else:
            return self.random.choice(self.used_examples)
