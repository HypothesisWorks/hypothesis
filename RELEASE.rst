RELEASE_TYPE: patch

This patch relaxes constraints on the expected values returned
by the standard library function :func:`hypot` and the internal
helper function :func:`~hypotheses.internal.cathetus`, this to
fix near-exact test-failures on some 32-bit systems.
