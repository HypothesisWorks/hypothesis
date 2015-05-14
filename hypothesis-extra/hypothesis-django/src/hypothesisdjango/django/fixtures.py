from __future__ import division, print_function, absolute_import, \
    unicode_literals

import time
import pytest
from random import Random

from hypothesis.core import simplify_template_such_that
from hypothesis.settings import Settings, Verbosity
from hypothesis.internal.tracker import Tracker
from hypothesis.errors import UnsatisfiedAssumption
from hypothesis.internal.compat import hrange


class Fixture(object):

    def __init__(self, strategy, constraint=None, execute=None):
        self.strategy = strategy
        self.constraint = constraint
        self.settings = Settings(
            max_examples=10000,
            max_iterations=10000,
            max_shrinks=5000,
        )
        self.constraint = constraint or (lambda x: True)
        self.execute = execute or (lambda f: f())

    def template_condition(self, template):
        def run():
            try:
                result = self.strategy.reify(template)
                return self.constraint(result)
            except UnsatisfiedAssumption:
                return False

        return self.execute(run)

    def __call__(self):
        if not hasattr(self, 'template'):
            tracker = Tracker()
            random = Random()

            found = False
            rounds_since_shrink = 0
            for _ in hrange(1000):
                template = self.strategy.draw_and_produce(random)
                if tracker.track(template) > 1:
                    continue
                if self.template_condition(template):
                    if not found:
                        best = template
                        found = True
                    elif self.strategy.strictly_simpler(template, best):
                        best = template
                        rounds_since_shrink = 0
                    else:
                        rounds_since_shrink += 1
                        if rounds_since_shrink >= 5:
                            break

            for template in simplify_template_such_that(
                self.strategy, random, best, self.template_condition,
                tracker, self.settings, time.time()
            ):
                self.template = template
        result = self.strategy.reify(self.template)
        return result


def fixture(strategy, constraint=None, execute=None):
    f = Fixture(strategy, constraint, execute)

    @pytest.fixture
    def run_fixture():
        return f()
    return run_fixture
