RELEASE_TYPE: patch

This release improves the behaviour of the :func:`~hypothesis.strategies.characters` strategy
when shrinking, by changing which characters are considered smallest to prefer more "normal" ascii characters
where available.
