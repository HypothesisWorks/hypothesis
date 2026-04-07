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

from hypothesis import configuration as fs

previous_home_dir = None


def setup_function(function):
    global previous_home_dir
    previous_home_dir = fs.storage_directory()
    fs.set_hypothesis_home_dir(None)


def teardown_function(function):
    global previous_home_dir
    fs.set_hypothesis_home_dir(previous_home_dir)
    previous_home_dir = None


def test_defaults_to_the_default():
    assert fs.storage_directory() == fs.__hypothesis_home_directory_default


def test_can_set_homedir(tmp_path):
    fs.set_hypothesis_home_dir(tmp_path)
    assert fs.storage_directory("kittens") == tmp_path / "kittens"


def test_will_pick_up_location_from_env(monkeypatch, tmp_path):
    monkeypatch.setattr(os, "environ", {"HYPOTHESIS_STORAGE_DIRECTORY": str(tmp_path)})
    assert fs.storage_directory() == tmp_path


def test_storage_directories_are_not_created_automatically(tmp_path):
    fs.set_hypothesis_home_dir(tmp_path)
    assert not fs.storage_directory("badgers").exists()
