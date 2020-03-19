RELEASE_TYPE: minor

This release allows the :func:`~hypothesis.extra.numpy.array_dtypes` strategy
to generate Numpy dtypes which have `field titles in addition to field names
<https://docs.scipy.org/doc/numpy/user/basics.rec.html#field-titles>`__.
We expect this to expose latent bugs where code expects that
``set(dtype.names) == set(dtype.fields)``, though the latter may include titles.
