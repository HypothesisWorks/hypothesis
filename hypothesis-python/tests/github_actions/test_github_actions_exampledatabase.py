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

import pytest

from hypothesis import given, strategies as st
from hypothesis.database import ReadOnlyDatabase
from hypothesis.extra.github_actions import GitHubArtifactDatabase


def test_require_readonly_wrapping():
    database = GitHubArtifactDatabase("test", "test")
    # save, move and delete can only be called when wrapped around ReadonlyDatabase
    with pytest.raises(RuntimeError):
        database.save(b"foo", b"bar")
    with pytest.raises(RuntimeError):
        database.move(b"foo", b"bar")
    with pytest.raises(RuntimeError):
        database.delete(b"foo", b"bar")

    # check that the database silently ignores writes when wrapped around ReadOnlyDatabase
    database = ReadOnlyDatabase(database)
    database.save(b"foo", b"bar")
    database.move(b"foo", b"bar")
    database.delete(b"foo", b"bar")


@given(st.binary(), st.binary())
def test_database_not_created_when_not_used(tmp_path_factory, key, value):
    path = tmp_path_factory.mktemp("hypothesis") / "examples"
    assert not os.path.exists(str(path))
    database = GitHubArtifactDatabase("test", "test", path=path)
    assert not list(database.fetch(key))
    assert not os.path.exists(str(path))
    database.save(key, value)
    assert os.path.exists(str(path))
    assert list(database.fetch(key)) == [value]
