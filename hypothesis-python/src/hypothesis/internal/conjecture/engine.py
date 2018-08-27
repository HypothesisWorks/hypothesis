# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import heapq
from enum import Enum
from random import Random, getrandbits
from weakref import WeakKeyDictionary
from functools import total_ordering
from collections import defaultdict

import attr

from hypothesis import Phase, Verbosity, HealthCheck
from hypothesis import settings as Settings
from hypothesis._settings import local_settings, note_deprecation
from hypothesis.reporting import debug_report
from hypothesis.internal.compat import Counter, ceil, hbytes, hrange, \
    int_to_bytes, benchmark_time, int_from_bytes, to_bytes_sequence
from hypothesis.utils.conventions import UniqueIdentifier
from hypothesis.internal.healthcheck import fail_health_check
from hypothesis.internal.conjecture.data import MAX_DEPTH, Status, \
    StopTest, ConjectureData
from hypothesis.internal.conjecture.shrinking import Length, Integer, \
    Lexical, Ordering

# Tell pytest to omit the body of this module from tracebacks
# http://doc.pytest.org/en/latest/example/simple.html#writing-well-integrated-assertion-helpers
__tracebackhide__ = True


HUNG_TEST_TIME_LIMIT = 5 * 60
MAX_SHRINKS = 500


@attr.s
class HealthCheckState(object):
    valid_examples = attr.ib(default=0)
    invalid_examples = attr.ib(default=0)
    overrun_examples = attr.ib(default=0)
    draw_times = attr.ib(default=attr.Factory(list))


class ExitReason(Enum):
    max_examples = 0
    max_iterations = 1
    timeout = 2
    max_shrinks = 3
    finished = 4
    flaky = 5


class RunIsComplete(Exception):
    pass


class ConjectureRunner(object):

    def __init__(
        self, test_function, settings=None, random=None,
        database_key=None,
    ):
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

        # Tree nodes are stored in an array to prevent heavy nesting of data
        # structures. Branches are dicts mapping bytes to child nodes (which
        # will in general only be partially populated). Leaves are
        # ConjectureData objects that have been previously seen as the result
        # of following that path.
        self.tree = [{}]

        # A node is dead if there is nothing left to explore past that point.
        # Recursively, a node is dead if either it is a leaf or every byte
        # leads to a dead node when starting from here.
        self.dead = set()

        # We rewrite the byte stream at various points during parsing, to one
        # that will produce an equivalent result but is in some sense more
        # canonical. We keep track of these so that when walking the tree we
        # can identify nodes where the exact byte value doesn't matter and
        # treat all bytes there as equivalent. This significantly reduces the
        # size of the search space and removes a lot of redundant examples.

        # Maps tree indices where to the unique byte that is valid at that
        # point. Corresponds to data.write() calls.
        self.forced = {}

        # Maps tree indices to a mask that restricts bytes at that point.
        # Currently this is only updated by draw_bits, but it potentially
        # could get used elsewhere.
        self.masks = {}

        # Where a tree node consists of the beginning of a block we track the
        # size of said block. This allows us to tell when an example is too
        # short even if it goes off the unexplored region of the tree - if it
        # is at the beginning of a block of size 4 but only has 3 bytes left,
        # it's going to overrun the end of the buffer regardless of the
        # buffer contents.
        self.block_sizes = {}

        self.interesting_examples = {}
        self.covering_examples = {}

        self.shrunk_examples = set()

        self.tag_intern_table = {}

        self.health_check_state = None

        self.used_examples_from_database = False

    def __tree_is_exhausted(self):
        return 0 in self.dead

    def test_function(self, data):
        if benchmark_time() - self.start_time >= HUNG_TEST_TIME_LIMIT:
            fail_health_check(self.settings, (
                'Your test has been running for at least five minutes. This '
                'is probably not what you intended, so by default Hypothesis '
                'turns it into an error.'
            ), HealthCheck.hung_test)

        self.call_count += 1
        try:
            self._test_function(data)
            data.freeze()
        except StopTest as e:
            if e.testcounter != data.testcounter:
                self.save_buffer(data.buffer)
                raise e
        except BaseException:
            self.save_buffer(data.buffer)
            raise
        finally:
            data.freeze()
            self.note_details(data)

        self.target_selector.add(data)

        self.debug_data(data)

        tags = frozenset(data.tags)
        data.tags = self.tag_intern_table.setdefault(tags, tags)

        if data.status == Status.VALID:
            self.valid_examples += 1
            for t in data.tags:
                existing = self.covering_examples.get(t)
                if (
                    existing is None or
                    sort_key(data.buffer) < sort_key(existing.buffer)
                ):
                    self.covering_examples[t] = data
                    if self.database is not None:
                        self.database.save(self.covering_key, data.buffer)
                        if existing is not None:
                            self.database.delete(
                                self.covering_key, existing.buffer)

        tree_node = self.tree[0]
        indices = []
        node_index = 0
        for i, b in enumerate(data.buffer):
            indices.append(node_index)
            if i in data.forced_indices:
                self.forced[node_index] = b
            try:
                self.masks[node_index] = data.masked_indices[i]
            except KeyError:
                pass
            try:
                node_index = tree_node[b]
            except KeyError:
                node_index = len(self.tree)
                self.tree.append({})
                tree_node[b] = node_index
            tree_node = self.tree[node_index]
            if node_index in self.dead:
                break

        for u, v in data.blocks:
            # This can happen if we hit a dead node when walking the buffer.
            # In that case we already have this section of the tree mapped.
            if u >= len(indices):
                break
            self.block_sizes[indices[u]] = v - u

        self.dead.update(indices[self.cap:])

        if data.status != Status.OVERRUN and node_index not in self.dead:
            self.dead.add(node_index)
            self.tree[node_index] = data

            for j in reversed(indices):
                mask = self.masks.get(j, 0xff)
                assert _is_simple_mask(mask)
                max_size = mask + 1

                if (
                    len(self.tree[j]) < max_size and
                    j not in self.forced
                ):
                    break
                if set(self.tree[j].values()).issubset(self.dead):
                    self.dead.add(j)
                else:
                    break

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
        if (
            self.settings.timeout > 0 and
            benchmark_time() >= self.start_time + self.settings.timeout
        ):
            note_deprecation((
                'Your tests are hitting the settings timeout (%.2fs). '
                'This functionality will go away in a future release '
                'and you should not rely on it. Instead, try setting '
                'max_examples to be some value lower than %d (the number '
                'of examples your test successfully ran here). Or, if you '
                'would prefer your tests to run to completion, regardless '
                'of how long they take, you can set the timeout value to '
                'hypothesis.unlimited.'
            ) % (
                self.settings.timeout, self.valid_examples),
                self.settings)
            self.exit_with(ExitReason.timeout)

        if not self.interesting_examples:
            if self.valid_examples >= self.settings.max_examples:
                self.exit_with(ExitReason.max_examples)
            if self.call_count >= max(
                self.settings.max_examples * 10,
                # We have a high-ish default max iterations, so that tests
                # don't become flaky when max_examples is too low.
                1000
            ):
                self.exit_with(ExitReason.max_iterations)

        if self.__tree_is_exhausted():
            self.exit_with(ExitReason.finished)

        self.record_for_health_check(data)

    def generate_novel_prefix(self):
        prefix = bytearray()
        node = 0
        while True:
            assert len(prefix) < self.cap
            assert node not in self.dead

            mask = self.masks.get(node, 0xff)
            assert _is_simple_mask(mask)
            upper_bound = mask + 1

            try:
                c = self.forced[node]
                prefix.append(c)
                node = self.tree[node][c]
                continue
            except KeyError:
                pass
            c = self.random.randrange(0, upper_bound)
            try:
                next_node = self.tree[node][c]
                if next_node in self.dead:
                    choices = [
                        b for b in hrange(upper_bound)
                        if self.tree[node].get(b) not in self.dead
                    ]
                    assert choices
                    c = self.random.choice(choices)
                    node = self.tree[node][c]
                else:
                    node = next_node
                prefix.append(c)
            except KeyError:
                prefix.append(c)
                break
        assert node not in self.dead
        return hbytes(prefix)

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
            fail_health_check(self.settings, (
                'Examples routinely exceeded the max allowable size. '
                '(%d examples overran while generating %d valid ones)'
                '. Generating examples this large will usually lead to'
                ' bad results. You could try setting max_size parameters '
                'on your collections and turning '
                'max_leaves down on recursive() calls.') % (
                state.overrun_examples, state.valid_examples
            ), HealthCheck.data_too_large)
        if state.invalid_examples == max_invalid_draws:
            fail_health_check(self.settings, (
                'It looks like your strategy is filtering out a lot '
                'of data. Health check found %d filtered examples but '
                'only %d good ones. This will make your tests much '
                'slower, and also will probably distort the data '
                'generation quite a lot. You should adapt your '
                'strategy to filter less. This can also be caused by '
                'a low max_leaves parameter in recursive() calls') % (
                state.invalid_examples, state.valid_examples
            ), HealthCheck.filter_too_much)

        draw_time = sum(state.draw_times)

        if draw_time > 1.0:
            fail_health_check(self.settings, (
                'Data generation is extremely slow: Only produced '
                '%d valid examples in %.2f seconds (%d invalid ones '
                'and %d exceeded maximum size). Try decreasing '
                "size of the data you're generating (with e.g."
                'max_size or max_leaves parameters).'
            ) % (
                state.valid_examples, draw_time, state.invalid_examples,
                state.overrun_examples), HealthCheck.too_slow,)

    def save_buffer(self, buffer):
        if self.settings.database is not None:
            key = self.database_key
            if key is None:
                return
            self.settings.database.save(key, hbytes(buffer))

    def downgrade_buffer(self, buffer):
        if (
            self.settings.database is not None and
            self.database_key is not None
        ):
            self.settings.database.move(
                self.database_key, self.secondary_key, buffer)

    @property
    def secondary_key(self):
        return b'.'.join((self.database_key, b'secondary'))

    @property
    def covering_key(self):
        return b'.'.join((self.database_key, b'coverage'))

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
                stack[-1].append(int_from_bytes(
                    data.buffer[ex.start:ex.end]
                ))
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
            status = '%s (%r)' % (status, data.interesting_origin,)

        self.debug('%d bytes %r -> %s, %s' % (
            data.index, stack[0], status, data.output,
        ))

    def run(self):
        with local_settings(self.settings):
            try:
                self._run()
            except RunIsComplete:
                pass
            for v in self.interesting_examples.values():
                self.debug_data(v)
            self.debug(
                u'Run complete after %d examples (%d valid) and %d shrinks'
                % (self.call_count, self.valid_examples, self.shrinks))

    def _new_mutator(self):
        target_data = [None]

        def draw_new(data, n):
            return uniform(self.random, n)

        def draw_existing(data, n):
            return target_data[0].buffer[data.index:data.index + n]

        def draw_smaller(data, n):
            existing = target_data[0].buffer[data.index:data.index + n]
            r = uniform(self.random, n)
            if r <= existing:
                return r
            return _draw_predecessor(self.random, existing)

        def draw_larger(data, n):
            existing = target_data[0].buffer[data.index:data.index + n]
            r = uniform(self.random, n)
            if r >= existing:
                return r
            return _draw_successor(self.random, existing)

        def reuse_existing(data, n):
            choices = data.block_starts.get(n, [])
            if choices:
                i = self.random.choice(choices)
                return hbytes(data.buffer[i:i + n])
            else:
                result = uniform(self.random, n)
                assert isinstance(result, hbytes)
                return result

        def flip_bit(data, n):
            buf = bytearray(
                target_data[0].buffer[data.index:data.index + n])
            i = self.random.randint(0, n - 1)
            k = self.random.randint(0, 7)
            buf[i] ^= (1 << k)
            return hbytes(buf)

        def draw_zero(data, n):
            return hbytes(b'\0' * n)

        def draw_max(data, n):
            return hbytes([255]) * n

        def draw_constant(data, n):
            return hbytes([self.random.randint(0, 255)]) * n

        def redraw_last(data, n):
            u = target_data[0].blocks[-1][0]
            if data.index + n <= u:
                return target_data[0].buffer[data.index:data.index + n]
            else:
                return uniform(self.random, n)

        options = [
            draw_new,
            redraw_last, redraw_last,
            reuse_existing, reuse_existing,
            draw_existing, draw_smaller, draw_larger,
            flip_bit,
            draw_zero, draw_max, draw_zero, draw_max,
            draw_constant,
        ]

        bits = [
            self.random.choice(options) for _ in hrange(3)
        ]

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
                start = p[data.index:data.index + n]
                result = start + result[len(start):]
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
            data.forced_indices.update(
                hrange(data.index, data.index + initial))
            data.hit_zero_bound = True
            result = hbytes(initial)
        elif data.index + initial >= self.cap:
            data.hit_zero_bound = True
            n = self.cap - data.index
            data.forced_indices.update(
                hrange(self.cap, data.index + initial))
            result = result[:n] + hbytes(initial - n)
        assert len(result) == initial
        return result

    @property
    def database(self):
        if self.database_key is None:
            return None
        return self.settings.database

    def has_existing_examples(self):
        return (
            self.database is not None and
            Phase.reuse in self.settings.phases
        )

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
            self.debug('Reusing examples from database')
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
                self.settings.database.fetch(self.database_key),
                key=sort_key
            )
            desired_size = max(2, ceil(0.1 * self.settings.max_examples))

            for extra_key in [self.secondary_key, self.covering_key]:
                if len(corpus) < desired_size:
                    extra_corpus = list(
                        self.settings.database.fetch(extra_key),
                    )

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
                        self.settings.database.delete(
                            self.database_key, existing)
                        self.settings.database.delete(
                            self.secondary_key, existing)

    def exit_with(self, reason):
        self.exit_reason = reason
        raise RunIsComplete()

    def generate_new_examples(self):
        if Phase.generate not in self.settings.phases:
            return

        zero_data = self.cached_test_function(
            hbytes(self.settings.buffer_size))
        if zero_data.status == Status.OVERRUN or (
            zero_data.status == Status.VALID and
            len(zero_data.buffer) * 2 > self.settings.buffer_size
        ):
            fail_health_check(
                self.settings,
                'The smallest natural example for your test is extremely '
                'large. This makes it difficult for Hypothesis to generate '
                'good examples, especially when trying to reduce failing ones '
                'at the end. Consider reducing the size of your data if it is '
                'of a fixed size. You could also fix this by improving how '
                'your data shrinks (see https://hypothesis.readthedocs.io/en/'
                'latest/data.html#shrinking for details), or by introducing '
                'default values inside your strategy. e.g. could you replace '
                'some arguments with their defaults by using '
                'one_of(none(), some_complex_strategy)?',
                HealthCheck.large_base_example
            )

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
                    result = prefix[data.index:data.index + n]
                    if len(result) < n:
                        result += uniform(self.random, n - len(result))
                else:
                    result = uniform(self.random, n)
                return self.__zero_bound(data, result)

            targets_found = len(self.covering_examples)

            last_data = ConjectureData(
                max_length=self.settings.buffer_size,
                draw_bytes=draw_bytes
            )
            self.test_function(last_data)
            last_data.freeze()

            if len(self.covering_examples) > targets_found:
                count = 0
            else:
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
                    result = buffer[data.index:data.index + n]
                    if len(result) < n:
                        result += hbytes(n - len(result))
                    return self.__rewrite(data, result)

                data = ConjectureData(
                    draw_bytes=draw_bytes,
                    max_length=self.settings.buffer_size,
                )
                self.test_function(data)
                data.freeze()
            else:
                target, origin = self.target_selector.select()
                mutations += 1
                targets_found = len(self.covering_examples)
                data = ConjectureData(
                    draw_bytes=mutator(origin),
                    max_length=self.settings.buffer_size
                )
                self.test_function(data)
                data.freeze()
                if (
                    data.status > origin.status or
                    len(self.covering_examples) > targets_found
                ):
                    mutations = 0
                elif (
                    data.status < origin.status or
                    not self.target_selector.has_tag(target, data) or
                    mutations >= 10
                ):
                    # Cap the variations of a single example and move on to
                    # an entirely fresh start.  Ten is an entirely arbitrary
                    # constant, but it's been working well for years.
                    mutations = 0
                    mutator = self._new_mutator()
            if getattr(data, 'hit_zero_bound', False):
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
        if (
            Phase.shrink not in self.settings.phases or
            not self.interesting_examples
        ):
            return

        for prev_data in sorted(
            self.interesting_examples.values(),
            key=lambda d: sort_key(d.buffer)
        ):
            assert prev_data.status == Status.INTERESTING
            data = ConjectureData.for_buffer(prev_data.buffer)
            self.test_function(data)
            if data.status != Status.INTERESTING:
                self.exit_with(ExitReason.flaky)

        self.clear_secondary_key()

        while len(self.shrunk_examples) < len(self.interesting_examples):
            target, example = min([
                (k, v) for k, v in self.interesting_examples.items()
                if k not in self.shrunk_examples],
                key=lambda kv: (sort_key(kv[1].buffer), sort_key(repr(kv[0]))),
            )
            self.debug('Shrinking %r' % (target,))

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
                self.settings.database.fetch(self.secondary_key),
                key=sort_key
            )
            for c in corpus:
                primary = {
                    v.buffer for v in self.interesting_examples.values()
                }

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

    def prescreen_buffer(self, buffer):
        """Attempt to rule out buffer as a possible interesting candidate.

        Returns False if we know for sure that running this buffer will not
        produce an interesting result. Returns True if it might (because it
        explores territory we have not previously tried).

        This is purely an optimisation to try to reduce the number of tests we
        run. "return True" would be a valid but inefficient implementation.
        """
        node_index = 0
        n = len(buffer)
        for k, b in enumerate(buffer):
            if node_index in self.dead:
                return False
            try:
                # The block size at that point provides a lower bound on how
                # many more bytes are required. If the buffer does not have
                # enough bytes to fulfill that block size then we can rule out
                # this buffer.
                if k + self.block_sizes[node_index] > n:
                    return False
            except KeyError:
                pass
            try:
                b = self.forced[node_index]
            except KeyError:
                pass
            try:
                b = b & self.masks[node_index]
            except KeyError:
                pass
            try:
                node_index = self.tree[node_index][b]
            except KeyError:
                return True
        else:
            return False

    def cached_test_function(self, buffer):
        node_index = 0
        for c in buffer:
            try:
                c = self.forced[node_index]
            except KeyError:
                pass
            try:
                c = c & self.masks[node_index]
            except KeyError:
                pass
            try:
                node_index = self.tree[node_index][c]
            except KeyError:
                break
            node = self.tree[node_index]
            if isinstance(node, ConjectureData):
                return node
        result = ConjectureData.for_buffer(buffer)
        self.test_function(result)
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


def _is_simple_mask(mask):
    """A simple mask is ``(2 ** n - 1)`` for some ``n``, so it has the effect
    of keeping the lowest ``n`` bits and discarding the rest.

    A mask in this form can produce any integer between 0 and the mask itself
    (inclusive), and the total number of these values is ``(mask + 1)``.
    """
    return (mask & (mask + 1)) == 0


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


def sort_key(buffer):
    return (len(buffer), buffer)


def uniform(random, n):
    return int_to_bytes(random.getrandbits(n * 8), n)


class SampleSet(object):
    """Set data type with the ability to sample uniformly at random from it.

    The mechanism is that we store the set in two parts: A mapping of
    values to their index in an array. Sampling uniformly at random then
    becomes simply a matter of sampling from the array, but we can use
    the index for efficient lookup to add and remove values.
    """

    __slots__ = ('__values', '__index')

    def __init__(self):
        self.__values = []
        self.__index = {}

    def __len__(self):
        return len(self.__values)

    def __repr__(self):
        return 'SampleSet(%r)' % (self.__values,)

    def add(self, value):
        assert value not in self.__index
        # Adding simply consists of adding the value to the end of the array
        # and updating the index.
        self.__index[value] = len(self.__values)
        self.__values.append(value)

    def remove(self, value):
        # To remove a value we first remove it from the index. But this leaves
        # us with the value still in the array, so we have to fix that. We
        # can't simply remove the value from the array, as that would a) Be an
        # O(n) operation and b) Leave the index completely wrong for every
        # value after that index.
        # So what we do is we take the last element of the array and place it
        # in the position of the value we just deleted (if the value was not
        # already the last element of the array. If it was then we don't have
        # to do anything extra). This reorders the array, but that's OK because
        # we don't care about its order, we just need to sample from it.
        i = self.__index.pop(value)
        last = self.__values.pop()
        if i < len(self.__values):
            self.__values[i] = last
            self.__index[last] = i

    def choice(self, random):
        return random.choice(self.__values)


class Negated(object):
    __slots__ = ('tag',)

    def __init__(self, tag):
        self.tag = tag


NEGATED_CACHE = {}  # type: dict


def negated(tag):
    try:
        return NEGATED_CACHE[tag]
    except KeyError:
        result = Negated(tag)
        NEGATED_CACHE[tag] = result
        return result


universal = UniqueIdentifier('universal')


class TargetSelector(object):
    """Data structure for selecting targets to use for mutation.

    The goal is to do a good job of exploiting novelty in examples without
    getting too obsessed with any particular novel factor.

    Roughly speaking what we want to do is give each distinct coverage target
    equal amounts of time. However some coverage targets may be harder to fuzz
    than others, or may only appear in a very small minority of examples, so we
    don't want to let those dominate the testing.

    Targets are selected according to the following rules:

    1. We ideally want valid examples as our starting point. We ignore
       interesting examples entirely, and other than that we restrict ourselves
       to the best example status we've seen so far. If we've only seen
       OVERRUN examples we use those. If we've seen INVALID but not VALID
       examples we use those. Otherwise we use VALID examples.
    2. Among the examples we've seen with the right status, when asked to
       select a target, we select a coverage target and return that along with
       an example exhibiting that target uniformly at random.

    Coverage target selection proceeds as follows:

    1. Whenever we return an example from select, we update the usage count of
       each of its tags.
    2. Whenever we see an example, we add it to the list of examples for all of
       its tags.
    3. When selecting a tag, we select one with a minimal usage count. Among
       those of minimal usage count we select one with the fewest examples.
       Among those, we select one uniformly at random.

    This has the following desirable properties:

    1. When two coverage targets are intrinsically linked (e.g. when you have
       multiple lines in a conditional so that either all or none of them will
       be covered in a conditional) they are naturally deduplicated.
    2. Popular coverage targets will largely be ignored for considering what
       test to run - if every example exhibits a coverage target, picking an
       example because of that target is rather pointless.
    3. When we discover new coverage targets we immediately exploit them until
       we get to the point where we've spent about as much time on them as the
       existing targets.
    4. Among the interesting deduplicated coverage targets we essentially
       round-robin between them, but with a more consistent distribution than
       uniformly at random, which is important particularly for short runs.
    """

    def __init__(self, random):
        self.random = random
        self.best_status = Status.OVERRUN
        self.reset()

    def reset(self):
        self.examples_by_tags = defaultdict(list)
        self.tag_usage_counts = Counter()
        self.tags_by_score = defaultdict(SampleSet)
        self.scores_by_tag = {}
        self.scores = []
        self.mutation_counts = 0
        self.example_counts = 0
        self.non_universal_tags = set()
        self.universal_tags = None

    def add(self, data):
        if data.status == Status.INTERESTING:
            return
        if data.status < self.best_status:
            return
        if data.status > self.best_status:
            self.best_status = data.status
            self.reset()

        if self.universal_tags is None:
            self.universal_tags = set(data.tags)
        else:
            not_actually_universal = self.universal_tags - data.tags
            for t in not_actually_universal:
                self.universal_tags.remove(t)
                self.non_universal_tags.add(t)
                self.examples_by_tags[t] = list(
                    self.examples_by_tags[universal]
                )

        new_tags = data.tags - self.non_universal_tags

        for t in new_tags:
            self.non_universal_tags.add(t)
            self.examples_by_tags[negated(t)] = list(
                self.examples_by_tags[universal]
            )

        self.example_counts += 1
        for t in self.tags_for(data):
            self.examples_by_tags[t].append(data)
            self.rescore(t)

    def has_tag(self, tag, data):
        if tag is universal:
            return True
        if isinstance(tag, Negated):
            return tag.tag not in data.tags
        return tag in data.tags

    def tags_for(self, data):
        yield universal
        for t in data.tags:
            yield t
        for t in self.non_universal_tags:
            if t not in data.tags:
                yield negated(t)

    def rescore(self, tag):
        new_score = (
            self.tag_usage_counts[tag], len(self.examples_by_tags[tag]))
        try:
            old_score = self.scores_by_tag[tag]
        except KeyError:
            pass
        else:
            self.tags_by_score[old_score].remove(tag)
        self.scores_by_tag[tag] = new_score

        sample = self.tags_by_score[new_score]
        if len(sample) == 0:
            heapq.heappush(self.scores, new_score)
        sample.add(tag)

    def select_tag(self):
        while True:
            peek = self.scores[0]
            sample = self.tags_by_score[peek]
            if len(sample) == 0:
                heapq.heappop(self.scores)
            else:
                return sample.choice(self.random)

    def select_example_for_tag(self, t):
        return self.random.choice(self.examples_by_tags[t])

    def select(self):
        t = self.select_tag()
        self.mutation_counts += 1
        result = self.select_example_for_tag(t)
        assert self.has_tag(t, result)
        for s in self.tags_for(result):
            self.tag_usage_counts[s] += 1
            self.rescore(s)
        return t, result


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
                u, v = self.blocks[j]
                if d == '-':
                    value = int_from_bytes(attempt[u:v])
                    if value == 0:
                        failed = True
                        break
                    else:
                        attempt[u:v] = int_to_bytes(value - 1, v - u)
                elif d == 'X':
                    del attempt[u:v]
                else:  # pragma: no cover
                    assert False, 'Unrecognised command %r' % (d,)
            if failed or not self.incorporate_new_buffer(attempt):
                i += 1
    run.command = description
    run.__name__ = 'block_program(%r)' % (description,)
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
        return (
            self.runs,
            self.failures,
            self.calls,
            self.index
        )


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
        'pass_to_descendant',
        'zero_examples',
        'adaptive_example_deletion',
        'reorder_examples',
        'minimize_duplicated_blocks',
        'minimize_individual_blocks',
    ]

    EMERGENCY_PASSES = [
        block_program('-XX'),
        block_program('XX'),
        'example_deletion_with_block_lowering',
        'shrink_offset_pairs',
        'minimize_block_pairs_retaining_sum',
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
            'lower_common_block_offset',
            classification=PassClassification.SPECIAL
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
            pass_function=run, index=len(self.passes),
            classification=classification,
        )
        if hasattr(run, 'command'):
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
        while (
            self.has_queued_passes(classification) and
            self.shrink_target is initial
        ):
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
        return buffer.startswith(self.buffer) or \
            self.incorporate_new_buffer(buffer)

    def incorporate_new_buffer(self, buffer):
        buffer = hbytes(buffer[:self.shrink_target.index])
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

        if not self.__engine.prescreen_buffer(buffer):
            return False

        assert sort_key(buffer) <= sort_key(self.shrink_target.buffer)
        data = ConjectureData.for_buffer(buffer)
        self.__engine.test_function(data)
        self.__test_function_cache[buffer] = data
        return self.incorporate_test_data(data)

    def incorporate_test_data(self, data):
        self.__test_function_cache[data.buffer] = data
        if (
            self.__predicate(data) and
            sort_key(data.buffer) < sort_key(self.shrink_target.buffer)
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

        self.debug('Shrink Pass %s' % (sp.name,))

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
            self.debug('Shrink Pass %s completed.' % (sp.name,))

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
                self.debug('Reclassified %s from %s to %s' % (
                    sp.name, previous.name, sp.classification.name
                ))

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
        if (
            not any(self.shrink_target.buffer) or
            self.incorporate_new_buffer(hbytes(len(self.shrink_target.buffer)))
        ):
            return

        try:
            self.greedy_shrink()
        finally:
            if self.__engine.report_debug_info:
                def s(n):
                    return 's' if n != 1 else ''

                total_deleted = self.initial_size - len(
                    self.shrink_target.buffer)

                self.debug('---------------------')
                self.debug('Shrink pass profiling')
                self.debug('---------------------')
                self.debug('')
                calls = self.__engine.call_count - self.initial_calls
                self.debug((
                    'Shrinking made a total of %d call%s '
                    'of which %d shrank. This deleted %d byte%s out of %d.'
                ) % (
                    calls, s(calls),
                    self.shrinks,
                    total_deleted, s(total_deleted),
                    self.initial_size,
                ))
                for useful in [True, False]:
                    self.debug('')
                    if useful:
                        self.debug('Useful passes:')
                    else:
                        self.debug('Useless passes:')
                    self.debug('')
                    for p in sorted(
                        self.passes,
                        key=lambda t: (
                            -t.calls, -t.runs,
                            t.deletions, t.shrinks,
                        ),
                    ):
                        if p.calls == 0:
                            continue
                        if (p.shrinks != 0) != useful:
                            continue

                        self.debug((
                            '  * %s ran %d time%s, making %d call%s of which '
                            '%d shrank, deleting %d byte%s.'
                        ) % (
                            p.name,
                            p.runs, s(p.runs),
                            p.calls, s(p.calls),
                            p.shrinks,
                            p.deletions, s(p.deletions),
                        ))
                self.debug('')

    def greedy_shrink(self):
        """Run a full set of greedy shrinks (that is, ones that will only ever
        move to a better target) and update shrink_target appropriately.

        This method iterates to a fixed point and so is idempontent - calling
        it twice will have exactly the same effect as calling it once.
        """
        self.run_shrink_pass('alphabet_minimize')
        while self.single_greedy_shrink_iteration():
            self.run_shrink_pass('lower_common_block_offset')

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

        self.run_shrink_pass('remove_discarded')

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
            PassClassification.AVOID
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
            descendants = sorted(set(
                st.buffer[d.start:d.end] for d in self.shrink_target.examples
                if d.start >= ex.start and d.end <= ex.end and
                d.length < ex.length and d.label == ex.label
            ), key=sort_key)

            for d in descendants:
                if self.incorporate_new_buffer(
                    self.buffer[:ex.start] + d + self.buffer[ex.end:]
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
            i,
            t.buffer[:t.blocks[i][0]] in self.__shrinking_prefixes
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
        return not (
            self.is_shrinking_block(i) or
            i in self.shrink_target.forced_blocks
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

        blocked = [current.buffer[u:v] for u, v in current.blocks]

        changed = [
            i for i in sorted(self.__changed_blocks)
            if any(blocked[i]) and i not in self.shrink_target.forced_blocks
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
        """Lower any two blocks offset from each other the same ammount.

        Before this shrink pass, two blocks explicitly offset from each
        other would not get minimized properly:
         >>> b = st.integers(0, 255)
         >>> find(st.tuples(b, b), lambda x: x[0] == x[1] + 1)
        (149,148)

        This expensive (O(n^2)) pass goes through every pair of non-zero
        blocks in the current shrink target and sees if the shrink
        target can be improved by applying an offset to both of them.
        """
        current = [self.shrink_target.buffer[u:v] for u, v in self.blocks]

        def int_from_block(i):
            return int_from_bytes(current[i])

        def block_len(i):
            u, v = self.blocks[i]
            return v - u

        # Try reoffseting every pair
        def reoffset_pair(pair, o):
            n = len(self.blocks)
            # Number of blocks may have changed, need to validate
            valid_pair = [
                p for p in pair if p < n and int_from_block(p) > 0 and
                self.is_payload_block(p)
            ]

            if len(valid_pair) < 2:
                return

            m = min([int_from_block(p) for p in valid_pair])

            new_blocks = [self.shrink_target.buffer[u:v]
                          for u, v in self.blocks]
            for i in valid_pair:
                new_blocks[i] = int_to_bytes(
                    int_from_block(i) + o - m, block_len(i))
            buffer = hbytes().join(new_blocks)
            return self.incorporate_new_buffer(buffer)

        i = 0
        while i < len(self.blocks):
            if self.is_payload_block(i) and int_from_block(i) > 0:
                j = i + 1
                while j < len(self.shrink_target.blocks):
                    block_val = int_from_block(j)
                    i_block_val = int_from_block(i)
                    if self.is_payload_block(j) \
                       and block_val > 0 and i_block_val > 0:
                        offset = min(int_from_block(i),
                                     int_from_block(j))
                        # Save current before shrinking
                        current = [self.shrink_target.buffer[u:v]
                                   for u, v in self.blocks]
                        Integer.shrink(
                            offset, lambda o: reoffset_pair((i, j), o),
                            random=self.random
                        )
                    j += 1
            i += 1

    def mark_shrinking(self, blocks):
        """Mark each of these blocks as a shrinking block: That is, lowering
        its value lexicographically may cause less data to be drawn after."""
        t = self.shrink_target
        for i in blocks:
            if self.__shrinking_block_cache.get(i) is True:
                continue
            self.__shrinking_block_cache[i] = True
            prefix = t.buffer[:t.blocks[i][0]]
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
            if new_target.blocks != self.shrink_target.blocks:
                self.clear_change_tracking()
            else:
                for i, (u, v) in enumerate(self.shrink_target.blocks):
                    if (
                        i not in self.__changed_blocks and
                        current[u:v] != new[u:v]
                    ):
                        self.mark_changed(i)
        else:
            self.__changed_blocks = set()

        self.shrink_target = new_target
        self.__shrinking_block_cache = {}
        self.__intervals = None

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
            u, v = self.blocks[block]
            n = min(v - u, len(b))
            initial_attempt[v - n:v] = b[-n:]

        start = self.shrink_target.blocks[blocks[0]][0]
        end = self.shrink_target.blocks[blocks[-1]][1]

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
            r1, s1 = self.shrink_target.blocks[j]
            r2, s2 = initial_data.blocks[j]
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

            in_original = [
                c for c in ex.children if c.start >= end
            ]

            in_replaced = [
                c for c in replacement.children if c.start >= end
            ]

            if len(in_replaced) >= len(in_original) or not in_replaced:
                continue

            # We've found an example where some of the children went missing
            # as a result of this change, and just replacing it with the data
            # it would have had and removing the spillover didn't work. This
            # means that some of its children towards the right must be
            # important, so we try to arrange it so that it retains its
            # rightmost children instead of its leftmost.
            regions_to_delete.add((
                in_original[0].start, in_original[-len(in_replaced)].start
            ))

        for u, v in sorted(
            regions_to_delete, key=lambda x: x[1] - x[0], reverse=True
        ):
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
                if ex.discarded and (
                    not discarded or ex.start >= discarded[-1][-1]
                ):
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
            pieces = [
                st.buffer[c.start:c.end]
                for c in ex.children
            ]
            if not pieces:
                pieces = [st.buffer[ex.start:ex.end]]
            prefix = st.buffer[:ex.start]
            suffix = st.buffer[ex.end:]
            shrinker.shrink(
                pieces, lambda ls: self.incorporate_new_buffer(
                    prefix + hbytes().join(ls) + suffix,
                ), random=self.random, **kwargs
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

            # FIXME: IOU one attempt to debug this - DRMacIver
            # This is a mysterious problem that should be impossible to trigger
            # but isn't. I don't know what's going on, and it defeated my
            # my attempts to reproduce or debug it. I'd *guess* it's related to
            # nondeterminism in the test function. That should be impossible in
            # the cases where I'm seeing it, but I haven't been able to put
            # together a reliable reproduction of it.
            if ex.index >= len(attempt.examples):  # pragma: no cover
                continue

            in_replacement = attempt.examples[ex.index]
            used = in_replacement.length

            if (
                not self.__predicate(attempt) and
                in_replacement.end < len(attempt.buffer) and
                used < ex.length
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
            canon(self.shrink_target.buffer[u:v])
            for u, v in self.blocks
        )
        counts.pop(hbytes(), None)
        blocks = [buffer for buffer, count in counts.items() if count > 1]

        blocks.sort(reverse=True)
        blocks.sort(key=lambda b: counts[b] * len(b), reverse=True)
        for block in blocks:
            targets = [
                i for i, (u, v) in enumerate(self.blocks)
                if canon(self.shrink_target.buffer[u:v]) == block
            ]
            # This can happen if some blocks have been lost in the previous
            # shrinking.
            if len(targets) <= 1:
                continue

            Lexical.shrink(
                block,
                lambda b: self.try_shrinking_blocks(targets, b),
                random=self.random, full=False
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
            u, v = self.blocks[i]
            Lexical.shrink(
                self.shrink_target.buffer[u:v],
                lambda b: self.try_shrinking_blocks((i,), b),
                random=self.random, full=False,
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

            u, v = self.blocks[i]

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
                del buf[ex.start:ex.end]
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
        i = 0
        while i < len(self.shrink_target.blocks):
            if self.is_payload_block(i):
                j = i + 1
                while j < len(self.shrink_target.blocks):
                    u, v = self.shrink_target.blocks[i]
                    m = int_from_bytes(self.shrink_target.buffer[u:v])
                    if m == 0:
                        break
                    r, s = self.shrink_target.blocks[j]
                    n = int_from_bytes(self.shrink_target.buffer[r:s])

                    if (
                        s - r == v - u and
                        self.is_payload_block(j)
                    ):
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
                            Integer.shrink(
                                m, lambda x: trial(x, tot - x),
                                random=self.random
                            )
                    j += 1
            i += 1

    def reorder_examples(self):
        """This pass allows us to reorder pairs of examples which come from the
        same strategy (or strategies that happen to pun to the same label by
        accident, but that shouldn't happen often).

        For example, consider the following:

        .. code-block:: python

            import hypothesis.strategies as st
            from hypothesis import given

            @given(st.text(), st.text())
            def test_does_not_exceed_100(x, y):
                assert x != y

        Without the ability to reorder x and y this could fail either with
        ``x="", ``y="0"``, or the other way around. With reordering it will
        reliably fail with ``x=""``, ``y="0"``.
        """
        self.example_wise_shrink(Ordering, key=sort_key)

    def alphabet_minimize(self):
        """Attempts to replace most bytes in the buffer with 0 or 1. The main
        benefit of this is that it significantly increases our cache hit rate
        by making things that are equivalent more likely to have the same
        representation.

        We only run this once rather than as part of the main passes as
        once it's done its magic it's unlikely to ever be useful again.
        It's important that it runs first though, because it makes
        everything that comes after it faster because of the cache hits.
        """
        for c in (1, 0):
            alphabet = set(self.buffer) - set(hrange(c + 1))

            if not alphabet:
                continue

            def clear_to(reduced):
                reduced = set(reduced)
                attempt = hbytes([
                    b if b <= c or b in reduced else c
                    for b in self.buffer
                ])
                return self.consider_new_buffer(attempt)

            Length.shrink(
                sorted(alphabet), clear_to,
                random=self.random,
            )
