# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import uuid

import pytest
from fakeredis import FakeRedis

from hypothesis import strategies as st
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.errors import InvalidArgument
from hypothesis.extra.redis import RedisExampleDatabase
from hypothesis.stateful import Bundle, RuleBasedStateMachine, rule


@pytest.mark.parametrize(
    "kw",
    [
        {"redis": "not a redis instance"},
        {"redis": FakeRedis(), "expire_after": 10},  # not a timedelta
        {"redis": FakeRedis(), "key_prefix": "not a bytestring"},
    ],
)
def test_invalid_args_raise(kw):
    with pytest.raises(InvalidArgument):
        RedisExampleDatabase(**kw)


def test_all_methods():
    db = RedisExampleDatabase(FakeRedis())
    db.save(b"key1", b"value")
    assert list(db.fetch(b"key1")) == [b"value"]
    db.move(b"key1", b"key2", b"value")
    assert list(db.fetch(b"key1")) == []
    assert list(db.fetch(b"key2")) == [b"value"]
    db.delete(b"key2", b"value")
    assert list(db.fetch(b"key2")) == []
    db.delete(b"key2", b"unknown value")


class DatabaseComparison(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        server = FakeRedis(host=uuid.uuid4().hex)  # Different (fake) server each time
        self.dbs = [InMemoryExampleDatabase(), RedisExampleDatabase(server)]

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


TestDBs = DatabaseComparison.TestCase
