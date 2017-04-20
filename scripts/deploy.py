#!/usr/bin/env python

import os
import sys
from time import time, sleep
import random
sys.path.append(os.path.dirname(__file__))  # noqa

import hypothesistooling as tools


if __name__ == '__main__':
    last_release = tools.latest_version()

    print("Current version: %s. Latest released version: %s" % (
        tools.__version__, last_release
    ))

    start_time = time()

    prev_pending = None

    while time() <= start_time + 60 * 60:
        jobs = tools.build_jobs()
        if jobs["failed"]:
            print("Failing this due to failure of jobs %s" % (
                ', '.join(jobs["failed"]),
            ))
            sys.exit(1)
        else:
            pending = jobs["pending"]
            pending.remove("deploy")
            if pending:
                still_pending = set(pending)
                if prev_pending is None:
                    print("Waiting for the following jobs to complete:")
                    for p in sorted(still_pending):
                        print(" * %s" % (p,))
                    print()
                else:
                    completed = prev_pending - still_pending
                    if completed:
                        print("%s completed since last check." % (
                            ', '.join(sorted(completed)),))
                prev_pending = still_pending
                naptime = 10.0 * (2 + random.random())
                print("Waiting %.2fs for %d more job%s to complete" % (
                    naptime, len(pending), "s" if len(pending) > 1 else "",))
                sleep(naptime)
            else:
                break
    else:
        print("We've been waiting for an hour. That seems bad. Failing now")
        sys.exit(1)

    if not tools.on_master():
        print("Not deploying due to not being on master")
        sys.exit(0)

    if not tools.has_source_changes(last_release):
        print("Not deploying due to no source changes")
        sys.exit(0)

    print("Looks good to release! Pushing the tag now.")
    tools.create_tag()
    sys.exit(0)
