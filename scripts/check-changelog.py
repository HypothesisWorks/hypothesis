#!/usr/bin/env python

import os
import sys

sys.path.append(os.path.dirname(__file__))  # noqa

import hypothesistooling as tools
from datetime import datetime, timedelta


if __name__ == '__main__':
    changelog = tools.changelog()

    if "\n%s - " % (tools.__version__,) not in changelog:
        print(
            'The current version (%s) isn\'t mentioned in the changelog' % (
                tools.__version__,))
        sys.exit(1)

    now = datetime.utcnow()

    hour = timedelta(hours=1)

    acceptable_dates = {
        d.strftime("%Y-%m-%d")
        for d in (now, now + hour, now - hour)
    }

    when = ' or '.join(sorted(acceptable_dates))

    if not any(d in changelog for d in acceptable_dates):
        print((
            'The current date (%s) isn\'t mentioned in the changelog. '
            'Remember this will be released as soon as you merge to master!'
        ) % (when,))
        sys.exit(1)
