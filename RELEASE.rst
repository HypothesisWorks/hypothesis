RELEASE_TYPE: patch

This patch fixes the `~hypothesis.settings.min_satisfying_examples` settings
documentation, by explaining that example shrinking is tracked at the level
of the underlying bytestream rather than the output value.
