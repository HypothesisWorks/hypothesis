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


VALID_STARTS = (
    "# coding=utf-8",
    "#!/usr/bin/env python",
)

if __name__ == '__main__':
    import sys
    n = max(map(len, VALID_STARTS))
    bad = False
    for f in sys.argv[1:]:
        with open(f, "r", encoding="utf-8") as i:
            start = i.read(n)
            if not any(start.startswith(s) for s in VALID_STARTS):
                print(
                    "%s has incorrect start %r" % (f, start), file=sys.stderr)
                bad = True
    sys.exit(int(bad))
