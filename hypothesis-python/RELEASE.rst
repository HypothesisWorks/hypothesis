RELEASE_TYPE: minor

This release adds the :func:`~hypothesis.extra.numpy.basic_indices` strategy,
to generate `basic indexes <https://docs.scipy.org/doc/numpy/reference/arrays.indexing.html>`__
for arrays of the specified shape (:issue:`1930`).

It generates tuples containing some mix of integers, :obj:`python:slice` objects,
``...`` (Ellipsis), and :obj:`numpy:numpy.newaxis`; which when used to index an array
of the specified shape produce either a scalar or a shared-memory view of the array.
Note that the index tuple may be longer or shorter than the array shape, and may
produce a view with another dimensionality again!

Thanks to Lampros Mountrakis, Ryan Soklaski, and Zac Hatfield-Dodds for their
collaboration on this surprisingly subtle strategy!
