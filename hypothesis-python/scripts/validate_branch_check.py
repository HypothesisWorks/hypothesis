# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import json
import sys
from collections import defaultdict

if __name__ == "__main__":
    with open("branch-check", encoding="utf-8") as i:
        data = [json.loads(l) for l in i]

    checks = defaultdict(set)

    for d in data:
        checks[d["name"]].add(d["value"])

    if not checks:
        print("No branches found in the branch-check file?")
        sys.exit(1)

    always_true = []
    always_false = []

    for c, vs in sorted(checks.items()):
        if len(vs) < 2:
            v = next(iter(vs))
            assert v in (False, True)
            if v:
                always_true.append(c)
            else:
                always_false.append(c)

    failure = always_true or always_false

    if failure:
        print("Some branches were not properly covered.")

    if always_true:
        print()
        print("The following were always True:")
        for c in always_true:
            print(f"  * {c}")
    if always_false:
        print()
        print("The following were always False:")
        for c in always_false:
            print(f"  * {c}")
    if failure:
        sys.exit(1)

    print(
        f"""Successfully validated {len(checks)} branch{"es" if len(checks) > 1 else ""}."""
    )
