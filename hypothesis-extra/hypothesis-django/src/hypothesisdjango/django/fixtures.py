from __future__ import division, print_function, absolute_import, \
    unicode_literals

from django.db import transaction
from django.test.runner import setup_databases
from random import Random

from hypothesis.core import best_satisfying_template
from hypothesis.settings import Settings
from hypothesis.errors import UnsatisfiedAssumption


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

    def template_condition(self, template):
        def run():
            try:
                with transaction.atomic():
                    result = self.constraint(self.strategy.reify(template))
                    transaction.set_rollback(True)
                return result
            except UnsatisfiedAssumption:
                return False

        return self.execute(run)

    def _set_template(self):
        verbosity = 1
        old_config = setup_databases(
            verbosity=verbosity, interactive=False
        )
        try:
            if self.settings.database:
                storage = self.settings.database.storage("django.fixtures")
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
