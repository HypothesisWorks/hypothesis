RELEASE_TYPE: patch

This release makes several changes:

1. It significantly improves Hypothesis's ability to use coverage information
   to find interesting examples.
2. It reduces the default ``max_examples`` setting from 200 to 100. This takes
   advantage of the improved algorithm meaning fewer examples are typically
   needed to get the same testing and is sufficiently better at covering
   interesting behaviour, and offsets some of the performance problems of
   running under coverage.

The new algorithm for 1 also makes some changes to Hypothesis's low level data
generation which apply even with coverage turned off. They generally reduce the
total amount of data generated, which should improve test performance somewhat
even without the change to the number of examples run - where data generation
costs dominates you should see anything between a slight slow down or a factor
of two speed up (or something completely different if your data isn't
represented well by our benchmarking).
