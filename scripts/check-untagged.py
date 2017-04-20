#!/usr/bin/env python

import os
import sys

sys.path.append(os.path.dirname(__file__))  # noqa

import hypothesistooling as tools


if __name__ == '__main__':
    if tools.__version__ in tools.tags():
        if tools.has_source_changes(tools.__version__):
            print("Has code changes from existing released version %s" % (
                tools.__version__,
            ))
            print(
                "This means you should update src/hypothesis/version.py "
                "to a new version before merging to master. Don't forget "
                "to update the changelog too!"
            )
            sys.exit(1)
