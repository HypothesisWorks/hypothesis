RELEASE_TYPE: patch

This release fixes a bug in :func:`~hypothesis.strategies.recursive` which would
have meant that in practice ``max_leaves`` was treated as if it was lower than
it actually is - specifically it would be capped at the largest power of two
smaller than it. It is now handled correctly.
