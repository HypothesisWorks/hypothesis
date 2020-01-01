# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

import json
import sys
from collections import defaultdict

if __name__ == "__main__":
    with open("branch-check") as i:
        data = [json.loads(l) for l in i]

    checks = defaultdict(set)

    for d in data:
        checks[d["name"]].add(d["value"])

    always_true = []
    always_false = []

    for c, vs in sorted(checks.items()):
        if len(vs) < 2:
            v = list(vs)[0]
            assert v in (False, True)
            if v:
                always_true.append(c)
            else:
                always_false.append(c)

    failure = always_true or always_false

    if failure:
        print("Some branches were not properly covered.")
        print()

    if always_true:
        print("The following were always True:")
        print()
        for c in always_true:
            print("  * %s" % (c,))
    if always_false:
        print("The following were always False:")
        print()
        for c in always_false:
            print("  * %s" % (c,))
    if failure:
        sys.exit(1)
