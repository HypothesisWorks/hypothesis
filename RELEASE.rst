RELEASE_TYPE: patch

This release improves the performance of
:func:`hypothesis.strategies.characters` when using ``blacklist_characters``
and :func:`hypothesis.strategies.from_regex` when using negative character
classes.

The problems this fixes were found in the course of work funded by
`Smarkets <https://smarkets.com/>`_.
