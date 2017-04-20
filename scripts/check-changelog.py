#!/usr/bin/env python

import os
import sys

sys.path.append(os.path.dirname(__file__)) # noqa

import hypothesistooling as tools
from datetime import datetime


if __name__ == '__main__':
    changelog = tools.changelog()

    if "\n%s - " % (tools.__version__,) not in changelog:
        print(
            "The current version (%s) isn't mentioned in the changelog" % (
                tools.__version__,))
        sys.exit(1)

    when = datetime.utcnow().strftime("%Y-%m-%d")

    if when not in changelog:
        print((
            "The current date (%s) isn't mentioned in the changelog. "
            "Remember this will be released as soon as you merge to master!"
        ) % (when,))
        sys.exit(1)
