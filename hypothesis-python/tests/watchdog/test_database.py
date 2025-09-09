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

import pytest

from hypothesis import Phase, settings
from hypothesis.database import (
    DirectoryBasedExampleDatabase,
    InMemoryExampleDatabase,
    MultiplexedDatabase,
)
from hypothesis.internal.compat import WINDOWS

from tests.common.utils import flaky, skipif_threading, wait_for
from tests.cover.test_database_backend import _database_conforms_to_listener_api

# e.g.
# * FAILED hypothesis-python/tests/watchdog/test_database.py::
#   test_database_listener_multiplexed -
#   Exception: timing out after waiting 60s for condition lambda: events ==
#   [("save", (b"a", b"a"))] * 2
# * FAILED hypothesis-python/tests/watchdog/test_database.py::
#   test_still_listens_if_directory_did_not_exist -
#   Exception: timing out after waiting 60s for condition lambda: len(events) == 1
#
# It seems possible the failures are correlated on windows (ie if one db test fails,
# another is more likely to). I suspect a watchdog or windows issue: possibly a
# change handler is not being registered by watchdog correctly, or is registered
# too late, or... . A timeout of 60 not firing means it's unlikely "the machine is
# slow and takes a while to fire the event" is the problem here.
#
# It seems watchdog CI also has a similar problem:
# * https://github.com/gorakhargosh/watchdog/pull/581#issuecomment-548257915
# * cmd+f `def rerun_filter` in the watchdog repository
pytestmark = pytest.mark.skipif(
    WINDOWS, reason="watchdog tests are too flaky on windows"
)

OSX = sys.platform == "darwin"


# we need real time here, not monkeypatched for CI
time_sleep = time.sleep


def test_database_listener_directory():
    _database_conforms_to_listener_api(
        lambda path: DirectoryBasedExampleDatabase(path),
        supports_value_delete=False,
        parent_settings=settings(
            # this test is very expensive because we wait between every rule for
            # the filesystem observer to fire.
            max_examples=5,
            stateful_step_count=10,
            # expensive runtime makes shrinking take forever
            phases=set(Phase) - {Phase.shrink},
        ),
    )


# seen flaky on test-win; we get *three* of the same save events in the first
# assertion, which...is baffling, and possibly a genuine bug (most likely in
# watchdog).
@skipif_threading  # add_listener is not thread safe because watchdog is not
@pytest.mark.skipif(OSX, reason="times out consistently on osx")
def test_database_listener_multiplexed(tmp_path):
    db = MultiplexedDatabase(
        InMemoryExampleDatabase(), DirectoryBasedExampleDatabase(tmp_path)
    )
    events = []

    def listener(event):
        events.append(event)

    db.add_listener(listener)

    db.save(b"a", b"a")
    wait_for(lambda: events == [("save", (b"a", b"a"))] * 2, timeout=60)

    db.remove_listener(listener)
    db.delete(b"a", b"a")
    db.save(b"a", b"b")
    wait_for(lambda: events == [("save", (b"a", b"a"))] * 2, timeout=60)

    db.add_listener(listener)
    db.delete(b"a", b"b")
    db.save(b"a", b"c")
    # InMemory database fires immediately, while DirectoryBased has to
    # wait for filesystem listeners. Therefore the events can arrive out of
    # order. Test a weaker multiset property, disregarding ordering.
    wait_for(
        lambda: Counter(events[2:])
        == {
            # InMemory
            ("delete", (b"a", b"b")): 1,
            # DirectoryBased
            ("delete", (b"a", None)): 1,
            # both
            ("save", (b"a", b"c")): 2,
        },
        timeout=60,
    )


@skipif_threading  # add_listener is not thread safe because watchdog is not
@pytest.mark.skipif(OSX, reason="times out consistently on osx")
def test_database_listener_directory_explicit(tmp_path):
    db = DirectoryBasedExampleDatabase(tmp_path)
    events = []

    def listener(event):
        events.append(event)

    db.add_listener(listener)

    db.save(b"k1", b"v1")
    wait_for(lambda: events == [("save", (b"k1", b"v1"))], timeout=60)

    db.remove_listener(listener)
    db.delete(b"k1", b"v1")
    db.save(b"k1", b"v2")
    wait_for(lambda: events == [("save", (b"k1", b"v1"))], timeout=60)

    db.add_listener(listener)
    db.delete(b"k1", b"v2")
    db.save(b"k1", b"v3")
    wait_for(
        lambda: events[1:]
        == [
            ("delete", (b"k1", None)),
            ("save", (b"k1", b"v3")),
        ],
        timeout=60,
    )

    # moving into a nonexistent key
    db.move(b"k1", b"k2", b"v3")
    time_sleep(0.5)
    # moving back into an existing key
    db.move(b"k2", b"k1", b"v3")
    time_sleep(0.5)

    if sys.platform.startswith("darwin"):
        assert events[3:] == [
            ("delete", (b"k1", b"v3")),
            ("save", (b"k2", b"v3")),
            ("delete", (b"k2", b"v3")),
            ("save", (b"k1", b"v3")),
        ], str(events[3:])
    elif sys.platform.startswith("win"):
        # watchdog fires save/delete events instead of move events on windows.
        # This means we don't broadcast the exact deleted value.
        assert events[3:] == [
            ("delete", (b"k1", None)),
            ("save", (b"k2", b"v3")),
            ("delete", (b"k2", None)),
            ("save", (b"k1", b"v3")),
        ], str(events[3:])
    elif sys.platform.startswith("linux"):
        # move #1
        assert ("save", (b"k2", b"v3")) in events
        # sometimes watchdog fires a move event (= save + delete with value),
        # and other times it fires separate save and delete events (= delete with
        # no value). I think this is due to particulars of what happens when
        # a new directory gets created very close to the time when a file is
        # saved to that directory.
        assert any(("delete", (b"k1", val)) in events for val in [b"v3", None])

        # move #2
        assert ("save", (b"k1", b"v3")) in events
        assert any(("delete", (b"k2", val)) in events for val in [b"v3", None])
    else:
        raise NotImplementedError(f"unknown platform {sys.platform}")


@flaky(max_runs=5, min_passes=1)  # time_sleep(0.1) probably isn't enough here
@skipif_threading  # add_listener is not thread safe because watchdog is not
def test_database_listener_directory_move(tmp_path):
    db = DirectoryBasedExampleDatabase(tmp_path)
    events = []

    def listener(event):
        events.append(event)

    # make sure both keys exist and that v1 exists in k1 and not k2
    db.save(b"k1", b"v1")
    db.save(b"k2", b"v_unrelated")

    time_sleep(0.1)
    db.add_listener(listener)
    time_sleep(0.1)

    db.move(b"k1", b"k2", b"v1")
    # events might arrive in either order
    wait_for(
        lambda: set(events)
        == {
            ("save", (b"k2", b"v1")),
            # windows doesn't fire move events, so value is None
            ("delete", (b"k1", None if sys.platform.startswith("win") else b"v1")),
        },
        timeout=60,
    )


@skipif_threading  # add_listener is not thread safe because watchdog is not
def test_still_listens_if_directory_did_not_exist(tmp_path):
    # if we start listening on a nonexistent path, we will create that path and
    # still listen for events
    events = []

    def listener(event):
        events.append(event)

    p = tmp_path / "does_not_exist_yet"
    db = DirectoryBasedExampleDatabase(p)
    assert not p.exists()

    db.add_listener(listener)
    assert p.exists()

    assert not events
    db.save(b"k1", b"v1")
    wait_for(lambda: len(events) == 1, timeout=60)
