.. _hypothesis-numpy:

=================================
Scientific Hypothesis (for NumPy)
=================================

Hypothesis offers a number of strategies for `NumPy <http://www.numpy.org/>`_ testing,
available in the :mod:`hypothesis[numpy]` :doc:`extra </extras>`.
It lives in the ``hypothesis.extra.numpy`` package.

The centerpiece is the ``arrays`` strategy, which generates arrays with
any dtype, shape, and contents you can specify or give a strategy for.
To make this as useful as possible, strategies are provided to generate array
shapes and generate all kinds of fixed-size or compound dtypes.


.. automodule:: hypothesis.extra.numpy
   :members: arrays, array_shapes, scalar_dtypes, boolean_dtypes, unsigned_integer_dtypes, integer_dtypes, floating_dtypes, complex_number_dtypes, datetime64_dtypes, timedelta64_dtypes, byte_string_dtypes, unicode_string_dtypes, array_dtypes, nested_dtypes
