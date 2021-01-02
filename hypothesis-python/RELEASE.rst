RELEASE_TYPE: patch

This patch extends our faster special case for
:func:`~hypothesis.strategies.sampled_from` elements in unique
:func:`~hypothesis.strategies.lists` to account for chains of
``.map(...)`` and ``.filter(...)`` calls (:issue:`2036`).
