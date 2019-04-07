RELEASE_TYPE: patch

This patch improves the performance of unique collections such as
:func:`hypothesis.strategies.sets` when the elements are drawn from a
:func:`hypothesis.strategies.sampled_from` strategy (:issue:`1115`).
