===================================
Hypothesis for the Scientific Stack
===================================

.. _hypothesis-numpy:

-----
numpy
-----

Hypothesis offers a number of strategies for `NumPy <https://www.numpy.org/>`_ testing,
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
Supported Versions
~~~~~~~~~~~~~~~~~~

There is quite a lot of variation between pandas versions. We only
commit to supporting the latest version of pandas, but older minor versions are
supported on a "best effort" basis.  Hypothesis is currently tested against
and confirmed working with Pandas 0.19, 0.20, 0.21, 0.22, and 0.23.

Releases that are not the latest patch release of their minor version are not
tested or officially supported, but will probably also work unless you hit a
pandas bug.
