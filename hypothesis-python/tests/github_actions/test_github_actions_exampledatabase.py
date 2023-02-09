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

from hypothesis.extra.github_actions import GitHubArtifactDatabase

from hypothesis import given
from hypothesis import strategies as st


def test_readonly_db_is_not_writable():
    wrapped = GitHubArtifactDatabase("test", "test")
    wrapped.create(b"key", b"value")
    assert wrapped.fetch(b"key") is None


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
