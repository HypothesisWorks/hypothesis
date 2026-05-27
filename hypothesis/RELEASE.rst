RELEASE_TYPE: patch

This patch fixes a bug where :func:`~hypothesis.strategies.decimals` with the
``places`` argument could generate values outside the ``min_value`` and
``max_value`` bounds, when those bounds had more fractional digits than
``places`` (:issue:`4651`).
