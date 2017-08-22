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
import sys
import json

from hypothesis.internal.reflection import proxies

pretty_file_name_cache = {}


def pretty_file_name(f):
    try:
        return pretty_file_name_cache[f]
    except KeyError:
        pass

    parts = f.split(os.path.sep)
    parts = parts[parts.index('hypothesis'):]
    result = os.path.sep.join(parts)
    pretty_file_name_cache[f] = result
    return result


def check_function_impl(f):
    @proxies(f)
    def accept(*args, **kwargs):
        # 0 is here, 1 is the proxy function, 2 is where we were actually
        # called from.
        caller = sys._getframe(2)
        description = '%s:%d, %s passed' % (
            pretty_file_name(caller.f_code.co_filename),
            caller.f_lineno, f.__name__,
        )
        try:
            result = f(*args, **kwargs)
            record_branch(description, True)
            return result
        except:
            record_branch(description, False)
            raise
    return accept


if os.getenv('HYPOTHESIS_INTERNAL_BRANCH_CHECK') == 'true':
    log = open('branch-check', 'w')
    written = set()

    def record_branch(name, value):
        key = (name, value)
        if key in written:
            return
        written.add(key)
        log.write(
            json.dumps({'name': name, 'value': value})
        )
        log.write('\n')
        log.flush()

    check_function = check_function_impl

else:
    def record_branch(name, value):
        pass

    def check_function(f):
        return f
