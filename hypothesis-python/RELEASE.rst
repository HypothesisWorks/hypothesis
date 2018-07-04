RELEASE_TYPE: patch

This patch fixes a rare bug where an incorrect percentage drawtime
could be displayed for a test, when the system clock was changed during
a test running under Python 2 (we use :func:`python:time.monotonic`
where it is available to avoid such problems).  It also fixes a possible
zero-division error that can occur when the underlying C library
double-rounds an intermediate value in :func:`python:math.fsum` and
gets the least significant bit wrong.
