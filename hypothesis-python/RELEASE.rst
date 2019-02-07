RELEASE_TYPE: patch

This release modifies the shrinker to interleave different types of reduction operations,
e.g. switching between deleting data and lowering scalar values rather than trying entirely deletions then entirely lowering.

This may slow things down somewhat in the typical case, but has the major advantage that many previously difficult to shrink examples should become much faster,
because the shrinker will no longer tend to stall when trying some ineffective changes to the shrink target but will instead interleave it with other more effective operations.
