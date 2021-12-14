# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Dumping ground module for things that don't have anywhere better to go.

See https://twitter.com/betsythemuffin/status/1003313844108824584
"""

import ast
import os
from contextlib import contextmanager


@contextmanager
def in_dir(d):
    prev = os.getcwd()
    try:
        os.chdir(d)
        yield
    finally:
        os.chdir(prev)


def once(fn):
    def accept():
        if accept.has_been_called:
            return
        fn()
        accept.has_been_called = True

    accept.has_been_called = False
    accept.__name__ = fn.__name__
    return accept


def unlink_if_present(path):
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def unquote_string(s):
    return ast.literal_eval(s)
