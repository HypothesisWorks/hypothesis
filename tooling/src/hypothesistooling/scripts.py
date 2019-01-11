# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

import os
import re
import shlex
import subprocess
import sys

from hypothesistooling import ROOT


def print_command(command, args):
    args = list(args)
    ranges = []
    for i, v in enumerate(args):
        if os.path.exists(v):
            if not ranges or ranges[-1][-1] < i - 1:
                ranges.append([i, i])
            elif ranges[-1][-1] + 1 == i:
                ranges[-1][-1] += 1
    for i, j in ranges:
        if j > i:
            args[i] = "..."
            for k in range(i + 1, j + 1):
                args[k] = None
    args = [v for v in args if v is not None]
    print(command, *map(shlex.quote, args))


def run_script(script, *args, **kwargs):
    print_command(script, args)
    return subprocess.check_call([os.path.join(SCRIPTS, script), *args], **kwargs)


SCRIPTS = os.path.join(ROOT, "tooling", "scripts")
COMMON = os.path.join(SCRIPTS, "common.sh")


def __calc_script_variables():
    exports = re.compile(r"export ([A-Z_]+)(=|$)")

    with open(COMMON) as i:
        common = i.read()

    for name, _ in exports.findall(common):
        globals()[name] = os.environ[name]


__calc_script_variables()


def tool_path(name):
    return os.path.join(os.path.dirname(sys.executable), name)


def pip_tool(name, *args, **kwargs):
    print_command(name, args)
    r = subprocess.call([tool_path(name), *args], **kwargs)

    if r != 0:
        sys.exit(r)
