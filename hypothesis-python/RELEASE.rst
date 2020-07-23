RELEASE_TYPE: patch

This release improves the performance of the ``sample`` method on objects obtained from :func:`~hypothesis.strategies.randoms`
when ``use_true_random=False``. This should mostly only be noticeable when the sample size is a large fraction of the population size,
but may also help avoid health check failures in some other cases.
