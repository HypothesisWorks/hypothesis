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
from datetime import datetime

HEADER_FILE = "scripts/header.py"

CURRENT_YEAR = datetime.utcnow().year

HEADER_SOURCE = open(HEADER_FILE).read().strip().format(year=CURRENT_YEAR)


def main():
    rootdir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.chdir(rootdir)
    files = sys.argv[1:]

    for f in files:
        print(f)
        lines = []
        with open(f, encoding="utf-8") as o:
            shebang = None
            first = True
            header_done = False
            for l in o.readlines():
                if first:
                    first = False
                    if l[:2] == '#!':
                        shebang = l
                        continue
                if 'END HEADER' in l and not header_done:
                    lines = []
                    header_done = True
                else:
                    lines.append(l)
        source = ''.join(lines).strip()
        with open(f, "w", encoding="utf-8") as o:
            if shebang is not None:
                o.write(shebang)
                o.write("\n")
            o.write(HEADER_SOURCE)
            if source:
                o.write("\n\n")
                o.write(source)
            o.write("\n")


if __name__ == '__main__':
    main()
