===================================
Hypothesis for the Scientific Stack
===================================

.. _hypothesis-numpy:

-----
numpy
-----

Hypothesis offers a number of strategies for `NumPy <http://www.numpy.org/>`_ testing,
available in the :mod:`hypothesis[numpy]` :doc:`extra </extras>`.
It lives in the ``hypothesis.extra.numpy`` package.

The centerpiece is the :func:`~hypothesis.extra.numpy.arrays` strategy, which generates arrays with
any dtype, shape, and contents you can specify or give a strategy for.
To make this as useful as possible, strategies are provided to generate array
shapes and generate all kinds of fixed-size or compound dtypes.


.. automodule:: hypothesis.extra.numpy
   :members:

.. _hypothesis-pandas:

------
pandas
------

Hypothesis provides strategies for several of the core pandas data types:
:class:`pandas.Index`, :class:`pandas.Series` and :class:`pandas.DataFrame`.

The general approach taking by the pandas module is that there are multiple
strategies for generating indexes, and all of the other strategies take the
number of entries they contain from their index strategy (with sensible defaults).
So e.g. a Series is specified by specifying its :class:`numpy.dtype` (and/or
a strategy for generating elements for it).

.. automodule:: hypothesis.extra.pandas
   :members:
