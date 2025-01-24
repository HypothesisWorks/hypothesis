RELEASE_TYPE: patch

Some Hypothesis internals now use the number of choices as a yardstick of input size, rather than the entropy consumed by those choices. We don't expect this to cause significant behavioral changes.
