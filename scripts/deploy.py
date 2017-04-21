#!/usr/bin/env python

import os
import sys
import shutil
from time import time, sleep
import random
sys.path.append(os.path.dirname(__file__))  # noqa

import hypothesistooling as tools
import subprocess


DIST = os.path.join(tools.ROOT, "dist")


PENDING_STATUS = ('started', 'created')


if __name__ == '__main__':
    last_release = tools.latest_version()

    print("Current version: %s. Latest released version: %s" % (
        tools.__version__, last_release
    ))

    if not tools.on_master():
        print("Not deploying due to not being on master")
        sys.exit(0)

    if not tools.has_source_changes(last_release):
        print("Not deploying due to no source changes")
        sys.exit(0)

    start_time = time()

    prev_pending = None

    # We time out after an hour, which is a stupidly long time and it should
    # never actually take that long: A full Travis run only takes about 20-30
    # minutes! This is really just here as a guard in case something goes
    # wrong and we're not paying attention so as to not be too mean to Travis..
    while time() <= start_time + 60 * 60:
        jobs = tools.build_jobs()

        failed_jobs = [
            (k, v)
            for k, vs in jobs.items()
            if k not in PENDING_STATUS + ('passed',)
            for v in vs
        ]

        if failed_jobs:
            print("Failing this due to failure of jobs %s" % (
                ', '.join("%s(%s)" % (s, j) for j, s in failed_jobs),
            ))
            sys.exit(1)
        else:
            pending = [j for s in PENDING_STATUS for j in jobs.get(s, ())]
            try:
                # This allows us to test the deploy job for a build locally.
                pending.remove("deploy")
            except ValueError:
                pass
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
        print("We've been waiting for an hour. That seems bad. Failing now.")
        sys.exit(1)

    print("Looks good to release!")

    if os.path.exists(DIST):
        shutil.rmtree(DIST)

    print("Now uploading to pypi.")

    subprocess.check_output([
        sys.executable, "setup.py", "sdist", "--dist-dir", DIST,
    ])

    subprocess.check_output([
        sys.executable, "-m", "twine", "--config-file=./.pypirc",
        "upload", os.path.join(DIST, "*"),
    ])

    print("Release seems good. Pushing the tag now.")

    tools.create_tag()
    sys.exit(0)
