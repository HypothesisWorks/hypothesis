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
from collections import defaultdict

import attr

from hypothesis import Phase, Verbosity, HealthCheck
from hypothesis import settings as Settings
from hypothesis.reporting import debug_report
from hypothesis.internal.compat import Counter, ceil, hbytes, hrange, \
    int_to_text, int_to_bytes, benchmark_time, int_from_bytes, \
    to_bytes_sequence, unicode_safe_repr
from hypothesis.utils.conventions import UniqueIdentifier
from hypothesis.internal.healthcheck import fail_health_check
from hypothesis.internal.conjecture.data import MAX_DEPTH, Status, \
    StopTest, ConjectureData
from hypothesis.internal.conjecture.minimizer import minimize, minimize_int

# Tell pytest to omit the body of this module from tracebacks
# http://doc.pytest.org/en/latest/example/simple.html#writing-well-integrated-assertion-helpers
__tracebackhide__ = True


HUNG_TEST_TIME_LIMIT = 5 * 60


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

        # Maps tree indices to the maximum byte that is valid at that point.
        # Currently this is only used inside draw_bits, but it potentially
        # could get used elsewhere.
        self.capped = {}

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
                self.capped[node_index] = data.capped_indices[i]
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
            # In that case we alrady have this section of the tree mapped.
            if u >= len(indices):
                break
            self.block_sizes[indices[u]] = v - u

        self.dead.update(indices[self.cap:])

        if data.status != Status.OVERRUN and node_index not in self.dead:
            self.dead.add(node_index)
            self.tree[node_index] = data

            for j in reversed(indices):
                if (
                    len(self.tree[j]) < self.capped.get(j, 255) + 1 and
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

            if self.shrinks >= self.settings.max_shrinks:
                self.exit_with(ExitReason.max_shrinks)
        if (
            self.settings.timeout > 0 and
            benchmark_time() >= self.start_time + self.settings.timeout
        ):
            self.exit_with(ExitReason.timeout)

        if not self.interesting_examples:
            if self.valid_examples >= self.settings.max_examples:
                self.exit_with(ExitReason.max_examples)
            if self.call_count >= max(
                self.settings.max_iterations, self.settings.max_examples
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
            upper_bound = self.capped.get(node, 255) + 1
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
        if self.settings.database is not None:
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
        with self.settings:
            debug_report(message)

    def debug_data(self, data):
        if self.settings.verbosity < Verbosity.debug:
            return
        buffer_parts = [u"["]
        for i, (u, v) in enumerate(data.blocks):
            if i > 0:
                buffer_parts.append(u" || ")
            buffer_parts.append(
                u', '.join(int_to_text(int(i)) for i in data.buffer[u:v]))
        buffer_parts.append(u']')

        status = unicode_safe_repr(data.status)

        if data.status == Status.INTERESTING:
            status = u'%s (%s)' % (
                status, unicode_safe_repr(data.interesting_origin,))

        self.debug(u'%d bytes %s -> %s, %s' % (
            data.index,
            u''.join(buffer_parts),
            status,
            data.output,
        ))

    def run(self):
        with self.settings:
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

        if self.settings.perform_health_check:
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
            cap = max(
                sort_key(v.buffer)
                for v in self.interesting_examples.values()
            )
            for c in corpus:
                if sort_key(c) >= cap:
                    break
                else:
                    data = self.cached_test_function(c)
                    if (
                        data.status != Status.INTERESTING or
                        self.interesting_examples[data.interesting_origin]
                        is not data
                    ):
                        self.settings.database.delete(
                            self.secondary_key, c)

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
                b = min(b, self.capped[node_index])
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
        for i in hrange(self.settings.buffer_size):
            try:
                c = self.forced[node_index]
            except KeyError:
                if i < len(buffer):
                    c = buffer[i]
                else:
                    c = 0
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


NEGATED_CACHE = {}


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
        self.__discarding_failed = False
        self.__shrinking_prefixes = set()

        # We keep track of the current best example on the shrink_target
        # attribute.
        self.shrink_target = None
        self.update_shrink_target(initial)

    def incorporate_new_buffer(self, buffer):
        buffer = hbytes(buffer[:self.shrink_target.index])
        assert sort_key(buffer) < sort_key(self.shrink_target.buffer)

        if self.shrink_target.buffer.startswith(buffer):
            return False

        if not self.__engine.prescreen_buffer(buffer):
            return False

        assert sort_key(buffer) <= sort_key(self.shrink_target.buffer)
        data = ConjectureData.for_buffer(buffer)
        self.__engine.test_function(data)
        return self.incorporate_test_data(data)

    def incorporate_test_data(self, data):
        if (
            self.__predicate(data) and
            sort_key(data.buffer) < sort_key(self.shrink_target.buffer)
        ):
            self.update_shrink_target(data)
            self.__shrinking_block_cache = {}
            if data.has_discards and not self.__discarding_failed:
                self.remove_discarded()
            return True
        return False

    def cached_test_function(self, buffer):
        result = self.__engine.cached_test_function(buffer)
        self.incorporate_test_data(result)
        return result

    def debug(self, msg):
        self.__engine.debug(msg)

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

        self.greedy_shrink()
        self.escape_local_minimum()

    def greedy_shrink(self):
        """Run a full set of greedy shrinks (that is, ones that will only ever
        move to a better target) and update shrink_target appropriately.

        This method iterates to a fixed point and so is idempontent - calling
        it twice will have exactly the same effect as calling it once.

        """
        run_expensive_shrinks = False

        prev = None
        while prev is not self.shrink_target:
            prev = self.shrink_target

            # We reset our tracking of what changed at the beginning of the
            # loop so that we don't get distracted by things that change once
            # and then are stable thereafter.
            self.clear_change_tracking()

            self.remove_discarded()
            self.adaptive_example_deletion()
            self.zero_draws()
            self.minimize_duplicated_blocks()
            self.minimize_individual_blocks()
            self.reorder_blocks()
            self.lower_dependent_block_pairs()
            self.lower_common_block_offset()

            # Passes after this point are expensive: Prior to here they should
            # all involve no more than about n log(n) shrinks, but after here
            # they may be quadratic or worse. Running all of the passes until
            # they make no changes is important for correctness, but nothing
            # says we have to run all of them on each run! So if the fast
            # passes still seem to be making useful changes, we restart the
            # loop here and give them another go.
            # To avoid the case where the expensive shrinks unlock a trivial
            # change in one of the previous passes causing this to become much
            # more expensive by doubling the number of times we have to run
            # them to get to run the expensive passes again, we make this
            # decision "sticky" - once it's been useful to run the expensive
            # changes at least once, we always run them.
            if prev is self.shrink_target:
                run_expensive_shrinks = True

            if not run_expensive_shrinks:
                continue

            self.interval_deletion_with_block_lowering()
            self.pass_to_interval()
            self.reorder_bytes()

    @property
    def blocks(self):
        return self.shrink_target.blocks

    @property
    def intervals(self):
        if self.__intervals is None:
            target = self.shrink_target
            intervals = set(target.blocks)
            intervals.add((0, target.index))
            intervals.update(
                (ex.start, ex.end) for ex in target.examples
                if ex.start < ex.end
            )
            intervals_by_level = {}
            for ex in target.examples:
                if ex.start < ex.end:
                    intervals_by_level.setdefault(ex.depth, []).append(ex)
            for l in intervals_by_level.values():
                for e1, e2 in zip(l, l[1:]):
                    if (
                        not (e1.discarded or e2.discarded) and
                        e1.end == e2.start
                    ):
                        intervals.add((e1.start, e2.end))
            for i in hrange(len(target.blocks) - 1):
                intervals.add((target.blocks[i][0], target.blocks[i + 1][1]))
            # Intervals are sorted as longest first, then by interval start.
            self.__intervals = tuple(sorted(
                set(intervals),
                key=lambda se: (se[0] - se[1], se[0])
            ))
        return self.__intervals

    def zero_draws(self):
        """Attempt to replace each draw call with its minimal possible value.

        This is intended as a fast-track to minimize whole sub-examples that
        don't matter as rapidly as possible. For example, suppose we had
        something like the following:

        ls = data.draw(st.lists(st.lists(st.integers())))
        assert len(ls) >= 10

        Then each of the elements of ls need to be minimized, and we can do
        that by deleting individual values from them, but we'd much rather do
        it fast rather than slow - deleting elements one at a time takes
        sum(map(len, ls)) shrinks, and ideally we'd do this in len(ls) shrinks
        as we try to replace each element with [].

        This pass does that by identifying the size of the "natural smallest"
        element here. It first tries replacing an entire interval with zero.
        This will sometimes work (e.g. when the interval is a block), but often
        what will happen is that there will be leftover zeros that spill over
        into the next example and ruin things - e.g. here if ls[0] is non-empty
        and we replace it with all zero, some of the extra zeros will be
        interpreted as terminating ls and will shrink it down to a one element
        list, causing the test to pass.

        So what we do instead is that once we've evaluated that shrink, we use
        the size of the intervals there to find other possible sizes that we
        could try replacing the interval with. In this case we'd spot that
        there is a one-byte interval starting at right place for ls[i] and try
        to replace it with that. This will successfully replace ls[i] with []
        as desired.

        """
        i = 0
        while i < len(self.shrink_target.examples):
            ex = self.shrink_target.examples[i]
            buf = self.shrink_target.buffer
            if any(buf[ex.start:ex.end]):
                prefix = buf[:ex.start]
                suffix = buf[ex.end:]
                attempt = self.cached_test_function(
                    prefix + hbytes(ex.length) + suffix
                )
                if attempt.status == Status.VALID:
                    replacement = attempt.examples[i]
                    assert replacement.start == ex.start
                    if replacement.length < ex.length:
                        self.incorporate_new_buffer(
                            prefix + hbytes(replacement.length) + suffix
                        )
            i += 1

    def pass_to_interval(self):
        """Attempt to replace each interval with a subinterval.

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
        i = 0
        while i < len(self.shrink_target.examples):
            ex = self.shrink_target.examples[i]
            changed = False

            for j in hrange(i + 1, len(self.shrink_target.examples)):
                child = self.shrink_target.examples[j]
                if child.start >= ex.end:
                    break
                if child.length < ex.length:
                    buf = self.shrink_target.buffer
                    if self.incorporate_new_buffer(
                        buf[:ex.start] + buf[child.start:child.end] +
                        buf[ex.end:]
                    ):
                        changed = True
                        break
            if not changed:
                i += 1

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

        self.debug('Removing common block offset')

        current = self.shrink_target

        blocked = [current.buffer[u:v] for u, v in current.blocks]

        changed = sorted(self.__changed_blocks)

        ints = [int_from_bytes(blocked[i]) for i in changed]
        offset = min(ints)
        if offset == 0:
            return

        for i in hrange(len(ints)):
            ints[i] -= offset

        def reoffset(o):
            new_blocks = list(blocked)
            for i, v in zip(changed, ints):
                new_blocks[i] = int_to_bytes(v + o, len(blocked[i]))
            return self.incorporate_new_buffer(hbytes().join(new_blocks))

        minimize_int(offset, reoffset)

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

    def update_shrink_target(self, new_target):
        assert new_target.frozen
        if self.shrink_target is not None:
            if new_target.blocks != self.shrink_target.blocks:
                self.__changed_blocks = set()
            else:
                current = self.shrink_target.buffer
                new = new_target.buffer

                for i, (u, v) in enumerate(self.shrink_target.blocks):
                    if (
                        i not in self.__changed_blocks and
                        current[u:v] != new[u:v]
                    ):
                        self.__changed_blocks.add(i)
        else:
            self.__changed_blocks = set()

        self.shrink_target = new_target
        self.__shrinking_block_cache = {}
        self.__intervals = None

    def escape_local_minimum(self):
        """Attempt to restart the shrink process from a larger initial value in
        a way that allows us to escape a local minimum that the main greedy
        shrink process will get stuck in.

        The idea is that when we've completed the shrink process, we try
        starting it again from something reasonably near to the shrunk example
        that is likely to exhibit the same behaviour.

        We search for an example that is selected randomly among ones that are
        "structurally similar" to the original. If we don't find one we bail
        out fairly quickly as this will usually not work. If we do, we restart
        the shrink process from there. If this results in us finding a better
        final example, we do this again until it stops working.

        This is especially useful for things where the tendency to move
        complexity to the right works against us - often a generic instance of
        the problem is easy to shrink, but trying to reduce the size of a
        minimized example further is hard. For example suppose we had something
        like:

        x = data.draw(lists(integers()))
        y = data.draw(lists(integers(), min_size=len(x), max_size=len(x)))
        assert not (any(x) and any(y))

        Then this could shrink to something like [0, 1], [0, 1].

        Attempting to shrink this further by deleting an element of x would
        result in losing the last element of y, and the test would start
        passing. But if we were to replace this with [a, b], [c, d] with c != 0
        then deleting a or b would work.

        """
        count = 0
        while count < 10:
            count += 1
            self.debug('Retrying from random restart')
            attempt_buf = bytearray(self.shrink_target.buffer)

            # We use the shrinking information to identify the
            # structural locations in the byte stream - if lowering
            # the block would result in changing the size of the
            # example, changing it here is too likely to break whatever
            # it was caused the behaviour we're trying to shrink.
            # Everything non-structural, we redraw uniformly at random.
            for i, (u, v) in enumerate(self.blocks):
                if not self.is_shrinking_block(i):
                    attempt_buf[u:v] = uniform(self.__engine.random, v - u)
            attempt = self.cached_test_function(attempt_buf)
            if self.__predicate(attempt):
                prev = self.shrink_target
                self.update_shrink_target(attempt)
                self.__shrinking_block_cache = {}
                self.greedy_shrink()
                if (
                    sort_key(self.shrink_target.buffer) <
                    sort_key(prev.buffer)
                ):
                    # We have successfully shrunk the example past where
                    # we started from. Now we begin the whole processs
                    # again from the new, smaller, example.
                    count = 0
                else:
                    self.update_shrink_target(prev)
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
        there is some size dependency on the value of a block. The amount of
        work done here is relatively small - most such dependencies will be
        handled by the interval_deletion_with_block_lowering pass - but will be
        effective when there is a large amount of redundant data after the
        block to be lowered.

        """
        initial_attempt = bytearray(self.shrink_target.buffer)
        for i in blocks:
            if i >= len(self.blocks):
                break
            u, v = self.blocks[i]
            n = min(v - u, len(b))
            initial_attempt[v - n:v] = b[-n:]

        initial_data = self.cached_test_function(initial_attempt)

        if initial_data.status == Status.INTERESTING:
            return initial_data is self.shrink_target

        # If this produced something completely invalid we ditch it
        # here rather than trying to persevere.
        if initial_data.status < Status.VALID:
            return False

        if len(initial_data.buffer) < v:
            return False

        lost_data = len(self.shrink_target.buffer) - len(initial_data.buffer)

        # If this did not in fact cause the data size to shrink we
        # bail here because it's not worth trying to delete stuff from
        # the remainder.
        if lost_data <= 0:
            return False

        self.mark_shrinking(blocks)

        try_with_deleted = bytearray(initial_attempt)
        del try_with_deleted[v:v + lost_data]

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
        if not self.shrink_target.has_discards:
            return

        discarded = []

        for ex in self.shrink_target.examples:
            if ex.discarded and (
                not discarded or ex.start >= discarded[-1][-1]
            ):
                discarded.append((ex.start, ex.end))

        attempt = bytearray(self.shrink_target.buffer)
        for u, v in reversed(discarded):
            del attempt[u:v]

        # We track whether discarding works because as long as it does we will
        # always want to run it whenever the option is available - whenever a
        # shrink ends up introducing new discarded data we can attempt to
        # delete it immediately. However if some discarded data looks essential
        # in some way then that would be wasteful, so we turn off the automatic
        # discarding if this ever fails. When this next runs explicitly, it
        # will reset the flag if the status changes.
        self.__discarding_failed = not self.incorporate_new_buffer(attempt)

    def adaptive_example_deletion(self):
        """Attempt to delete every draw call, plus some short sequences of draw
        calls.

        The only things this guarantees to attempt to delete are every draw
        call and every draw call plus its immediate successor (the first
        non-empty draw call that starts strictly after it). However if this
        seems to be working pretty well it will do its best to exploit that
        and adapt to the fact there's currently a lot that it can delete.

        This is the main point at which we try to lower the size of the data.
        e.g. if we have two successive draw calls, this will attempt to delete
        the first and replace it with the second.

        The fact that this will also try deleting the successor call is
        important. For example, if we have something like:

        while many.more(data):
            data.draw(stuff)

        This pass will attempt to delete adjacent pairs of calls to shorten the
        loop.

        """
        self.debug('greedy interval deletes')
        i = 0
        while i < len(self.shrink_target.examples):
            if self.shrink_target.examples[i].length == 0:
                i += 1
                continue

            # Note: We do want this fixed rather than changing during this
            # iteration of the loop.
            target = self.shrink_target

            def try_delete_range(k):
                """Can we delete k non-trivial non-overlapping examples
                starting from i?"""
                stack = []
                j = i
                while k > 0 and j < len(target.examples):
                    ex = target.examples[j]
                    if ex.length > 0 and (
                        not stack or stack[-1][1] <= ex.start
                    ):
                        stack.append((ex.start, ex.end))
                        k -= 1
                    j += 1
                assert stack
                attempt = bytearray(target.buffer)
                for u, v in reversed(stack):
                    del attempt[u:v]
                attempt = hbytes(attempt)
                if sort_key(attempt) >= sort_key(self.shrink_target.buffer):
                    return False
                return self.incorporate_new_buffer(attempt)

            # This is an adaptive pass loosely modelled after timsort. If
            # little or nothing is deletable here then we don't try any more
            # deletions than the naive greedy algorithm would, but if it looks
            # like we have an opportunity to delete a lot then we try to do so.

            # What we're trying to do is to find a large k such that we can
            # delete k but not k + 1 draws starting from this point, and we
            # want to do that in O(log(k)) rather than O(k) test executions.

            # We try a quite careful sequence of small shrinks here before we
            # move on to anything big. This is because if we try to be
            # aggressive too early on we'll tend to find that we lose out when
            # the example is "nearly minimal".
            if try_delete_range(2):
                if try_delete_range(3) and try_delete_range(4):

                    # At this point it looks like we've got a pretty good
                    # opportunity for a long run here. We do an exponential
                    # probe upwards to try and find some k where we can't
                    # delete many intervals. We do this rather than choosing
                    # that upper bound to immediately be large because we
                    # don't really expect k to be huge. If it turns out that
                    # it is, the subsequent example is going to be so tiny that
                    # it doesn't really matter if we waste a bit of extra time
                    # here.
                    hi = 5
                    while try_delete_range(hi):
                        assert hi <= len(target.examples)
                        hi *= 2

                    # We now know that we can delete the first lo intervals but
                    # not the first hi. We preserve that property while doing
                    # a binary search to find the point at which we stop being
                    # able to delete intervals.
                    lo = 4
                    while lo + 1 < hi:
                        mid = (lo + hi) // 2
                        if try_delete_range(mid):
                            lo = mid
                        else:
                            hi = mid
            else:
                try_delete_range(1)
            # We unconditionally bump i because we have always tried deleting
            # one more example than we succeeded at deleting, so we expect the
            # next example to be undeletable.
            i += 1

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
        self.debug('Simultaneous shrinking of duplicated blocks')

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

            minimize(
                block,
                lambda b: self.try_shrinking_blocks(targets, b),
                random=self.__engine.random, full=False
            )

    def minimize_individual_blocks(self):
        """Attempt to minimize each block in sequence.

        This is the pass that ensures that e.g. each integer we draw is a
        minimum value. So it's the part that guarantees that if we e.g. do

        x = data.draw(integers())
        assert x < 10

        then in our shrunk example, x = 10 rather than say 97.

        """
        self.debug('Shrinking of individual blocks')
        i = 0
        while i < len(self.blocks):
            u, v = self.blocks[i]
            minimize(
                self.shrink_target.buffer[u:v],
                lambda b: self.try_shrinking_blocks((i,), b),
                random=self.__engine.random, full=False,
            )
            i += 1

    def reorder_blocks(self):
        """Attempt to reorder blocks of the same size so that lexically larger
        values go later.

        This is mostly useful for canonicalization of examples. e.g. if we have

        x = data.draw(st.integers())
        y = data.draw(st.integers())
        assert x == y

        Then by minimizing x and y individually this could give us either
        x=0, y=1 or x=1, y=0. According to our sorting order, the former is a
        better example, but if in our initial draw y was zero then we will not
        get it.

        When this pass runs it will swap the values of x and y if that occurs.

        As well as canonicalization, this can also unblock other things. For
        example suppose we have

        n = data.draw(st.integers(0, 10))
        ls = data.draw(st.lists(st.integers(), min_size=n, max_size=n))
        assert len([x for x in ls if x != 0]) <= 1

        We could end up with something like [1, 0, 0, 1] if we started from the
        wrong place. This pass would reorder this to [0, 0, 1, 1]. Shrinking n
        can then try to delete the lost bytes (see try_shrinking_blocks for how
        this works), taking us immediately to [1, 1]. This is a less important
        role for this pass, but still significant.

        """
        self.debug('Reordering blocks')
        block_lengths = sorted(self.shrink_target.block_starts, reverse=True)
        for n in block_lengths:
            i = 1
            while i < len(self.shrink_target.block_starts.get(n, ())):
                j = i
                while j > 0:
                    buf = self.shrink_target.buffer
                    blocks = self.shrink_target.block_starts[n]
                    a_start = blocks[j - 1]
                    b_start = blocks[j]
                    a = buf[a_start:a_start + n]
                    b = buf[b_start:b_start + n]
                    if a <= b:
                        break
                    swapped = (
                        buf[:a_start] + b + buf[a_start + n:b_start] +
                        a + buf[b_start + n:])
                    assert len(swapped) == len(buf)
                    assert swapped < buf
                    if self.incorporate_new_buffer(swapped):
                        j -= 1
                    else:
                        break
                i += 1

    def interval_deletion_with_block_lowering(self):
        """This pass tries to delete each interval while replacing a block that
        precedes that interval with its immediate two lexicographical
        predecessors.

        We only do this for blocks that are marked as shrinking - that
        is, when we tried lowering them it resulted in a smaller example.
        This makes it important that this runs after minimize_individual_blocks
        (which populates those blocks).

        The reason for this pass is that it guarantees that we can delete
        elements of ls in the following scenario:

        n = data.draw(st.integers(0, 10))
        ls = data.draw(st.lists(st.integers(), min_size=n, max_size=n))

        Replacing the block for n with its predecessor replaces n with n - 1,
        and deleting a draw call in ls means that we draw exactly the desired
        n - 1 elements for this list.

        We actually also try replacing n with n - 2, as we will have intervals
        for adjacent pairs of draws and that ensures that those will find the
        right block lowering in this case too.

        This is necessarily a somewhat expensive pass - worst case scenario it
        tries len(blocks) * len(intervals) = O(len(buffer)^2 log(len(buffer)))
        shrinks, so it's important that it runs late in the process when the
        example size is small and most of the blocks that can be zeroed have
        been.

        """
        self.debug('Lowering blocks while deleting intervals')
        i = 0
        while i < len(self.intervals):
            u, v = self.intervals[i]
            changed = False
            # This loop never exits normally because the r >= u branch will
            # always trigger once we find a block inside the interval, hence
            # the pragma.
            for j, (r, s) in enumerate(  # pragma: no branch
                self.blocks
            ):
                if r >= u:
                    break
                if not self.is_shrinking_block(j):
                    continue
                b = self.shrink_target.buffer[r:s]
                if any(b):
                    n = int_from_bytes(b)

                    for m in hrange(max(n - 2, 0), n):
                        c = int_to_bytes(m, len(b))
                        attempt = bytearray(self.shrink_target.buffer)
                        attempt[r:s] = c
                        del attempt[u:v]
                        if self.incorporate_new_buffer(attempt):
                            changed = True
                            break
                    if changed:
                        break
            if not changed:
                i += 1

    def lower_dependent_block_pairs(self):
        """This is a fairly specific shrink pass that is mostly specialised for
        our integers strategy, though is probably useful in other places.

        It looks for adjacent pairs of blocks where lowering the value of the
        first changes the size of the second. Where this happens, we may lose
        interestingness because this takes the prefix rather than the suffix
        of the next block, so if lowering the block produces an uninteresting
        value and this change happens, we try replacing the second block with
        its suffix and shrink again.

        For example suppose we had:

            m = data.draw_bits(8)
            n = data.draw_bits(m)

        And initially we draw m = 9, n = 1. This gives us the bytes [9, 0, 1].
        If we lower 9 to 8 then we now read [9, 0], because the block size of
        the n has changed. This pass allows us to also try [9, 1], which
        corresponds to m=8, n=1 as desired.

        This should *mostly* be handled by the minimize_individual_blocks pass,
        but that won't always work because its length heuristic can be wrong if
        the changes to the next block have knock on size changes, while this
        one triggers more reliably.

        """
        self.debug('Lowering adjacent pairs of dependent blocks')
        i = 0
        while i + 1 < len(self.blocks):
            u, v = self.blocks[i]
            i += 1

            b = int_from_bytes(self.shrink_target.buffer[u:v])
            if b > 0:
                attempt = bytearray(self.shrink_target.buffer)
                attempt[u:v] = int_to_bytes(b - 1, v - u)
                attempt = hbytes(attempt)
                shrunk = self.cached_test_function(attempt)
                if (
                    shrunk is not self.shrink_target and
                    i < len(shrunk.blocks) and
                    shrunk.blocks[i][1] < self.blocks[i][1]
                ):
                    _, r = self.blocks[i]
                    k = shrunk.blocks[i][1] - shrunk.blocks[i][0]
                    buf = attempt[:v] + self.shrink_target.buffer[r - k:]
                    self.incorporate_new_buffer(buf)

    def reorder_bytes(self):
        """This is a hyper-specific and moderately expensive shrink pass. It is
        designed to do similar things to reorder_blocks, but it works in cases
        where reorder_blocks may fail.

        The idea is that we expect to have a *lot* of single byte blocks, and
        they have very different meanings and interpretations. This means that
        the reasonably cheap approach of doing what is basically insertion sort
        on these blocks is unlikely to work.

        So instead we try to identify the subset of the single-byte blocks that
        we can freely move around and more aggressively put those into a sorted
        order.

        This is useful because e.g. we draw integers as single bytes, and if we
        don't have a pass like that then we're unable to shrink from [10, 0] to
        [0, 10].

        In the event that we fail to do much sorting this is O(number of out of
        order pairs), which is O(n^2) in the worst case. In order to offset we
        try to do as much efficient sorting as possible to reduce the number of
        out of order pairs before we get to that stage.

        """
        free_bytes = []

        for i, (u, v) in enumerate(self.blocks):
            if (
                v == u + 1 and
                u not in self.shrink_target.forced_indices
            ):
                free_bytes.append(u)

        if not free_bytes:
            return

        original = self.shrink_target

        def attempt(new_ordering):
            assert len(new_ordering) == len(free_bytes)
            assert len(self.shrink_target.buffer) == len(original.buffer)

            attempt = bytearray(self.shrink_target.buffer)
            for i, b in zip(free_bytes, new_ordering):
                attempt[i] = b
            return self.incorporate_new_buffer(attempt)

        ordering = [self.shrink_target.buffer[i] for i in free_bytes]

        if ordering == sorted(ordering):
            return

        if attempt(sorted(ordering)):
            return True

        n = len(ordering)

        # We now try to sort the "high bytes". The idea here is that high bytes
        # are more likely to be "payload" in some sense: Their value matters
        # mostly in relation to the other values. Additionally they are likely
        # to be moved around more in the reordering, so if we can get them
        # sorted up front we will save a lot of time later.

        # In order to do this we use binary search to find a value v such that
        # we can sort all values >= v. We do this in at most 8 steps (usually
        # less).

        # Invariant: We can sort the set of bytes which are >= hi, we can't
        # sort the set of bytes that are >= lo.

        # But see comment below about how these invariants may occasionally be
        # violated.
        lo = min(ordering)
        hi = max(ordering)
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            excessive = [i for i in hrange(n) if ordering[i] >= mid]
            trial = list(ordering)
            for i, b in zip(excessive, sorted(ordering[i] for i in excessive)):
                trial[i] = b
            if trial == ordering or attempt(trial):
                if (
                    len(self.shrink_target.buffer) !=
                    len(original.buffer)
                ):
                    return
                # Technically this could result in us violating our invariants
                # if the bytes change too much. However if that happens the
                # loop is still useful so we carry on as if it didn't.
                ordering = [
                    self.shrink_target.buffer[i] for i in free_bytes]
                hi = mid
            else:
                lo = mid

        i = 1
        while i < n:
            for k in hrange(i - 1, -1, -1):
                if ordering[k] <= ordering[i]:
                    continue
                swapped = list(ordering)
                swapped[k], swapped[i] = swapped[i], swapped[k]
                if attempt(swapped):
                    i = k
                    if (
                        len(self.shrink_target.buffer) !=
                        len(original.buffer)
                    ):
                        return
                    ordering = [
                        self.shrink_target.buffer[i] for i in free_bytes]
                    break
            else:
                i += 1
