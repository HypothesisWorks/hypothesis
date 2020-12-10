RELEASE_TYPE: patch

This patch improves the error message if :func:`~hypothesis.strategies.builds`
is passed an :class:`~python:enum.Enum` which cannot be called without arguments,
to suggest using :func:`~hypothesis.strategies.sampled_from` (:issue:`2693`).
