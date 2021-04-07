RELEASE_TYPE: patch

This patch adds a more helpful error message if you try to call
:func:`~hypothesis.strategies.sampled_from` on an :class:`~python:enum.Enum`
which has no members, but *does* have :func:`~python:dataclasses.dataclass`-style
annotations (:issue:`2923`).
