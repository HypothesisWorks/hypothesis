# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import inspect
import json
from collections import defaultdict

import pytest
from _pytest.monkeypatch import MonkeyPatch

# we'd like to support xdist here for parallelism, but a session-scope fixture won't
# be enough: https://github.com/pytest-dev/pytest-xdist/issues/271. need a lockfile
# or equivalent.
shrink_calls = defaultdict(list)


def pytest_collection_modifyitems(config, items):
    skip = pytest.mark.skip(reason="Does not call minimal()")
    for item in items:
        # is this perfect? no. but it is cheap!
        if " minimal(" in inspect.getsource(item.obj):
            continue
        item.add_marker(skip)


@pytest.fixture(scope="function", autouse=True)
def _benchmark_shrinks():
    from hypothesis.internal.conjecture.shrinker import Shrinker

    monkeypatch = MonkeyPatch()

    def record_shrink_calls(calls):
        name = None
        for frame in inspect.stack():
            if frame.function.startswith("test_"):
                name = f"{frame.filename.split('/')[-1]}::{frame.function}"
        # some minimal calls happen at collection-time outside of a test context
        # (maybe something we should fix/look into)
        if name is None:
            return

        shrink_calls[name].append(calls)

    old_shrink = Shrinker.shrink

    def shrink(self, *args, **kwargs):
        v = old_shrink(self, *args, **kwargs)
        record_shrink_calls(self.engine.call_count - self.initial_calls)
        return v

    monkeypatch.setattr(Shrinker, "shrink", shrink)
    yield

    # start teardown
    Shrinker.shrink = old_shrink


def pytest_sessionfinish(session, exitstatus):
    print(f"\nshrinker profiling:\n{json.dumps(shrink_calls)}")
