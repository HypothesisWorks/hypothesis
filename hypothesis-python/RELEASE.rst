RELEASE_TYPE: patch

This patch improves the internals of :func:`~hypothesis.strategies.builds` type
inference, to handle recursive forward references in certain dataclasses.
This is useful for e.g. :pypi:`hypothesmith`'s forthcoming :pypi:`LibCST` mode.
