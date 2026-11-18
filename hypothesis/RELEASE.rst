RELEASE_TYPE: patch

This patch speeds up shrinking by comparing a candidate against the current
shrink target lazily, instead of computing the sort key of every choice on
each attempt.

It also avoids a deprecation warning on import under Python 3.16.
