#!/usr/bin/env python

import os
import sys

sys.path.append(os.path.dirname(__file__)) # noqa

import hypothesistooling as tools


if __name__ == '__main__':
    branch = tools.current_branch()

    if branch != "master":
        print("Not deploying due to non-master branch %s" % (branch,))
        sys.exit(1)

    last_release = tools.latest_version()

    if not tools.has_source_changes(last_release):
        print("Not deploying due to no source changes")
        sys.exit(1)

    print("Current version: %s. Latest released version: %s" % (
        tools.__version__, last_release
    ))

    print("Looks good to release! Pushing the tag now.")
    tools.create_tag()
    sys.exit(0)
