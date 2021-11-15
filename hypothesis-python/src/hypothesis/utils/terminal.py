# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
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

import os


def guess_background_color():
    """Returns one of "dark", "light", or "unknown".

    This is basically just guessing, but better than always guessing "dark"!
    See also https://stackoverflow.com/questions/2507337/ and
    https://unix.stackexchange.com/questions/245378/
    """
    # Guessing based on the $COLORFGBG environment variable
    try:
        fg, *_, bg = os.getenv("COLORFGBG").split(";")
    except Exception:
        pass
    else:
        # 0=black, 7=light-grey, 15=white ; we don't interpret other colors
        if fg in ("7", "15") and bg == "0":
            return "dark"
        elif fg == "0" and bg in ("7", "15"):
            return "light"
    # TODO: Guessing based on the xterm control sequence
    return "unknown"
