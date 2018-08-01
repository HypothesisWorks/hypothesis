RELEASE_TYPE: patch

This release adds some more internal caching to the shrinker. This should cause
a significant speed up for shrinking, especially for stateful testing and
large example sizes.
