RELEASE_TYPE: patch

This patch fixes a bug in :func:`~hypothesis.strategies.from_regex` that
caused ``from_regex("", fullmatch=True)`` to unintentionally generate non-empty
strings (:issue:`4982`).

The only strings that completely match an empty regex pattern are empty
strings.
