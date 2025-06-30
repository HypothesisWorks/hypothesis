# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis.utils.threading import ThreadLocal


def test_threadlocal_setattr_and_getattr():
    threadlocal = ThreadLocal(a=1, b=2)
    assert threadlocal.a == 1
    assert threadlocal.b == 2
    # check that we didn't add attributes to the ThreadLocal instance itself
    # instead of its threading.local() variable
    assert set(threadlocal.__dict__) == {
        "_ThreadLocal__initialized",
        "_ThreadLocal__kwargs",
        "_ThreadLocal__threadlocal",
    }

    threadlocal.a = 3
    assert threadlocal.a == 3
    assert threadlocal.b == 2
    assert set(threadlocal.__dict__) == {
        "_ThreadLocal__initialized",
        "_ThreadLocal__kwargs",
        "_ThreadLocal__threadlocal",
    }


def test_nonexistent_getattr_raises():
    threadlocal = ThreadLocal(a=1)
    with pytest.raises(AttributeError):
        _c = threadlocal.c


def test_nonexistent_setattr_raises():
    threadlocal = ThreadLocal(a=1)
    with pytest.raises(AttributeError):
        threadlocal.c = 2
