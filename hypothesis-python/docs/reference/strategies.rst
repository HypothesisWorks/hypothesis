.. _strategies:

Strategies Reference
====================

Strategies are the way Hypothesis describes the values for |@given| to generate.  For instance, passing the strategy ``st.lists(st.integers(), min_size=1)`` to |@given| tells Hypothesis to generate lists of integers with at least one element.

This reference page lists all of Hypothesis' first-party functions which return a strategy. There are also many provided by :doc:`third-party libraries </extensions>`.  Note that we often say "strategy" when we mean "function returning a strategy"; it's usually clear from context which one we mean.

Strategies can be passed to other strategies as arguments, combined using :ref:`combinator strategies <combinators>`, or modified using |.filter|, |.map|, or |.flatmap|.

Primitives
----------

.. autofunction:: hypothesis.strategies.none
.. autofunction:: hypothesis.strategies.nothing
.. autofunction:: hypothesis.strategies.just
.. autofunction:: hypothesis.strategies.booleans

Numeric
-------

.. seealso::

  See also the separate sections for :ref:`Numpy strategies <hypothesis-numpy>`, :ref:`Pandas strategies <hypothesis-pandas>`, and :ref:`Array API strategies <array-api>`.

.. autofunction:: hypothesis.strategies.integers
.. autofunction:: hypothesis.strategies.floats
.. autofunction:: hypothesis.strategies.complex_numbers
.. autofunction:: hypothesis.strategies.decimals
.. autofunction:: hypothesis.strategies.fractions

Strings
-------

.. seealso::

  The |st.uuids| and |st.ip_addresses| strategies generate instances of :mod:`UUID <python:uuid>` and :mod:`IPAddress <python:ipaddress>` respectively. You can generate corresponding string values by using |.map|, such as ``st.uuids().map(str)``.

.. autofunction:: hypothesis.strategies.text
.. autofunction:: hypothesis.strategies.characters
.. autofunction:: hypothesis.strategies.from_regex
.. autofunction:: hypothesis.strategies.binary
.. autofunction:: hypothesis.strategies.emails

.. autofunction:: hypothesis.provisional.domains

.. warning::

  The |st.domains| strategy is provisional. Its interface may be changed in a minor release, without being subject to our :ref:`deprecation policy <deprecation-policy>`. That said, we expect it to be relatively stable.

.. autofunction:: hypothesis.provisional.urls

.. warning::

  The |st.urls| strategy is provisional. Its interface may be changed in a minor release, without being subject to our :ref:`deprecation policy <deprecation-policy>`. That said, we expect it to be relatively stable.

Collections
-----------

.. autofunction:: hypothesis.strategies.lists
.. autofunction:: hypothesis.strategies.tuples
.. autofunction:: hypothesis.strategies.sets
.. autofunction:: hypothesis.strategies.frozensets
.. autofunction:: hypothesis.strategies.dictionaries
.. autofunction:: hypothesis.strategies.fixed_dictionaries
.. autofunction:: hypothesis.strategies.iterables

Datetime
--------

.. autofunction:: hypothesis.strategies.dates
.. autofunction:: hypothesis.strategies.times
.. autofunction:: hypothesis.strategies.datetimes
.. autofunction:: hypothesis.strategies.timezones
.. autofunction:: hypothesis.strategies.timezone_keys
.. autofunction:: hypothesis.strategies.timedeltas

Recursive
---------

.. autofunction:: hypothesis.strategies.recursive
.. autofunction:: hypothesis.strategies.deferred

Random
------

.. autofunction:: hypothesis.strategies.randoms
.. autofunction:: hypothesis.strategies.random_module
.. autofunction:: hypothesis.register_random

.. _combinators:

Combinators
-----------

.. autofunction:: hypothesis.strategies.one_of
.. autofunction:: hypothesis.strategies.builds
.. autofunction:: hypothesis.strategies.composite
.. autofunction:: hypothesis.strategies.data

Typing
------

.. autofunction:: hypothesis.strategies.from_type
.. autofunction:: hypothesis.strategies.register_type_strategy

Hypothesis
----------

.. autofunction:: hypothesis.strategies.runner
.. autofunction:: hypothesis.strategies.shared

Misc
----

.. autofunction:: hypothesis.strategies.functions
.. autofunction:: hypothesis.strategies.slices
.. autofunction:: hypothesis.strategies.uuids
.. autofunction:: hypothesis.strategies.ip_addresses

.. autofunction:: hypothesis.strategies.sampled_from
.. autofunction:: hypothesis.strategies.permutations

Related
-------

.. autoclass:: hypothesis.strategies.DrawFn
.. autoclass:: hypothesis.strategies.DataObject

  .. automethod:: hypothesis.strategies.DataObject.draw

.. autoclass:: hypothesis.strategies.SearchStrategy

  .. automethod:: hypothesis.strategies.SearchStrategy.example
  .. automethod:: hypothesis.strategies.SearchStrategy.filter
  .. automethod:: hypothesis.strategies.SearchStrategy.map
  .. automethod:: hypothesis.strategies.SearchStrategy.flatmap

.. _hypothesis-numpy:

NumPy
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

Array API
---------

.. note::

  Several array libraries have more library-specific strategies, including :pypi:`Xarray <xarray>` (via their :ref:`upstream strategies <xarray:testing.hypothesis>`) and :pypi:`NumPy` (via :ref:`its Hypothesis extra <hypothesis-numpy>`). Of course, strategies in the Array API namespace can still be used to test Xarray or NumPy, just like any other array library.

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

.. _django-strategies:

Django
------

.. seealso::

  See the :ref:`Django API reference <hypothesis-django>` for documentation on testing Django with Hypothesis.

.. autofunction:: hypothesis.extra.django.from_model
.. autofunction:: hypothesis.extra.django.from_form
.. autofunction:: hypothesis.extra.django.from_field
.. autofunction:: hypothesis.extra.django.register_field_strategy

.. _hypothesis-lark:

hypothesis[lark]
----------------

.. note::

  Strategies in this module require the ``hypothesis[lark]`` :doc:`extra </extras>`, via ``pip install hypothesis[lark]``.

.. automodule:: hypothesis.extra.lark
   :members:

Example grammars, which may provide a useful starting point for your tests, can be found
`in the Lark repository <https://github.com/lark-parser/lark/tree/master/examples>`__
and in `this third-party collection <https://github.com/ligurio/lark-grammars>`__.

.. _hypothesis-pytz:

hypothesis[pytz]
----------------

.. note::

  Strategies in this module require the ``hypothesis[pytz]`` :doc:`extra </extras>`, via ``pip install hypothesis[pytz]``.

.. automodule:: hypothesis.extra.pytz
   :members:

.. _hypothesis-dateutil:

hypothesis[dateutil]
--------------------

.. note::

  Strategies in this module require the ``hypothesis[dateutil]`` :doc:`extra </extras>`, via ``pip install hypothesis[dateutil]``.

.. automodule:: hypothesis.extra.dateutil
   :members:
