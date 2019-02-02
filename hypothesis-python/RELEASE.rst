RELEASE_TYPE: patch

This patch fixes a bug where :func:`~hypothesis.strategies.from_regex`
could throw an internal error if the :obj:`python:re.IGNORECASE` flag
was used (:issue:`1786`).
