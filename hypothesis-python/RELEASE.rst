RELEASE_TYPE: patch

This release improves how Hypothesis handles reducing the size of integers'
representation. This change should mostly be invisible as it's purely about
the underlying representation and not the generated value, but it may result
in some improvements to shrink performance.
