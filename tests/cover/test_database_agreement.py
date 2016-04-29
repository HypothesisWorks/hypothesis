# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

import os
import shutil
import tempfile

import hypothesis.strategies as st
from hypothesis.database import SQLiteExampleDatabase, \
    InMemoryExampleDatabase, DirectoryBasedExampleDatabase
from hypothesis.stateful import rule, Bundle, RuleBasedStateMachine


class DatabaseComparison(RuleBasedStateMachine):

    def __init__(self):
        super(DatabaseComparison, self).__init__()
        self.tempd = tempfile.mkdtemp()
        exampledir = os.path.join(self.tempd, 'examples')

        self.dbs = [
            DirectoryBasedExampleDatabase(exampledir),
            InMemoryExampleDatabase(), SQLiteExampleDatabase(':memory:'),
            DirectoryBasedExampleDatabase(exampledir),
        ]

    keys = Bundle('keys')
    values = Bundle('values')

    @rule(target=keys, k=st.binary())
    def k(self, k):
        return k

    @rule(target=values, v=st.binary())
    def v(self, v):
        return v

    @rule(k=keys, v=values)
    def save(self, k, v):
        for db in self.dbs:
            db.save(k, v)

    @rule(k=keys, v=values)
    def delete(self, k, v):
        for db in self.dbs:
            db.delete(k, v)

    @rule(k=keys)
    def values_agree(self, k):
        last = None
        for db in self.dbs:
            keys = set(db.fetch(k))
            if last is not None:
                assert last == keys
            last = keys

    def teardown(self):
        for d in self.dbs:
            d.close()
        shutil.rmtree(self.tempd)

TestDBs = DatabaseComparison.TestCase
