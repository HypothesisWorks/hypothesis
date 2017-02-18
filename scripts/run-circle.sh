#!/usr/bin/env bash

set -o errexit
set -o xtrace

# Only run CI if we're either on the master branch or this is a
# pull request.
if [ "$CIRCLE_BRANCH" != "master" ] && [ "$CI_PULL_REQUESTS" == "" ] ; then
  exit 0;
fi

make check-pypy
make check-py36
make check-py27
