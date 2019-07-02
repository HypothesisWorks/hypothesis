RELEASE_TYPE: minor

This release significantly improves the performance of drawing unique collections whose
elements are drawn from  :func:`~hypothesis.strategies.sampled_from`  strategies.

As a side effect, this detects an error condition that would previously have
passed silently: When the ``min_size`` argument on a collection with distinct elements
is greater than the number of elements being sampled, this will now raise an error.
