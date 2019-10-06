RELEASE_TYPE: patch

This patch improves the performance of unique collections such as
:func:`~hypothesis.strategies.sets` of :func:`~hypothesis.strategies.just`
or :func:`~hypothesis.strategies.booleans` strategies.  They were already
pretty good though, so you're unlikely to notice much!
