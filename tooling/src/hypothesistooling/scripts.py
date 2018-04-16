# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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
import sys
import json
import shlex
import subprocess

from hypothesistooling import ROOT


def run_script(script, *args, **kwargs):
    print(script, *map(shlex.quote, args))
    return subprocess.check_call(
        [os.path.join(SCRIPTS, script), *args], **kwargs
    )


SCRIPTS = os.path.join(ROOT, 'tooling', 'scripts')


DUMP_ENVIRON = """
set -e -u

%(python)s -c 'import os; import json; print(json.dumps(dict(os.environ)))'
source %(scripts)s/common.sh
%(python)s -c 'import os; import json; print(json.dumps(dict(os.environ)))'
""" % {
    'scripts': shlex.quote(SCRIPTS),
    'python': shlex.quote(os.path.abspath(sys.executable)),
}


def __calc_script_variables():
    output = subprocess.check_output([
        'bash', '-c', DUMP_ENVIRON
    ], env={'HOME': os.environ['HOME']})

    env1, env2 = map(json.loads, output.splitlines())
    for k, v in env2.items():
        if k not in env1:
            globals()[k] = v


__calc_script_variables()


def tool_path(name):
    return os.path.join(os.path.dirname(sys.executable), name)


def pip_tool(name, *args, **kwargs):
    r = subprocess.call([tool_path(name), *args], **kwargs)

    if r != 0:
        sys.exit(r)
