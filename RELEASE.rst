RELEASE_TYPE: patch

This is a patch release for :func:`~hypothesis.strategies.from_regex`, which
had a bug in handling of the :obj:`python:re.VERBOSE` flag (:issue:`992`).
Flags are now handled correctly when parsing regex.
