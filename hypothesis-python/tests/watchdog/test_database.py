# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import sys
import time
from collections import Counter

from hypothesis import Phase, settings
from hypothesis.database import (
    DirectoryBasedExampleDatabase,
    InMemoryExampleDatabase,
    MultiplexedDatabase,
)

from tests.cover.test_database_backend import _database_conforms_to_listener_api

# we need real time here, not monkeypatched for CI
time_sleep = time.sleep


def test_database_listener_directory():
    # this test is very expensive because we wait between every rule for the
    # filesystem observer to fire. Limit examples/step count as much as possible.
    _database_conforms_to_listener_api(
        lambda path: DirectoryBasedExampleDatabase(path),
        flush=lambda _db: time_sleep(0.2),
        supports_value_delete=False,
        # expensive flush makes shrinking take forever
        parent_settings=settings(
            max_examples=5, stateful_step_count=10, phases=set(Phase) - {Phase.shrink}
        ),
    )


def test_database_listener_multiplexed(tmp_path):
    db = MultiplexedDatabase(
        InMemoryExampleDatabase(), DirectoryBasedExampleDatabase(tmp_path)
    )
    events = []

    def listener(event):
        events.append(event)

    db.add_listener(listener)

    db.save(b"a", b"a")
    time_sleep(0.2)
    assert events == [("save", (b"a", b"a"))] * 2

    db.remove_listener(listener)
    db.delete(b"a", b"a")
    db.save(b"a", b"b")
    time_sleep(0.2)
    assert events == [("save", (b"a", b"a"))] * 2

    db.add_listener(listener)
    db.delete(b"a", b"b")
    db.save(b"a", b"c")
    time_sleep(0.2)
    # InMemory database fires immediately, while DirectoryBased has to
    # wait for filesystem listeners. Therefore the events can arrive out of
    # order. Test a weaker multiset property, disregarding ordering.
    assert Counter(events[2:]) == {
        # InMemory
        ("delete", (b"a", b"b")): 1,
        # DirectoryBased
        ("delete", (b"a", None)): 1,
        # both
        ("save", (b"a", b"c")): 2,
    }


def test_database_listener_directory_explicit(tmp_path):
    db = DirectoryBasedExampleDatabase(tmp_path)
    events = []

    def listener(event):
        events.append(event)

    db.add_listener(listener)

    db.save(b"k1", b"v1")
    time_sleep(0.2)
    assert events == [("save", (b"k1", b"v1"))]

    db.remove_listener(listener)
    db.delete(b"k1", b"v1")
    db.save(b"k1", b"v2")
    time_sleep(0.2)
    assert events == [("save", (b"k1", b"v1"))]

    db.add_listener(listener)
    db.delete(b"k1", b"v2")
    db.save(b"k1", b"v3")
    time_sleep(0.2)
    assert events[1:] == [
        ("delete", (b"k1", None)),
        ("save", (b"k1", b"v3")),
    ]

    # moving into a nonexistent key
    db.move(b"k1", b"k2", b"v3")
    time_sleep(0.2)
    # moving back into an existing key
    db.move(b"k2", b"k1", b"v3")
    time_sleep(0.2)

    if sys.platform.startswith("darwin"):
        expected = [
            ("delete", (b"k1", b"v3")),
            ("save", (b"k2", b"v3")),
            ("delete", (b"k2", b"v3")),
            ("save", (b"k1", b"v3")),
        ]
    elif sys.platform.startswith("win"):
        # windows fires a save/delete event for our particular moves
        # at the os-level instead of a move (or watchdog just isn't picking
        # up on it correctly on windows). This means we don't get the exact
        # deleted values for us to broadcast.
        expected = [
            ("delete", (b"k1", None)),
            ("save", (b"k2", b"v3")),
            ("delete", (b"k2", None)),
            ("save", (b"k1", b"v3")),
        ]
    elif sys.platform.startswith("linux"):
        expected = [
            # as far as I can tell, linux fires both a save and a move event
            # for the first move event. I don't know if this is our bug or an os
            # implementation detail. I am leaning towards the latter, since other
            # os' are fine.
            ("save", (b"k2", b"v3")),
            # first move event is normal...
            ("delete", (b"k1", b"v3")),
            ("save", (b"k2", b"v3")),
            # ...but the second move event gets picked up by watchdog as an individual
            # save/delete, not a move. I'm not sure why. Therefore we don't have
            # the delete value present; and the ordering is also different from
            # normal.
            ("save", (b"k1", b"v3")),
            ("delete", (b"k2", None)),
        ]
    else:
        raise NotImplementedError(f"unknown platform {sys.platform}")

    assert events[3:] == expected, str(events[3:])
