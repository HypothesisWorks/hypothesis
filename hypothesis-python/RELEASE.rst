RELEASE_TYPE: patch

Fix the type signature :func:`~hypothesis.extra.numpy.arrays` to correctly reflect the type of the dtype argument in the returned strategy when dtype is a numpy.dtype object.