"""
This script exists to populate the file src/hypothesis/internal/conjecture/substitutions.py
"""

from collections import defaultdict, deque
from  hypothesis.internal.conjecture.shrinker import sort_key, FIXERS
import sys
import os
from hypothesis.internal.conjecture.engine import ConjectureRunner, BUFFER_SIZE
from hypothesis.internal.conjecture.data import Status
from random import Random
from hypothesis import settings, strategies as st, Verbosity
import itertools
from hypothesis.internal.conjecture.dfa import ConcreteDFA, Indexer, INF
from hypothesis.internal.conjecture.lstar import LStar
from hypothesis.internal.conjecture.junkdrawer import uniform
from hypothesis.vendor.pretty import RepresentationPrinter
import heapq


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if True:
    sys.path.append(ROOT)
    from tests.quality.test_shrink_normalization import STRATEGIES_TO_NORMALIZE


def repair(test_function):
    runner = ConjectureRunner(
        test_function,
        settings=settings(database=None, max_examples=10 ** 4, report_multiple_bugs=True),
        random=Random(0),
        apply_limits=False,
    )

    failures = 0
    while failures < 100:
        start = runner.cached_test_function(uniform(random, BUFFER_SIZE // 4) + bytes(BUFFER_SIZE))
        if start.status != Status.INTERESTING:
            continue

        def is_good(d):
            return d.status == Status.INTERESTING and d.interesting_origin == start.interesting_origin

        end = runner.shrink(start, is_good)

        achieved = end.buffer
        goal = runner.interesting_examples[start.interesting_origin].buffer

        if achieved == goal:
            failures += 1
            continue
        failures = 0

        changed = True

        assert not achieved.startswith(goal)
        assert sort_key(goal) < sort_key(achieved)

        u = 0
        while achieved[u] == goal[u]:
            u += 1

        prefix = achieved[:u]

        for v in range(u + 1, len(achieved) + 1):
            suffix = achieved[v:]
            fixed = False

            original = achieved[u:v]

            def can_replace(s):
                if sort_key(s) > sort_key(original):
                    return False
                return is_good(runner.cached_test_function(prefix + s + suffix)) 

            for v2 in range(u, min(v, len(goal)) + 1):
                replacement = goal[u:v2]
                if can_replace(replacement):
                    assert replacement[-1] != original[-1]
                    fixed = True

                    learner = LStar(can_replace)

                    prev = -1
                    while learner.generation != prev:
                        prev = learner.generation

                        learner.repair(replacement)
                        learner.repair(original)

                        index = Indexer(learner.dfa)
                        learner.repair(index[0])
                        j = index.index(original)
                        if j + 1 < index.length:
                            learner.repair(index[j + 1])

                    assert Indexer(learner.dfa).length < INF
                    dfa = learner.dfa.to_concrete()

                    print(f"Learned to replace {original} with {replacement}")

                    FIXERS.append(dfa)

                    with open(os.path.join(ROOT, "src", "hypothesis", "internal", "conjecture", "fixers.py"), "a") as o:
                        printer = RepresentationPrinter(o)
                        printer.break_()
                        printer.text("FIXERS.append(")
                        with printer.indent(4):
                            printer.break_()
                            printer.pretty(dfa)
                        printer.break_()
                        printer.text(")")
                        printer.break_()
                    break
            if fixed:
                break


def minimal_values_of(strategy):
    values = {}

    def test_function(data):
        v = data.draw(strategy)
        buf = bytes(data.buffer)
        values[buf] = v

    runner = ConjectureRunner(
        test_function,
        settings=settings(database=None, max_examples=10 ** 4, report_multiple_bugs=True),
        random=Random(0),
        apply_limits=False
    )

    def predicate(s):
        data = runner.cached_test_function(s)
        return data.status >= Status.VALID and data.buffer == s

    learner = LStar(predicate)

    def fix(s):
        s = s + bytes(BUFFER_SIZE)
        learner.repair(s)
        data = runner.cached_test_function(s)
        if data.status >= Status.VALID:
            learner.repair(data.buffer)

    fix(bytes(BUFFER_SIZE))

    prev = -1
    while prev != learner.generation:
        prev = learner.generation

        for _ in range(10):
            fix(uniform(random, 10))

    yielded = set()

    while True:
        for s in learner.dfa:
            if not predicate(s):
                prev = learner.generation
                fix(s)
                assert learner.generation > prev
                break
            v = values[s]
            rep = repr(v)
            if rep in yielded:
                continue
            yielded.add(rep)
            yield v
        else:
            break



def repair_strategy(strategy):
    avoid = []

    for v in minimal_values_of(strategy):
        avoid.append(v)
        print("Learning to avoid", avoid)

        def test_function(data):
            if data.draw(strategy) not in avoid:
                data.mark_interesting()

        repair(test_function)
        if len(avoid) >= 50:
            break
        
if __name__ == '__main__':
    random = Random(0)

    for strategy in STRATEGIES_TO_NORMALIZE:
        print("Repairing", strategy)

        repair_strategy(strategy)
