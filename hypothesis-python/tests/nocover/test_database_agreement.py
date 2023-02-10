# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import datetime
import os
import shutil
import tempfile
from pathlib import Path
from zipfile import Path as ZipPath
from zipfile import ZipFile

from hypothesis.database import (
    DirectoryBasedExampleDatabase,
    InMemoryExampleDatabase,
    GitHubArtifactDatabase,
    _hash,
)
from hypothesis.stateful import Bundle, RuleBasedStateMachine, rule

from hypothesis import strategies as st


class GitHubArtifactMock:
    def __init__(self, tempd: str):
        self.tempd = tempd

        # This is a hack to create a fake GA artifact
        # Create a new empty zip file
        artifact_directory = Path(self.tempd) / "github-artifacts"
        artifact_directory.mkdir(parents=True, exist_ok=True)
        # This file should trigger the cache mechanism
        artifact_path = (
            artifact_directory / f"{datetime.datetime.now().isoformat()}.zip"
        )
        # Create a zip file
        with ZipFile(artifact_path, "w") as zip_file:
            # Create a new zip file
            zip_file.writestr(".mock", "")

        self._ga_root = ZipPath(artifact_path)
        self.db = GitHubArtifactDatabase("mock", "mock", artifact_directory)
        self.db._initialize_db()

        # Check that we have the same artifact path
        assert self.db._artifact == artifact_path

    def _value_path(self, key: bytes, value: bytes):
        return self.db._key_path(key) / _hash(value)

    def save(self, key: bytes, value: bytes):
        self.db._key_path(key).mkdir(parents=True, exist_ok=True)
        path: Path = self._value_path(key, value)
        if not path.exists():
            path.write_bytes(value)

    def move(self, src: bytes, dest: bytes, value: bytes):
        if src == dest:
            self.save(src, value)
            return
        try:
            self._value_path(src, value).rename(self._value_path(dest, value))
        except OSError:
            self.delete(src, value)
            self.save(dest, value)

    def delete(self, key: bytes, value: bytes):
        try:
            self._value_path(key, value).unlink()
        except OSError:
            pass


class DatabaseComparison(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.tempd = tempfile.mkdtemp()
        exampledir = os.path.join(self.tempd, "examples")

        self.ga = GitHubArtifactMock(self.tempd)

        self.w_dbs = [
            DirectoryBasedExampleDatabase(exampledir),
            InMemoryExampleDatabase(),
            DirectoryBasedExampleDatabase(exampledir),
            self.ga,
        ]

        self.r_dbs = [
            DirectoryBasedExampleDatabase(exampledir),
            InMemoryExampleDatabase(),
            DirectoryBasedExampleDatabase(exampledir),
            self.ga.db,
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
        for db in self.w_dbs:
            db.save(k, v)

    @rule(k=keys, v=values)
    def delete(self, k, v):
        for db in self.w_dbs:
            db.delete(k, v)

    @rule(k1=keys, k2=keys, v=values)
    def move(self, k1, k2, v):
        for db in self.w_dbs:
            db.move(k1, k2, v)

    @rule(k=keys)
    def values_agree(self, k):
        last = None
        last_db = None
        for db in self.r_dbs:
            keys = set(db.fetch(k))
            if last is not None:
                assert last == keys, (last_db, db)
            last = keys
            last_db = db

    def teardown(self):
        shutil.rmtree(self.tempd)


TestDBs = DatabaseComparison.TestCase
