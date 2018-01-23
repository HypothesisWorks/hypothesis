RELEASE_TYPE: patch

This release fixes a dependency problem.  It was possible to install
Hypothesis with an old version of :pypi:`attrs`, which would throw a
``TypeError`` as soon as you tried to import hypothesis.  Specifically, you
need attrs 16.0.0 or newer.

Hypothesis will now require the correct version of attrs when installing.
