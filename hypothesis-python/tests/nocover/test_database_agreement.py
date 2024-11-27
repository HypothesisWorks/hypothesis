# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import os
import shutil
import tempfile

from hypothesis import strategies as st
from hypothesis.database import (
    BackgroundWriteDatabase,
    DirectoryBasedExampleDatabase,
    InMemoryExampleDatabase,
)
from hypothesis.stateful import Bundle, RuleBasedStateMachine, rule


class DatabaseComparison(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.tempd = tempfile.mkdtemp()
        exampledir = os.path.join(self.tempd, "examples")

        self.dbs = [
            DirectoryBasedExampleDatabase(exampledir),
            InMemoryExampleDatabase(),
            DirectoryBasedExampleDatabase(exampledir),
            BackgroundWriteDatabase(InMemoryExampleDatabase()),
        ]

    keys = Bundle("keys")
    values = Bundle("values")

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

    @rule(k1=keys, k2=keys, v=values)
    def move(self, k1, k2, v):
        for db in self.dbs:
            db.move(k1, k2, v)

    @rule(k=keys)
    def values_agree(self, k):
        last = None
        last_db = None
        for db in self.dbs:
            keys = set(db.fetch(k))
            if last is not None:
                assert last == keys, (last_db, db)
            last = keys
            last_db = db

    def teardown(self):
        shutil.rmtree(self.tempd)


TestDBs = DatabaseComparison.TestCase
