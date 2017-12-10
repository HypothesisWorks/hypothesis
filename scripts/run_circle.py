#!/usr/bin/env python

# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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
import subprocess
import sys

from hypothesistooling import should_run_ci_task


if __name__ == '__main__':
    
    if (
        os.environ['CIRCLE_BRANCH'] != 'master' and 
        os.environ['CI_PULL_REQUEST'] == ''
    ):
        print('We only run CI builds on the master branch or in pull requests')
        sys.exit(0)
    
    is_pull_request = (os.environ['CI_PULL_REQUEST'] != '')
    
    for task in ['check-pypy', 'check-py36', 'check-py27']:
        if should_run_ci_task(task=task, is_pull_request=is_pull_request):
            subprocess.check_call(['make', task])
