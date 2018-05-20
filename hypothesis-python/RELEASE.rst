RELEASE_TYPE: patch

This patch uses :func:`python:random.getstate` and :func:`python:random.setstate`
to restore the PRNG state after :func:`@given <hypothesis.given>` runs
deterministic tests.  Without restoring state, you might have noticed problems
such as :issue:`1266`.  The fix also applies to stateful testing (:issue:`702`).
