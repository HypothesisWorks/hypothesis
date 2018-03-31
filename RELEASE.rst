RELEASE_TYPE: patch

This patch fixes the `~hypothesis.settings.min_satisfying_examples` settings
documentation, by explaining that example shrinking is tracked at the level
of the underlying bytestream rather than the output value.

The output from :func:`~hypothesis.find` in verbose mode has also been
adjusted - see :ref:`the example session <verbose-output>` - to avoid
duplicating lines when the example repr is constant, even if the underlying
representation has been shrunken.
