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

import os
import subprocess


def changed_paths_from_master():
    """
    Returns a list of files which have changed in this pull request.
    """
    files = set()
    command = ['git', 'diff', '--name-only'] + list(args)
    diff_output = subprocess.check_output(command).decode('ascii')
    for line in diff_output.splitlines():
        filepath = line.strip()
        if filepath:
            files.add(filepath)
    return files


def _is_safe_file(path):
    """
    Is this a file which has no effect on test results?
    """
    if path.endswith(('.rst', '.ipynb')):
        return True
    
    if path in ('CITATION', 'LICENSE.txt', ):
        return True

    if path.startswith(('src/', 'tests/', 'requirements/', 'setup.py')):
        return False
    
    return False


def should_run_task(task):
    """
    Given a task name, should we run this task in Travis?  Returns True/False.
    """
    event_type = os.environ.get('TRAVIS_EVENT_TYPE')
    if event_type != 'pull_request':
        print(
            'We only skip Travis jobs if the job is a pull request, '
            'but here event_type=%r.' % event_type
        )
        return True
    
    # These tests are usually fast; we always run them rather than trying
    # to keep up-to-date rules of exactly which changed files mean they
    # should run.
    if task in [
        'check-pyup-yml',
        'check-release-file',
        'check-shellcheck',
        'documentation',
        'lint',
    ]:
        print('We always run the %s task.' % task)
        return True
    
    # The remaining tasks are all some sort of test of Hypothesis 
    # functionality.  Since it's better to run tests when we don't need to
    # than skip tests when it was important, we remove any files which we
    # know are safe to ignore, and run tests if there's anything left.
    changed_paths = changed_paths_from_master()
    
    interesting_changed_paths = [
        c for c in changed_paths if not _is_safe_file(c)
    ]
    
    if interesting_changed_paths:
        print(
            'Changes to the following files mean we need to run tests: %s' %
            ', '.join(interesting_changed_paths)
        )
        return True
    else:
        print('There are no changes which would need a test run.')
        return False


if __name__ == '__main__':
    if should_run_task(task=os.environ['TASK']):
        subprocess.check_call(['make', os.environ['TASK']])
