RELEASE_TYPE: patch

This release fixes  :issue:`2027`, by changing the way Hypothesis tries to generate distinct examples to be more efficient.

This may result in slightly different data distribution, and should improve generation performance in general,
but should otherwise have minimal user impact.
