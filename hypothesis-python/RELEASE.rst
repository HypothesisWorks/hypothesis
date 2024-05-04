RELEASE_TYPE: patch

This patch turns off a warning for functions decorated with
:func:`typing.overload` and then :func:`~hypothesis.strategies.composite`,
although only in that order (:issue:`3970`).
