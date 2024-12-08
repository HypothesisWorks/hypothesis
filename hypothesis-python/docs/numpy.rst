===========================
Hypothesis for data science
===========================

.. _hypothesis-numpy:

-----
numpy
-----

Hypothesis offers a number of strategies for `NumPy <https://numpy.org/>`_ testing,
available in the ``hypothesis[numpy]`` :doc:`extra </extras>`.
It lives in the ``hypothesis.extra.numpy`` package.

The centerpiece is the :func:`~hypothesis.extra.numpy.arrays` strategy, which generates arrays with
any dtype, shape, and contents you can specify or give a strategy for.
To make this as useful as possible, strategies are provided to generate array
shapes and generate all kinds of fixed-size or compound dtypes.


.. automodule:: hypothesis.extra.numpy
   :members:
   :exclude-members: ArrayStrategy, BasicIndexStrategy, BroadcastableShapes, MutuallyBroadcastableShapesStrategy

.. _hypothesis-pandas:

------
pandas
------

Hypothesis provides strategies for several of the core pandas data types:
:class:`pandas.Index`, :class:`pandas.Series` and :class:`pandas.DataFrame`.

The general approach taken by the pandas module is that there are multiple
strategies for generating indexes, and all of the other strategies take the
number of entries they contain from their index strategy (with sensible defaults).
So e.g. a Series is specified by specifying its :class:`numpy.dtype` (and/or
a strategy for generating elements for it).

.. automodule:: hypothesis.extra.pandas
   :members:

~~~~~~~~~~~~~~~~~~
Supported versions
~~~~~~~~~~~~~~~~~~

There is quite a lot of variation between pandas versions. We only
commit to supporting the latest version of pandas, but older minor versions are
supported on a "best effort" basis.  Hypothesis is currently tested against
and confirmed working with every Pandas minor version from 1.1 through to 2.2.

Releases that are not the latest patch release of their minor version are not
tested or officially supported, but will probably also work unless you hit a
pandas bug.

.. _array-api:

---------
Array API
---------

Hypothesis offers strategies for `Array API <https://data-apis.org/>`_ adopting
libraries in the ``hypothesis.extra.array_api`` package. See :issue:`3037` for
more details.  If you want to test with :pypi:`CuPy <cupy>`, :pypi:`Dask <dask>`, :pypi:`JAX <jax>`,
:pypi:`MXNet <maxnet>`, :pypi:`PyTorch <torch>`, :pypi:`TensorFlow <tensorflow>`, or :pypi:`Xarray <xarray>` -
or just :pypi:`NumPy <numpy>` - this is the extension for you!

.. autofunction:: hypothesis.extra.array_api.make_strategies_namespace

The resulting namespace contains all our familiar strategies like
:func:`~xps.arrays` and :func:`~xps.from_dtype`, but based on the Array API
standard semantics and returning objects from the ``xp`` module:

.. automodule:: xps
   :members:
        from_dtype,
        arrays,
        array_shapes,
        scalar_dtypes,
        boolean_dtypes,
        numeric_dtypes,
        real_dtypes,
        integer_dtypes,
        unsigned_integer_dtypes,
        floating_dtypes,
        complex_dtypes,
        valid_tuple_axes,
        broadcastable_shapes,
        mutually_broadcastable_shapes,
        indices,
