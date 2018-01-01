RELEASE_TYPE: patch

This is a change to some internals around how Hypothesis handles avoiding
generating duplicate examples and seeking out novel regions of the search
space.

You are unlikely to see much difference as a result of it, but it fixes
a bug where an internal assertion could theoretically be triggered and has some
minor effects on the distribution of examples so could potentially find bugs
that have previously been missed.
