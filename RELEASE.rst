RELEASE_TYPE: patch

This release makes several changes:

1. It significantly improves Hypothesis's ability to use coverage information
   to find interesting examples.
2. It reduces the default ``max_examples`` setting from 200 to 100. This takes
   advantage of the improved algorithm meaning fewer examples are typically
   needed to get the same testing and is sufficiently better at covering
   interesting behaviour, and offsets some of the performance problems of
   running under coverage.
3. Hypothesis will always try to start its testing with an example that is near
   minimized.

The new algorithm for 1 also makes some changes to Hypothesis's low level data
generation which apply even with coverage turned off. They generally reduce the
total amount of data generated, which should improve test performance somewhat.
Between this and 3 you should see a noticeable reduction in test runtime (how
much so depends on your tests and how much example size affects their
performance. On our benchmarks, where data generation dominates, we saw up to
a factor of two performance improvement, but it's unlikely to be that large.
