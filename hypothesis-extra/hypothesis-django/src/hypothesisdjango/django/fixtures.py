# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import weakref
from random import Random

from django.db import transaction
from hypothesis.core import best_satisfying_template
from hypothesis.errors import UnsatisfiedAssumption
from django.test.runner import setup_databases
from hypothesis.settings import Settings

ALL_FIXTURES = []


def active_fixtures():
    for f in ALL_FIXTURES:
        t = f()
        if t is not None:
            yield t


class Fixture(object):

    def __init__(self, strategy, constraint=None, execute=None, settings=None):
        self.strategy = strategy
        self.constraint = constraint
        self.settings = settings or Settings(
            max_examples=10000,
            max_iterations=10000,
            max_shrinks=5000,
        )
        self.constraint = constraint or (lambda x: True)
        self.execute = execute or (lambda f: f())
        self._set_template()
        ALL_FIXTURES.append(weakref.ref(self))

    def template_condition(self, template):
        def run():
            try:
                with transaction.atomic():
                    for f in active_fixtures():
                        assert f is not self
                        if f.template == template:
                            return False
                        f()
                    result = self.constraint(self.strategy.reify(template))
                    transaction.set_rollback(True)
                return result
            except UnsatisfiedAssumption:
                return False

        return self.execute(run)

    def _set_template(self):
        verbosity = 0
        old_config = setup_databases(
            verbosity=verbosity, interactive=False
        )
        try:
            if self.settings.database:
                storage = self.settings.database.storage('django.fixtures')
            else:
                storage = None

            self.template = best_satisfying_template(
                search_strategy=self.strategy,
                random=Random(),
                condition=self.template_condition,
                settings=self.settings,
                storage=storage,
                max_parameter_tries=1
            )
        finally:
            old_names, mirrors = old_config
            for connection, old_name, destroy in old_names:
                if destroy:
                    connection.creation.destroy_test_db(
                        old_name, verbosity, False)

    def __call__(self):
        return self.strategy.reify(self.template)


def fixture(strategy, constraint=None, execute=None):
    return Fixture(strategy, constraint, execute)
