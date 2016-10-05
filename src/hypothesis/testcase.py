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

from hypothesis.internal.detection import is_hypothesis_test
from hypothesis.reporting import with_reporter


class HypothesisTestCase(object):
    def run(self, report=None):
        if is_hypothesis_test(getattr(self, self._testMethodName)):
            self.__hypothesis_notes = []

            setup_methods = getattr(
                self, 'hypothesis_setup_methods', ['setUp'])
            teardown_methods = getattr(
                self, 'hypothesis_teardown_methods', ['tearDown'])

            try:
                old_setups = [getattr(self, s) for s in setup_methods]
                old_teardowns = [getattr(self, s) for s in teardown_methods]
                for  s in setup_methods + teardown_methods: 
                    setattr(self, s, lambda: None)

                def setup_example():
                    for s in old_setups:
                        s()

                def teardown_example(example):
                    ex = None
                    for s in old_teardowns:
                        try:
                            s()
                        except ex:
                            pass
                    if ex is not None:
                        raise ex
                self.setup_example = setup_example
                self.teardown_example = teardown_example

                reporter = getattr(
                    self, 'hypothesis_reporter',
                    lambda n: self.__hypothesis_notes.append(str(n))
                )

                with with_reporter(reporter):
                    return super(HypothesisTestCase, self).run(report)
            finally:
                for name, method in zip(
                    setup_methods + teardown_methods,
                    old_setups + old_teardowns,
                ):
                    setattr(self, name, method)
        else:
            return super(HypothesisTestCase, self).run(report)

    def shortDescription(self):
        base = super(HypothesisTestCase, self).shortDescription()
        if self.__hypothesis_notes:
            if base:
                if base[-1] != '\n':
                    base += '\n'
            else:
                base = ''
            base += '\n'
            base += (
                '\n'.join(self.__hypothesis_notes)
            )
            base += '\n'
        return base
