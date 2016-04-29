# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import os

import hypothesis.configuration as fs

previous_home_dir = None


def setup_function(function):
    global previous_home_dir
    previous_home_dir = fs.hypothesis_home_dir()
    fs.set_hypothesis_home_dir(None)


def teardown_function(function):
    global previous_home_dir
    fs.set_hypothesis_home_dir(previous_home_dir)
    previous_home_dir = None


def test_homedir_exists_automatically():
    assert os.path.exists(fs.hypothesis_home_dir())


def test_can_set_homedir_and_it_will_exist(tmpdir):
    fs.set_hypothesis_home_dir(str(tmpdir.mkdir(u'kittens')))
    d = fs.hypothesis_home_dir()
    assert u'kittens' in d
    assert os.path.exists(d)


def test_will_pick_up_location_from_env(tmpdir):
    os.environ[u'HYPOTHESIS_STORAGE_DIRECTORY'] = str(tmpdir)
    assert fs.hypothesis_home_dir() == str(tmpdir)


def test_storage_directories_are_created_automatically(tmpdir):
    fs.set_hypothesis_home_dir(str(tmpdir))
    assert os.path.exists(fs.storage_directory(u'badgers'))
