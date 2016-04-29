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

import base64
from collections import namedtuple

import hypothesis.strategies as s
from hypothesis import settings
from hypothesis.database import SQLiteExampleDatabase
from hypothesis.stateful import GenericStateMachine
from hypothesis.tools.mergedbs import merge_dbs

FORK_NOW = u'fork'
Insert = namedtuple(u'Insert', (u'key', u'value', u'target'))
Delete = namedtuple(u'Delete', (u'key', u'value', u'target'))


class BackendForTesting(SQLiteExampleDatabase):

    def __init__(self):
        super(BackendForTesting, self).__init__()
        self.create_db_if_needed()
        self.mirror = set()

    def save(self, key, value):
        super(BackendForTesting, self).save(key, value)
        self.mirror.add((key, value))

    def delete(self, key, value):
        super(BackendForTesting, self).delete(key, value)
        try:
            self.mirror.remove((key, value))
        except KeyError:
            pass

    def refresh_mirror(self):
        self.mirror = set()
        with self.cursor() as cursor:
            cursor.execute("""
                select key, value
                from hypothesis_data_mapping
            """)
            for r in cursor:
                self.mirror.add(tuple(map(base64.b64decode, r)))


class DatabaseMergingState(GenericStateMachine):

    def __init__(self):
        super(DatabaseMergingState, self).__init__()
        self.forked = False
        self.original = BackendForTesting()
        self.left = BackendForTesting()
        self.right = BackendForTesting()
        self.seen_strings = set()

    def values(self):
        base = s.binary()
        if self.seen_strings:
            return s.sampled_from(sorted(self.seen_strings)) | base
        else:
            return base

    def steps(self):
        values = self.values()
        if not self.forked:
            return (
                s.just(FORK_NOW) |
                s.builds(Insert, values, values, s.none()) |
                s.builds(Delete, values, values, s.none())
            )
        else:
            targets = s.sampled_from((self.left, self.right))
            return (
                s.builds(Insert, values, values, targets) |
                s.builds(Delete, values, values, targets)
            )

    def execute_step(self, step):
        if step == FORK_NOW:
            self.forked = True
        else:
            assert isinstance(step, (Insert, Delete))
            self.seen_strings.add(step.key)
            self.seen_strings.add(step.value)
            if self.forked:
                targets = (step.target,)
            else:
                targets = (self.original, self.left, self.right)
            for target in targets:
                if isinstance(step, Insert):
                    target.save(step.key, step.value)
                else:
                    assert isinstance(step, Delete)
                    target.delete(step.key, step.value)

    def teardown(self):
        target_mirror = (self.left.mirror | self.right.mirror) - (
            (self.original.mirror - self.left.mirror) |
            (self.original.mirror - self.right.mirror)
        )

        n_inserts = len(
            self.right.mirror - self.left.mirror - self.original.mirror)
        n_deletes = len(
            (self.original.mirror - self.right.mirror) & self.left.mirror)

        result = merge_dbs(
            self.original.connection(),
            self.left.connection(),
            self.right.connection()
        )
        assert result.inserts == n_inserts
        assert result.deletes == n_deletes
        self.left.refresh_mirror()
        self.original.close()
        self.left.close()
        self.right.close()
        assert self.left.mirror == target_mirror


TestMerging = DatabaseMergingState.TestCase
TestMerging.settings = settings(
    TestMerging.settings, timeout=60)
