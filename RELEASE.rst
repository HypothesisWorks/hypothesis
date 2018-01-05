RELEASE_TYPE: patch

This release makes the Hypothesis shrinker slightly less greedy in order to
avoid local minima - when it gets stuck, it makes a small attempt to search
around the final example it would previously have returned to find a new
starting point to shrink from. This should improve example quality in some
cases, especially ones where the test data has dependencies among parts of it
that make it difficult for Hypothesis to proceed.
