RELEASE_TYPE: patch

This release fixes some hard to trigger bugs in Hypothesis's automata learning
code. This code is only run as part of the Hypothesis build process, and not
for user code, so this release has no user visible impact.
