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
import json
import warnings
from os import getenv
from pathlib import Path
from typing import Dict, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zipfile import BadZipFile
from zipfile import Path as ZipPath
from zipfile import ZipFile

from hypothesis.configuration import mkdir_p, storage_directory
from hypothesis.database import ExampleDatabase, _hash
from hypothesis.errors import HypothesisWarning


class GitHubArtifactDatabase(ExampleDatabase):
    """
    A directory-based database loaded from a GitHub Actions artifact.

    This is useful for sharing example databases between CI runs and developers, allowing the latter
    to get read-only access to the former. In most cases, this will be used through the
    :class:`~hypothesis.database.MultiplexedDatabase`, by combining a local directory-based database
    with this one. For example:

    .. code-block:: python

        local = DirectoryBasedExampleDatabase(".hypothesis/examples")
        shared = ReadOnlyDatabase(GitHubArtifactDatabase("user", "repo"))

        settings.register_profile("ci", database=local)
        settings.register_profile("dev", database=MultiplexedDatabase(local, shared))
        settings.load_profile("ci" if os.environ.get("CI") else "dev")

    .. note::
        Because this database is read-only, you always need to wrap it with the
        :class:`ReadOnlyDatabase`.

    If you're using a private repository, you must provide `GITHUB_TOKEN` as an environment variable,
    which would usually be a Personal Access Token with the `repo` scope.

    The database automatically implements a simple file-based cache with a default expiration period
    of 1 day. You can adjust this through the `cache_timeout` property.

    For mono-repo support, you can provide an unique `artifact_name` (e.g. `hypofuzz-example-db-branch`).
    """

    def __init__(
        self,
        owner: str,
        repo: str,
        artifact_name: str = "hypofuzz-example-db",
        cache_timeout: datetime.timedelta = datetime.timedelta(days=1),
    ):
        self.owner = owner
        self.repo = repo
        self.artifact_name = artifact_name
        self.cache_timeout = cache_timeout

        self.keypaths: Dict[str, ZipPath] = {}

        # Get the GitHub token from the environment
        # It's unnecessary to use a token if the repo is public
        self.token: str | None = getenv("GITHUB_TOKEN")

        self._path: Path = Path(
            storage_directory(f"github-artifact/{self.artifact_name}/")
        )
        # We don't want to initialize the cache until we need to
        self._initialized: bool = False
        self._disabled: bool = False

        # This is the path to the artifact in usage
        # .hypothesis/ci/github-artifacts/<artifact-name>/<isoformat>.zip
        self._artifact: Path | None = None

        # This is the FS root for the in-memory zipfile
        self._root: ZipPath | None = None

    def __repr__(self) -> str:
        return f"GitHubArtifactDatabase(owner={self.owner}, repo={self.repo}, artifact_name={self.artifact_name})"

    def _initialize_io(self) -> None:
        if self._initialized:
            return

        # Load the artifact into memory
        # This root allows us to access the files in the zipfile as if they were on the FS
        # It's compatible with the pathlib Path API
        self._root = ZipPath(str(self._artifact))
        self._initialized = True

    def _initialize_db(self) -> None:
        # Create the cache directory if it doesn't exist
        mkdir_p(str(self._path))

        # Get all artifacts
        cached_artifacts = sorted(
            self._path.glob("*.zip"),
            key=lambda a: datetime.datetime.fromisoformat(a.stem),
        )

        # Remove all but the latest artifact
        for new_artifact in cached_artifacts[:-1]:
            new_artifact.unlink()

        try:
            found_artifact = cached_artifacts[-1]
        except IndexError:
            found_artifact = None

        # Check if the latest artifact is a cache hit
        if found_artifact is not None and (
            datetime.datetime.now()
            - datetime.datetime.fromisoformat(found_artifact.stem)
            < self.cache_timeout
        ):
            self._artifact = found_artifact
            self._initialize_io()
            return

        # Download the latest artifact from GitHub
        new_artifact = self._fetch_artifact()

        if new_artifact:
            if found_artifact is not None:
                found_artifact.unlink()
            self._artifact = new_artifact
        elif found_artifact is not None:
            warnings.warn(
                HypothesisWarning(
                    "Using an expired artifact as a fallback for the database."
                )
            )
            self._artifact = found_artifact
        else:
            warnings.warn(HypothesisWarning("Disabling shared database due to errors."))
            self._disabled = True
            return

        self._initialize_io()

    def _fetch_artifact(self) -> Path | None:
        # Get the list of artifacts from GitHub
        request = Request(
            f"https://api.github.com/repos/{self.owner}/{self.repo}/actions/artifacts",
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28 ",
                "Authorization": f"Bearer {self.token}",
            },
        )

        try:
            response = urlopen(request)
            artifacts = json.loads(response.read())["artifacts"]
        except HTTPError as e:
            if e.code == 401:
                warnings.warn(
                    HypothesisWarning(
                        "Authorization failed when trying to download artifact from GitHub. "
                        "Check your $GITHUB_TOKEN environment variable or make the repository public. "
                    )
                )
                return None
            else:
                warnings.warn(
                    HypothesisWarning(
                        "Could not get the latest artifact from GitHub. "
                        "This could be because because the repository or artifact does not exist. "
                    )
                )
            return None
        except URLError:
            warnings.warn(
                HypothesisWarning(
                    "Could not connect to GitHub to get the latest artifact. "
                )
            )
            return None
        except TimeoutError:
            warnings.warn(
                HypothesisWarning(
                    "Could not connect to GitHub to get the latest artifact (connection timed out). "
                )
            )
            return None

        # Get the latest artifact from the list
        artifact = sorted(
            filter(lambda a: a["name"] == self.artifact_name, artifacts),
            key=lambda a: a["created_at"],
        )[-1]

        request = Request(
            artifact["archive_download_url"],
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Authorization": f"Bearer {self.token}",
            },
        )

        # Download the artifact
        try:
            response = urlopen(request)
            artifact_bytes = response.read()
        except HTTPError as e:
            if e.code == 401:
                warnings.warn(
                    HypothesisWarning(
                        "Authorization failed when trying to download artifact from GitHub. "
                        "Check your $GITHUB_TOKEN environment variable or make the repository public. "
                    )
                )
                return None
            else:
                warnings.warn(
                    HypothesisWarning(
                        "Could not get the latest artifact from GitHub. "
                        "This could be because because the repository or artifact does not exist. "
                    )
                )
            return None
        except URLError:
            warnings.warn(
                HypothesisWarning(
                    "Could not connect to GitHub to get the latest artifact. "
                )
            )
            return None
        except TimeoutError:
            warnings.warn(
                HypothesisWarning(
                    "Could not connect to GitHub to get the latest artifact (connection timed out). "
                )
            )
            return None

        # Save the artifact to the cache
        artifact_path = self._path / f"{datetime.datetime.now().isoformat()}.zip"
        try:
            with open(artifact_path, "wb") as f:
                f.write(artifact_bytes)
        except OSError:
            warnings.warn(
                HypothesisWarning("Could not save the latest artifact from GitHub. ")
            )
            return None

        # Test that the artifact is valid
        try:
            with ZipFile(artifact_path) as f:
                if f.testzip():
                    raise BadZipFile
        except BadZipFile:
            warnings.warn(
                HypothesisWarning(
                    "The downloaded artifact from GitHub is invalid. "
                    "This could be because the artifact was corrupted, "
                    "or because the artifact was not created by Hypothesis. "
                )
            )
            return None

        return artifact_path

    def _key_path(self, key) -> ZipPath:
        assert self._root is not None
        try:
            return self.keypaths[key]
        except KeyError:
            pass
        directory = self._root.joinpath(_hash(key))
        self.keypaths[key] = directory
        return directory

    def fetch(self, key: bytes) -> Iterable[bytes]:
        if self._disabled:
            return

        if not self._initialized:
            self._initialize_db()
            if self._disabled:
                return

        kp = self._key_path(key)
        if not kp.exists():
            return
        for path in kp.iterdir():
            try:
                with path.open("rb") as i:
                    yield i.read()
            except OSError:
                pass

    # Read-only interface
    def save(self, key: bytes, value: bytes) -> None:
        raise RuntimeError(
            "This database is read-only. Please wrap this class with ReadOnlyDatabase, i.e. ReadOnlyDatabase(GitHubArtifactsDatabase(...))."
        )

    def move(self, key: bytes, value: bytes) -> None:
        raise RuntimeError(
            "This database is read-only. Please wrap this class with ReadOnlyDatabase, i.e. ReadOnlyDatabase(GitHubArtifactsDatabase(...))."
        )

    def delete(self, key: bytes, value: bytes) -> None:
        raise RuntimeError(
            "This database is read-only. Please wrap this class with ReadOnlyDatabase, i.e. ReadOnlyDatabase(GitHubArtifactsDatabase(...))."
        )
