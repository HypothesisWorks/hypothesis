# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, unicode_literals

import os

__hypothesis_home_directory = None


def set_hypothesis_home_dir(directory):
    global __hypothesis_home_directory
    __hypothesis_home_directory = directory


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError:
        pass


def hypothesis_home_dir():
    global __hypothesis_home_directory
    if not __hypothesis_home_directory:
        __hypothesis_home_directory = os.getenv('HYPOTHESIS_STORAGE_DIRECTORY')
    if not __hypothesis_home_directory:
        __hypothesis_home_directory = os.path.join(
            os.getcwd(), '.hypothesis'
        )
    mkdir_p(__hypothesis_home_directory)
    return __hypothesis_home_directory


def storage_directory(name):
    path = os.path.join(hypothesis_home_dir(), name)
    mkdir_p(path)
    return path
