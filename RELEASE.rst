RELEASE_TYPE: patch

This release makes several changes:

1. It significantly improves Hypothesis's ability to use coverage information
   to find interesting examples.
2. It reduces the default ``max_examples`` setting to 100. This is intended to
   offset some of the performance hit of running under coverage, and the new
   algorithm is sufficiently better at covering interesting behaviour that
   reducing the number of examples should not come with a regression in ability
   to find bugs.
