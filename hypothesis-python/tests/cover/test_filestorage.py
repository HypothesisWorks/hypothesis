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
import subprocess
import sys
import textwrap

import pytest

from hypothesis import configuration as fs

previous_home_dir = None


def setup_function(function):
    global previous_home_dir
    previous_home_dir = fs.storage_directory().path
    fs.set_hypothesis_home_dir(None)


def teardown_function(function):
    global previous_home_dir
    fs.set_hypothesis_home_dir(previous_home_dir)
    previous_home_dir = None


def test_defaults_to_the_default():
    assert fs.storage_directory().path == fs.__hypothesis_home_directory_default


def test_can_set_homedir(tmp_path):
    fs.set_hypothesis_home_dir(tmp_path)
    assert fs.storage_directory("kittens").path == tmp_path / "kittens"


def test_will_pick_up_location_from_env(monkeypatch, tmp_path):
    monkeypatch.setattr(os, "environ", {"HYPOTHESIS_STORAGE_DIRECTORY": str(tmp_path)})
    assert fs.storage_directory().path == tmp_path


def test_storage_directories_are_not_created_automatically(tmp_path):
    fs.set_hypothesis_home_dir(tmp_path)
    assert not fs.storage_directory("badgers").path.exists()


def _gitignore_storage_dir_script(*, home_dir=None):
    return textwrap.dedent(f"""
        from hypothesis import given, strategies as st
        from hypothesis.configuration import set_hypothesis_home_dir

        home_dir = {repr(str(home_dir)) if home_dir is not None else None}
        if home_dir:
            set_hypothesis_home_dir(home_dir)

        @given(st.integers())
        def f(n):
            # fail to guarantee we write a file to .hypothesis/examples
            raise ValueError()

        try:
            f()
        except Exception:
            pass
        """)


@pytest.mark.parametrize("set_home_dir", [False, True])
def test_writes_gitignore_to_new_storage_dir(tmp_path, set_home_dir):
    subprocess.check_call(["git", "init", str(tmp_path)])

    home_dir = tmp_path / ("custom_storage_dir" if set_home_dir else ".hypothesis")
    (tmp_path / "test_a.py").write_text(
        _gitignore_storage_dir_script(home_dir=home_dir if set_home_dir else None),
        encoding="utf-8",
    )

    subprocess.check_call([sys.executable, "test_a.py"], cwd=tmp_path)
    assert home_dir.is_dir()
    assert (home_dir / ".gitignore").exists()

    status = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=tmp_path, text=True
    )
    assert home_dir.name not in status


@pytest.mark.parametrize("set_home_dir", [False, True])
def test_skips_gitignore_for_existing_storage_dir(tmp_path, set_home_dir):
    home_dir = tmp_path / ("custom_storage_dir" if set_home_dir else ".hypothesis")
    home_dir.mkdir()

    (tmp_path / "test_a.py").write_text(
        _gitignore_storage_dir_script(home_dir=home_dir if set_home_dir else None),
        encoding="utf-8",
    )

    subprocess.check_call([sys.executable, "test_a.py"], cwd=tmp_path)
    assert not (home_dir / ".gitignore").exists()
