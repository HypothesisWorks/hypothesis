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
import re
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path
from shutil import make_archive, rmtree
from typing import Optional

import pytest

from hypothesis import configuration, example, given, settings, strategies as st
from hypothesis.database import (
    BackgroundWriteDatabase,
    DirectoryBasedExampleDatabase,
    ExampleDatabase,
    GitHubArtifactDatabase,
    InMemoryExampleDatabase,
    MultiplexedDatabase,
    ReadOnlyDatabase,
    _pack_uleb128,
    _unpack_uleb128,
    choices_from_bytes,
    choices_to_bytes,
)
from hypothesis.errors import HypothesisWarning
from hypothesis.internal.compat import WINDOWS
from hypothesis.internal.conjecture.choice import choice_equal
from hypothesis.stateful import Bundle, RuleBasedStateMachine, rule
from hypothesis.strategies import binary, lists, tuples
from hypothesis.utils.conventions import not_set

from tests.common.utils import skipif_emscripten
from tests.conjecture.common import ir, nodes

small_settings = settings(max_examples=50)


@given(lists(tuples(binary(), binary())))
@small_settings
def test_backend_returns_what_you_put_in(xs):
    backend = InMemoryExampleDatabase()
    mapping = {}
    for key, value in xs:
        mapping.setdefault(key, set()).add(value)
        backend.save(key, value)
    for key, values in mapping.items():
        backend_contents = list(backend.fetch(key))
        distinct_backend_contents = set(backend_contents)
        assert len(backend_contents) == len(distinct_backend_contents)
        assert distinct_backend_contents == set(values)


def test_can_delete_keys():
    backend = InMemoryExampleDatabase()
    backend.save(b"foo", b"bar")
    backend.save(b"foo", b"baz")
    backend.delete(b"foo", b"bar")
    assert list(backend.fetch(b"foo")) == [b"baz"]


def test_default_database_is_in_memory():
    assert isinstance(ExampleDatabase(), InMemoryExampleDatabase)


def test_default_on_disk_database_is_dir(tmp_path):
    assert isinstance(
        ExampleDatabase(tmp_path.joinpath("foo")), DirectoryBasedExampleDatabase
    )


def test_does_not_error_when_fetching_when_not_exist(tmp_path):
    db = DirectoryBasedExampleDatabase(tmp_path / "examples")
    db.fetch(b"foo")


@pytest.fixture(scope="function", params=["memory", "directory"])
def exampledatabase(request, tmp_path):
    if request.param == "memory":
        return ExampleDatabase()
    assert request.param == "directory"
    return DirectoryBasedExampleDatabase(tmp_path / "examples")


def test_can_delete_a_key_that_is_not_present(exampledatabase):
    exampledatabase.delete(b"foo", b"bar")


def test_can_fetch_a_key_that_is_not_present(exampledatabase):
    assert list(exampledatabase.fetch(b"foo")) == []


def test_saving_a_key_twice_fetches_it_once(exampledatabase):
    exampledatabase.save(b"foo", b"bar")
    exampledatabase.save(b"foo", b"bar")
    assert list(exampledatabase.fetch(b"foo")) == [b"bar"]


def test_can_close_a_database_after_saving(exampledatabase):
    exampledatabase.save(b"foo", b"bar")


def test_class_name_is_in_repr(exampledatabase):
    assert type(exampledatabase).__name__ in repr(exampledatabase)


def test_an_absent_value_is_present_after_it_moves(exampledatabase):
    exampledatabase.move(b"a", b"b", b"c")
    assert next(exampledatabase.fetch(b"b")) == b"c"


def test_an_absent_value_is_present_after_it_moves_to_self(exampledatabase):
    exampledatabase.move(b"a", b"a", b"b")
    assert next(exampledatabase.fetch(b"a")) == b"b"


def test_two_directory_databases_can_interact(tmp_path):
    db1 = DirectoryBasedExampleDatabase(tmp_path)
    db2 = DirectoryBasedExampleDatabase(tmp_path)
    db1.save(b"foo", b"bar")
    assert list(db2.fetch(b"foo")) == [b"bar"]
    db2.save(b"foo", b"bar")
    db2.save(b"foo", b"baz")
    assert sorted(db1.fetch(b"foo")) == [b"bar", b"baz"]


def test_can_handle_disappearing_files(tmp_path, monkeypatch):
    db = DirectoryBasedExampleDatabase(tmp_path)
    db.save(b"foo", b"bar")
    base_listdir = os.listdir
    monkeypatch.setattr(
        os, "listdir", lambda d: [*base_listdir(d), "this-does-not-exist"]
    )
    assert list(db.fetch(b"foo")) == [b"bar"]


def test_readonly_db_is_not_writable():
    inner = InMemoryExampleDatabase()
    wrapped = ReadOnlyDatabase(inner)
    inner.save(b"key", b"value")
    inner.save(b"key", b"value2")
    wrapped.delete(b"key", b"value")
    wrapped.move(b"key", b"key2", b"value2")
    wrapped.save(b"key", b"value3")
    assert set(wrapped.fetch(b"key")) == {b"value", b"value2"}
    assert set(wrapped.fetch(b"key2")) == set()


def test_multiplexed_dbs_read_and_write_all():
    a = InMemoryExampleDatabase()
    b = InMemoryExampleDatabase()
    multi = MultiplexedDatabase(a, b)
    a.save(b"a", b"aa")
    b.save(b"b", b"bb")
    multi.save(b"c", b"cc")
    multi.move(b"a", b"b", b"aa")
    for db in (a, b, multi):
        assert set(db.fetch(b"a")) == set()
        assert set(db.fetch(b"c")) == {b"cc"}
    got = list(multi.fetch(b"b"))
    assert len(got) == 2
    assert set(got) == {b"aa", b"bb"}
    multi.delete(b"c", b"cc")
    for db in (a, b, multi):
        assert set(db.fetch(b"c")) == set()


def test_ga_require_readonly_wrapping():
    """Test that GitHubArtifactDatabase requires wrapping around ReadOnlyDatabase"""
    database = GitHubArtifactDatabase("test", "test")
    # save, move and delete can only be called when wrapped around ReadonlyDatabase
    with pytest.raises(RuntimeError, match=re.escape(database._read_only_message)):
        database.save(b"foo", b"bar")
    with pytest.raises(RuntimeError):
        database.move(b"foo", b"bar", b"foobar")
    with pytest.raises(RuntimeError):
        database.delete(b"foo", b"bar")

    # check that the database silently ignores writes when wrapped around ReadOnlyDatabase
    database = ReadOnlyDatabase(database)
    database.save(b"foo", b"bar")
    database.move(b"foo", b"bar", b"foobar")
    database.delete(b"foo", b"bar")


@contextmanager
def ga_empty_artifact(
    date: Optional[datetime] = None, path: Optional[Path] = None
) -> Iterator[tuple[Path, Path]]:
    """Creates an empty GitHub artifact."""
    if date:
        timestamp = date.isoformat().replace(":", "_")
    else:
        timestamp = datetime.now(timezone.utc).isoformat().replace(":", "_")

    temp_dir = None
    if not path:
        temp_dir = tempfile.mkdtemp()
        path = Path(temp_dir) / "github-artifacts"

    path.mkdir(parents=True, exist_ok=True)
    zip_path = path / f"{timestamp}.zip"

    with zipfile.ZipFile(zip_path, "w"):
        pass

    try:
        yield (path, zip_path)
    finally:
        if temp_dir:
            rmtree(temp_dir)


def test_ga_empty_read():
    """Tests that an inexistent key returns nothing."""
    with ga_empty_artifact() as (path, _):
        database = GitHubArtifactDatabase("test", "test", path=path)
        assert list(database.fetch(b"foo")) == []


def test_ga_initialize():
    """
    Tests that the database is initialized when a new artifact is found.
    As well that initialization doesn't happen again on the next fetch.
    """
    now = datetime.now(timezone.utc)
    with ga_empty_artifact(date=(now - timedelta(hours=2))) as (path, _):
        database = GitHubArtifactDatabase("test", "test", path=path)
        # Trigger initialization
        list(database.fetch(b""))
        initial_artifact = database._artifact
        assert initial_artifact
        assert database._artifact
        assert database._access_cache is not None
        with ga_empty_artifact(date=now, path=path) as (path, _):
            # Initialization shouldn't happen again
            list(database.fetch(b""))
            assert database._initialized
            assert database._artifact == initial_artifact


def test_ga_no_artifact(tmp_path):
    """Tests that the database is disabled when no artifact is found."""
    database = GitHubArtifactDatabase("test", "test", path=tmp_path)
    # Check that the database raises a warning
    with pytest.warns(HypothesisWarning):
        assert list(database.fetch(b"")) == []
    assert database._disabled is True
    assert list(database.fetch(b"")) == []


def test_ga_corrupted_artifact():
    """Tests that corrupted artifacts are properly detected and warned about."""
    with ga_empty_artifact() as (path, zip_path):
        # Corrupt the CRC of the zip file
        with open(zip_path, "rb+") as f:
            f.write(b"\x00\x01\x00\x01")

        database = GitHubArtifactDatabase("test", "test", path=path)
        # Check that the database raises a warning
        with pytest.warns(HypothesisWarning):
            assert list(database.fetch(b"")) == []
        assert database._disabled is True


def test_ga_deletes_old_artifacts():
    """Tests that old artifacts are automatically deleted."""
    now = datetime.now(timezone.utc)
    with ga_empty_artifact(date=now) as (path, file_now):
        with ga_empty_artifact(date=now - timedelta(hours=2), path=path) as (
            _,
            file_old,
        ):
            database = GitHubArtifactDatabase("test", "test", path=path)
            # Trigger initialization
            list(database.fetch(b""))
            assert file_now.exists()
            assert not file_old.exists()


def test_ga_triggers_fetching(monkeypatch, tmp_path):
    """Tests whether an artifact fetch is triggered, and an expired artifact is deleted."""
    with ga_empty_artifact() as (_, artifact):
        # We patch the _fetch_artifact method to return our artifact
        def fake_fetch_artifact(self) -> Optional[Path]:
            return artifact

        monkeypatch.setattr(
            GitHubArtifactDatabase, "_fetch_artifact", fake_fetch_artifact
        )

        database = GitHubArtifactDatabase(
            "test", "test", path=tmp_path, cache_timeout=timedelta(days=1)
        )

        # Test without an existing artifact
        list(database.fetch(b""))

        assert not database._disabled
        assert database._initialized
        assert database._artifact == artifact

        # Now we'll see if the DB also fetched correctly with an expired artifact
        now = datetime.now(timezone.utc)
        # We create an expired artifact
        with ga_empty_artifact(date=now - timedelta(days=2)) as (
            path_with_artifact,
            old_artifact,
        ):
            database = GitHubArtifactDatabase(
                "test", "test", path=path_with_artifact, cache_timeout=timedelta(days=1)
            )

            # Trigger initialization
            list(database.fetch(b""))
            assert not database._disabled
            assert database._initialized
            assert database._artifact == artifact

            # Check that the artifact was deleted
            assert not old_artifact.exists()


def test_ga_fallback_expired(monkeypatch):
    """
    Tests that the fallback to an expired artifact is triggered
    if fetching a new one fails. This allows for (by example) offline development.
    """
    now = datetime.now(timezone.utc)
    with ga_empty_artifact(date=now - timedelta(days=2)) as (path, artifact):
        database = GitHubArtifactDatabase(
            "test", "test", path=path, cache_timeout=timedelta(days=1)
        )

        # This should trigger the fallback
        def fake_fetch_artifact(self) -> Optional[Path]:
            return None

        monkeypatch.setattr(
            GitHubArtifactDatabase, "_fetch_artifact", fake_fetch_artifact
        )

        # Trigger initialization
        with pytest.warns(HypothesisWarning):
            list(database.fetch(b""))

        assert not database._disabled
        assert database._initialized
        assert database._artifact == artifact


class GitHubArtifactMocks(RuleBasedStateMachine):
    """
    This is a state machine that tests agreement of GitHubArtifactDatabase
    with DirectoryBasedExampleDatabase (as a reference implementation).
    """

    def __init__(self):
        super().__init__()
        self.temp_directory = Path(tempfile.mkdtemp())
        self.path = self.temp_directory / "github-artifacts"

        # This is where we will store the contents for the zip file
        timestamp = datetime.now(timezone.utc).isoformat().replace(":", "_")
        self.zip_destination = self.path / f"{timestamp}.zip"

        # And this is where we want to create it
        self.zip_content_path = self.path / timestamp
        self.zip_content_path.mkdir(parents=True, exist_ok=True)

        # We use a DirectoryBasedExampleDatabase to create the contents
        self.directory_db = DirectoryBasedExampleDatabase(str(self.zip_content_path))
        self.zip_db = GitHubArtifactDatabase("mock", "mock", path=self.path)

        # Create zip file for the first time
        self._archive_directory_db()
        self.zip_db._initialize_db()

    def _make_zip(self, tree_path: Path, zip_path: Path):
        destination = zip_path.parent.absolute() / zip_path.stem
        make_archive(
            str(destination),
            "zip",
            root_dir=tree_path,
        )

    def _archive_directory_db(self):
        # Delete all of the zip files in the directory
        for file in self.path.glob("*.zip"):
            file.unlink()

        self._make_zip(self.zip_content_path, self.zip_destination)

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
        self.directory_db.save(k, v)
        self._archive_directory_db()
        self.zip_db = GitHubArtifactDatabase("mock", "mock", path=self.path)
        self.zip_db._initialize_db()

    @rule(k=keys)
    def values_agree(self, k):
        v1 = set(self.directory_db.fetch(k))
        v2 = set(self.zip_db.fetch(k))

        assert v1 == v2


TestGADReads = GitHubArtifactMocks.TestCase


def test_gadb_coverage():
    # Ensure that we always cover the nonempty-archive case, which can otherwise
    # cause rare incomplete-coverage failures.
    state = GitHubArtifactMocks()
    state.save(b"key", b"value")
    state.values_agree(b"key")


@pytest.mark.parametrize("dirs", [[], ["subdir"]])
def test_database_directory_inaccessible(dirs, tmp_path, monkeypatch):
    monkeypatch.setattr(
        configuration, "__hypothesis_home_directory", tmp_path.joinpath(*dirs)
    )
    tmp_path.chmod(0o000)
    with (
        nullcontext()
        if WINDOWS
        else pytest.warns(HypothesisWarning, match=".*the default location is unusable")
    ):
        database = ExampleDatabase(not_set)
    database.save(b"fizz", b"buzz")


@skipif_emscripten
def test_background_write_database():
    db = BackgroundWriteDatabase(InMemoryExampleDatabase())
    db.save(b"a", b"b")
    db.save(b"a", b"c")
    db.save(b"a", b"d")
    assert set(db.fetch(b"a")) == {b"b", b"c", b"d"}

    db.move(b"a", b"a2", b"b")
    assert set(db.fetch(b"a")) == {b"c", b"d"}
    assert set(db.fetch(b"a2")) == {b"b"}

    db.delete(b"a", b"c")
    assert set(db.fetch(b"a")) == {b"d"}


@given(lists(nodes()))
# covering examples
@example(ir(True))
@example(ir(1))
@example(ir(0.0))
@example(ir(-0.0))
@example(ir("a"))
@example(ir(b"a"))
@example(ir(b"a" * 50))
@example(ir(b"1" * 100_000))  # really long bytes
def test_nodes_roundtrips(nodes1):
    s1 = choices_to_bytes([n.value for n in nodes1])
    assert isinstance(s1, bytes)
    ir2 = choices_from_bytes(s1)
    assert len(nodes1) == len(ir2)

    for n1, v2 in zip(nodes1, ir2):
        assert choice_equal(n1.value, v2)

    s2 = choices_to_bytes(ir2)
    assert s1 == s2


@given(st.integers(min_value=0))
def test_uleb_128_roundtrips(n1):
    buffer1 = _pack_uleb128(n1)
    idx, n2 = _unpack_uleb128(buffer1)
    assert idx == len(buffer1)
    assert n1 == n2
