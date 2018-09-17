RELEASE_TYPE: patch

This patch fixes a rare bug that would cause a particular shrinker pass to
raise an IndexError, if a shrink improvement changed the underlying data
in an unexpected way.
