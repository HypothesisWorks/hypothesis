# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2016 David R. MacIver
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

import time
from enum import Enum, IntEnum
from array import array
from random import Random, getrandbits
from weakref import ref, WeakKeyDictionary

from hypothesis import settings as Settings
from hypothesis import Phase
from hypothesis.errors import Flaky
from hypothesis.reporting import debug_report
from hypothesis.internal.compat import hbytes, hrange, Counter, \
    text_type, unicode_safe_repr
from hypothesis.internal.conjecture.data import Status, Sampler, \
    StopTest, ConjectureData
from hypothesis.internal.conjecture.minimizer import minimize


class ExitReason(Enum):
    max_examples = 0
    max_iterations = 1
    timeout = 2
    max_shrinks = 3
    finished = 4
    flaky = 5


class NodeStatus(IntEnum):
    UNEXPLORED = 0
    EXPLORED = 1
    FINISHED = 2


class TreeNode(object):

    def __init__(self, index, parent):
        self.parent = parent
        self.index = index
        assert parent is None or index < len(parent().weights)
        self.children = {}
        self.status = NodeStatus.UNEXPLORED
        self.explore_depth = -1
        self.__selection_weights = None

    @property
    def path(self):
        result = bytearray()
        p = self
        while p.parent is not None:
            result.append(p.char)
            p = p.parent()
        result.reverse()
        return hbytes(result)

    def __repr__(self):
        return 'TreeNode(%r, %r)' % (
            self.status, getattr(self, 'children', None))

    def explore(self, weights, choices):
        weights = tuple(weights)
        choices = tuple(choices)
        if self.status == NodeStatus.UNEXPLORED:
            self.live_count = len([w for w in weights if w > 0])
            if weights:
                self.weights = weights
                self.choices = choices
                self.status = NodeStatus.EXPLORED
            else:
                self.status = NodeStatus.FINISHED
                self.weights = ()
                self.choices = ()
        else:
            if (
                weights != self.weights or
                choices != self.choices
            ):
                raise Flaky(
                    'Saw different options on different visits. Expected %r '
                    'but got %r.' % (
                        list(zip(self.choices, self.weights)),
                        list(zip(choices, weights)),
                    ))

    @property
    def selection_weights(self):
        if self.__selection_weights is None:
            self.__selection_weights = array('d', self.weights)
            self.__selectable = len([w for w in self.weights if w > 0])
        return self.__selection_weights

    def __valid_choices(self):
        for w, c in zip(self.weights, self.choices):
            if w > 0:
                yield c

    @property
    def char(self):
        return self.parent().choices[self.index]

    @property
    def finished(self):
        return self.status == NodeStatus.FINISHED

    def update_ancestors(self):
        node = self
        while node.parent is not None:
            parent = node.parent()
            assert parent is not node
            if not parent.finished:
                if node.finished:
                    assert parent.live_count > 0, parent.live_count
                    parent.live_count -= 1
                    if parent.live_count == 0:
                        parent.status = NodeStatus.FINISHED
                        continue
                parent.selection_weights[node.index] = 0
                parent.__selectable -= 1
                if parent.__selectable <= 0:
                    parent.__update_depth()
                    parent.__update_selection_weights()
            node = parent

    def __update_depth(self):
        explore_depth = None
        for c in self.__valid_choices():
            if c not in self.children:
                explore_depth = 0
                break
            elif explore_depth is None:
                explore_depth = 1 + self.children[c].explore_depth
            else:
                explore_depth = min(
                    explore_depth, 1 + self.children[c].explore_depth)
        self.explore_depth = explore_depth

    def __update_selection_weights(self):
        selection_weights = array('d', self.weights)
        if self.explore_depth == 0:
            for i in hrange(len(selection_weights)):
                if self.choices[i] in self.children:
                    selection_weights[i] = 0
        else:
            target = min(
                self.children[c].explore_depth
                for c in self.__valid_choices()
                if self.children[c].status != NodeStatus.FINISHED)
            for i, c in enumerate(self.choices):
                try:
                    child = self.children[c]
                except KeyError:
                    try:
                        selection_weights[i] = 0
                    except IndexError:
                        break
                    continue
                if child is SENTINEL:
                    continue
                if (
                    child.status == NodeStatus.FINISHED or
                    child.explore_depth > target
                ):
                    selection_weights[i] = 0
        self.__selection_weights = selection_weights
        self.__selectable = len([w for w in self.__selection_weights if w > 0])

    def __check_finished(self):
        for w, c in zip(self.weights, self.choices):
            if w > 0:
                try:
                    if self.children[c].status != NodeStatus.FINISHED:
                        return False
                except KeyError:
                    return False
        self.status = NodeStatus.FINISHED
        return True

    def __weight(self, byte):
        try:
            i = self.choices.index(byte)
        except ValueError:
            return 0
        if i >= len(self.weights):
            return 0
        return self.weights[i]

    def walk(self, byte):
        result = None
        try:
            result = self.children[byte]
        except KeyError:
            try:
                index = self.choices.index(byte)
                if index >= len(self.weights) or self.weights[index] <= 0:
                    result = SENTINEL
            except ValueError:
                result = SENTINEL
            if result is not SENTINEL:
                result = TreeNode(parent=ref(self), index=index)
            self.children[byte] = result
        if result is SENTINEL:
            raise KeyError()
        assert self.choices[result.index] == byte
        return result


SENTINEL = object()


class RunIsComplete(Exception):
    pass


class ConjectureRunner(object):

    def __init__(
        self, test_function, settings=None, random=None,
        database_key=None,
    ):
        self._test_function = test_function
        self.settings = settings or Settings()
        self.last_data = None
        self.changed = 0
        self.shrinks = 0
        self.call_count = 0
        self.event_call_counts = Counter()
        self.valid_examples = 0
        self.start_time = time.time()
        self.random = random or Random(getrandbits(128))
        self.sampler = Sampler(self.random)
        self.database_key = database_key
        self.seen = set()
        self.duplicates = 0
        self.status_runtimes = {}
        self.events_to_strings = WeakKeyDictionary()
        self.tree = TreeNode(index=-1, parent=None)
        self.shrink_mode = False

    def new_buffer(self):
        self.last_data = ConjectureData.for_random(
            max_length=self.settings.buffer_size,
            random=self.random,
        )
        self.test_function(self.last_data)
        self.last_data.freeze()

    def test_function(self, data):
        self.call_count += 1
        try:
            self._test_function(data)
            data.freeze()
        except StopTest as e:
            if e.testcounter != data.testcounter:
                self.save_buffer(data.buffer)
                raise e
        except:
            self.save_buffer(data.buffer)
            raise
        finally:
            data.freeze()
            self.note_details(data)
        if (
            data.status == Status.INTERESTING and (
                self.last_data is None or
                data.buffer != self.last_data.buffer
            )
        ):
            self.debug_data(data)
        if data.status >= Status.VALID:
            self.valid_examples += 1

    def consider_new_test_data(self, data):
        # Transition rules:
        #   1. Transition cannot decrease the status
        #   2. Any transition which increases the status is valid
        #   3. If the previous status was interesting, only shrinking
        #      transitions are allowed.
        key = hbytes(data.buffer)
        if key in self.seen:
            self.duplicates += 1
            return False
        self.seen.add(key)
        if data.buffer == self.last_data.buffer:
            return False
        if self.last_data.status < data.status:
            return True
        if self.last_data.status > data.status:
            return False
        if data.status == Status.INVALID:
            return data.index >= self.last_data.index
        if data.status == Status.OVERRUN:
            return data.overdraw <= self.last_data.overdraw
        if data.status == Status.INTERESTING:
            assert len(data.buffer) <= len(self.last_data.buffer)
            if len(data.buffer) == len(self.last_data.buffer):
                assert data.buffer < self.last_data.buffer
            return True
        return True

    def save_buffer(self, buffer):
        if (
            self.settings.database is not None and
            self.database_key is not None and
            Phase.reuse in self.settings.phases
        ):
            self.settings.database.save(
                self.database_key, hbytes(buffer)
            )

    def note_details(self, data):
        if data.status == Status.INTERESTING:
            self.save_buffer(data.buffer)
        runtime = max(data.finish_time - data.start_time, 0.0)
        self.status_runtimes.setdefault(data.status, []).append(runtime)
        for event in set(map(self.event_to_string, data.events)):
            self.event_call_counts[event] += 1
        if data.buffer:
            tree = self.tree

            # Sometimes e.g. when shrinking we take a path that leads off the
            # tree. In that case we just stop early and only explore until we
            # got to that point.
            completed = data.status != Status.OVERRUN
            for ws, cs, b in zip(data.weights, data.choices, data.buffer):
                tree.explore(ws, cs)
                try:
                    tree = tree.walk(b)
                except KeyError:
                    completed = False
                    break

            if tree.status != NodeStatus.FINISHED:
                if completed:
                    assert data.buffer == tree.path
                    tree.explore((), ())

                if not self.shrink_mode:
                    tree.update_ancestors()

    def debug(self, message):
        with self.settings:
            debug_report(message)

    def debug_data(self, data):
        self.debug(u'%d bytes %s -> %s, %s' % (
            data.index,
            unicode_safe_repr(list(data.buffer[:data.index])),
            unicode_safe_repr(data.status),
            data.output,
        ))

    def __prescreen_buffer(self, buffer):
        tree = self.tree
        for b in buffer:
            if tree.status == NodeStatus.UNEXPLORED:
                return True
            if tree.status == NodeStatus.FINISHED:
                return False
            try:
                tree = tree.walk(b)
            except KeyError:
                return False
        return tree.status == NodeStatus.UNEXPLORED

    def incorporate_new_buffer(self, buffer):
        if buffer in self.seen:
            return False
        if not self.__prescreen_buffer(buffer):
            return False
        assert self.last_data.status == Status.INTERESTING
        if (
            self.settings.timeout > 0 and
            time.time() >= self.start_time + self.settings.timeout
        ):
            self.exit_reason = ExitReason.timeout
            raise RunIsComplete()
        buffer = buffer[:self.last_data.index]
        if sort_key(buffer) >= sort_key(self.last_data.buffer):
            return False
        assert sort_key(buffer) <= sort_key(self.last_data.buffer)
        data = ConjectureData.for_buffer(buffer)
        self.test_function(data)
        if self.consider_new_test_data(data):
            self.shrinks += 1
            self.last_data = data
            if self.shrinks >= self.settings.max_shrinks:
                self.exit_reason = ExitReason.max_shrinks
                raise RunIsComplete()
            self.last_data = data
            self.changed += 1
            return True
        return False

    def run(self):
        with self.settings:
            try:
                self._run()
            except RunIsComplete:
                pass
            self.debug(
                u'Run complete after %d examples (%d valid) and %d shrinks' % (
                    self.call_count, self.valid_examples, self.shrinks,
                ))

    def __retry_previous_examples(self):
        if (
            self.settings.database is not None and
            self.database_key is not None
        ):
            corpus = sorted(
                self.settings.database.fetch(self.database_key),
                key=lambda d: (len(d), d)
            )
            for existing in corpus:
                if self.valid_examples >= self.settings.max_examples:
                    self.exit_reason = ExitReason.max_examples
                    return
                if self.call_count >= max(
                    self.settings.max_iterations, self.settings.max_examples
                ):
                    self.exit_reason = ExitReason.max_iterations
                    return
                data = ConjectureData.for_buffer(existing)
                self.test_function(data)
                data.freeze()
                self.last_data = data
                if data.status < Status.VALID:
                    self.settings.database.delete(
                        self.database_key, existing)
                elif data.status == Status.VALID:
                    # Incremental garbage collection! we store a lot of
                    # examples in the DB as we shrink: Those that stay
                    # interesting get kept, those that become invalid get
                    # dropped, but those that are merely valid gradually go
                    # away over time.
                    if self.random.randint(0, 2) == 0:
                        self.settings.database.delete(
                            self.database_key, existing)
                else:
                    assert data.status == Status.INTERESTING
                    self.last_data = data
                    break

    def __generate_new_examples(self):
        if Phase.generate in self.settings.phases:
            if (
                self.last_data is None or
                self.last_data.status < Status.INTERESTING
            ):
                self.new_buffer()
            self.shrink_mode = False

            while self.last_data.status != Status.INTERESTING:
                if self.valid_examples >= self.settings.max_examples:
                    self.exit_reason = ExitReason.max_examples
                    return
                if self.call_count >= max(
                    self.settings.max_iterations, self.settings.max_examples
                ):
                    self.exit_reason = ExitReason.max_iterations
                    return
                if (
                    self.settings.timeout > 0 and
                    time.time() >= self.start_time + self.settings.timeout
                ):
                    self.exit_reason = ExitReason.timeout
                    return

                node = [self.tree]

                def draw_byte(data, weights, choices):
                    node[0].explore(weights, choices)
                    result = choices[
                        self.sampler.sample(node[0].selection_weights)]
                    node[0] = node[0].walk(result)
                    return result

                data = ConjectureData(
                    max_length=self.settings.buffer_size,
                    draw_byte=draw_byte,
                )
                self.test_function(data)
                data.freeze()
                if self.consider_new_test_data(data):
                    self.last_data = data

    def _run(self):
        self.last_data = None
        self.start_time = time.time()

        self.__retry_previous_examples()
        self.__generate_new_examples()
        data = self.last_data
        if data is None:
            self.exit_reason = ExitReason.finished
            return
        assert isinstance(data.output, text_type)

        if self.settings.max_shrinks <= 0:
            self.exit_reason = ExitReason.max_shrinks
            return

        if Phase.shrink not in self.settings.phases:
            self.exit_reason = ExitReason.finished
            return

        if not self.last_data.buffer:
            self.exit_reason = ExitReason.finished
            return

        data = ConjectureData.for_buffer(self.last_data.buffer)
        self.test_function(data)
        if data.status != Status.INTERESTING:
            self.exit_reason = ExitReason.flaky
            return

        self.__shrink_best_example()

    def __shrink_best_example(self):
        self.shrink_mode = True

        change_counter = -1

        while self.changed > change_counter:
            change_counter = self.changed

            self.debug('Random interval deletes')
            failed_deletes = 0
            while self.last_data.intervals and failed_deletes < 10:
                if self.random.randint(0, 1):
                    u, v = self.random.choice(self.last_data.intervals)
                else:
                    n = len(self.last_data.buffer) - 1
                    u, v = sorted((
                        self.random.choice(self.last_data.intervals)
                    ))
                if (
                    v < len(self.last_data.buffer)
                ) and self.incorporate_new_buffer(
                    self.last_data.buffer[:u] +
                    self.last_data.buffer[v:]
                ):
                    failed_deletes = 0
                else:
                    failed_deletes += 1

            self.debug('Structured interval deletes')
            i = 0
            while i < len(self.last_data.intervals):
                u, v = self.last_data.intervals[i]
                if not self.incorporate_new_buffer(
                    self.last_data.buffer[:u] +
                    self.last_data.buffer[v:]
                ):
                    i += 1

            if change_counter != self.changed:
                self.debug('Restarting')
                continue

            self.debug('Bulk replacing blocks with simpler blocks')
            i = 0
            while i < len(self.last_data.blocks):
                u, v = self.last_data.blocks[i]
                buf = self.last_data.buffer
                block = buf[u:v]
                n = v - u

                buffer = bytearray()
                for r, s in self.last_data.blocks:
                    if s - r == n and self.last_data.buffer[r:s] > block:
                        buffer.extend(block)
                    else:
                        buffer.extend(self.last_data.buffer[r:s])
                self.incorporate_new_buffer(hbytes(buffer))
                i += 1

            self.debug('Replacing individual blocks with simpler blocks')
            i = 0
            while i < len(self.last_data.blocks):
                u, v = self.last_data.blocks[i]
                buf = self.last_data.buffer
                block = buf[u:v]
                n = v - u
                all_blocks = sorted(set([bytes(n)] + [
                    buf[a:a + n]
                    for a in self.last_data.block_starts[n]
                ]))
                better_blocks = all_blocks[:all_blocks.index(block)]
                for b in better_blocks:
                    if self.incorporate_new_buffer(
                        buf[:u] + b + buf[v:]
                    ):
                        break
                i += 1

            self.debug('Simultaneous shrinking of duplicated blocks')
            block_counter = -1
            while block_counter < self.changed:
                block_counter = self.changed
                blocks = [
                    k for k, count in
                    Counter(
                        self.last_data.buffer[u:v]
                        for u, v in self.last_data.blocks).items()
                    if count > 1
                ]
                for block in blocks:
                    parts = [
                        self.last_data.buffer[r:s]
                        for r, s in self.last_data.blocks
                    ]

                    def replace(b):
                        return b''.join(
                            bytes(b if c == block else c) for c in parts
                        )
                    minimize(
                        block,
                        lambda b: self.incorporate_new_buffer(replace(b)),
                        self.random
                    )

            if change_counter != self.changed:
                self.debug('Restarting')
                continue

            self.debug('Lexicographical minimization of whole buffer')
            minimize(
                self.last_data.buffer, self.incorporate_new_buffer,
                cautious=True
            )

            if change_counter != self.changed:
                self.debug('Restarting')
                continue

            self.debug('Shrinking of individual blocks')
            i = 0
            while i < len(self.last_data.blocks):
                u, v = self.last_data.blocks[i]
                minimize(
                    self.last_data.buffer[u:v],
                    lambda b: self.incorporate_new_buffer(
                        self.last_data.buffer[:u] + b +
                        self.last_data.buffer[v:],
                    ), self.random
                )
                i += 1

            self.debug('Replacing intervals with simpler intervals')

            interval_counter = -1
            while interval_counter != self.changed:
                interval_counter = self.changed
                i = 0
                alternatives = None
                while i < len(self.last_data.intervals):
                    if alternatives is None:
                        alternatives = sorted(set(
                            self.last_data.buffer[u:v]
                            for u, v in self.last_data.intervals), key=len)
                    u, v = self.last_data.intervals[i]
                    for a in alternatives:
                        buf = self.last_data.buffer
                        if (
                            len(a) < v - u or
                            (len(a) == (v - u) and a < buf[u:v])
                        ):
                            if self.incorporate_new_buffer(
                                buf[:u] + a + buf[v:]
                            ):
                                alternatives = None
                                break
                    i += 1

            if change_counter != self.changed:
                self.debug('Restarting')
                continue

            self.debug('Shuffling suffixes while shrinking %r' % (
                self.last_data.bind_points,
            ))
            b = 0
            while b < len(self.last_data.bind_points):
                cutoff = sorted(self.last_data.bind_points)[b]

                def test_value(prefix):
                    if self.incorporate_new_buffer(
                        prefix +
                        hbytes(reversed(self.last_data.buffer[len(prefix):]))
                    ):
                        return True
                    for t in hrange(5):
                        alphabet = {}
                        for i, j in self.last_data.blocks[b:]:
                            alphabet.setdefault(j - i, []).append((i, j))
                        if t > 0:
                            for v in alphabet.values():
                                self.random.shuffle(v)
                        buf = bytearray(prefix)
                        for i, j in self.last_data.blocks[b:]:
                            u, v = alphabet[j - i].pop()
                            buf.extend(self.last_data.buffer[u:v])
                        if self.incorporate_new_buffer(hbytes(buf)):
                            return True
                    return False
                minimize(
                    self.last_data.buffer[:cutoff], test_value, cautious=True,
                    random=self.random,
                )
                b += 1

        self.exit_reason = ExitReason.finished

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


def sort_key(buffer):
    return (len(buffer), buffer)
