RELEASE_TYPE: minor

This release allows :func:`~hypothesis.strategies.slices` to generate ``step=None``,
and fixes an off-by-one error where the ``start`` index could be equal to ``size``.
This works fine for all Python sequences and Numpy arrays, but is undefined behaviour
in the `Array API standard <https://data-apis.org/>`__ (see :pull:`3065`).
