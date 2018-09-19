RELEASE_TYPE: patch

This patch allows Hypothesis to try a few more examples after finding the
first bug, in hopes of reporting multiple distinct bugs.  The heuristics
described in :issue:`847` ensure that we avoid wasting time on fruitless
searches, while still surfacing each bug as soon as possible.
For tests that don't find any bugs, there is no change at all.
