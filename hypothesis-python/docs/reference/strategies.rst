.. _strategies:

Strategies
==========

Primitives
----------

.. autofunction:: hypothesis.strategies.none
.. autofunction:: hypothesis.strategies.nothing
.. autofunction:: hypothesis.strategies.just
.. autofunction:: hypothesis.strategies.booleans

Numeric
-------

.. autofunction:: hypothesis.strategies.integers
.. autofunction:: hypothesis.strategies.floats
.. autofunction:: hypothesis.strategies.complex_numbers
.. autofunction:: hypothesis.strategies.decimals
.. autofunction:: hypothesis.strategies.fractions

Text
----

.. autofunction:: hypothesis.strategies.text
.. autofunction:: hypothesis.strategies.characters
.. autofunction:: hypothesis.strategies.from_regex
.. autofunction:: hypothesis.strategies.binary
.. autofunction:: hypothesis.strategies.emails
.. autofunction:: hypothesis.strategies.uuids
.. autofunction:: hypothesis.strategies.ip_addresses

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


Combinators
-----------

.. autofunction:: hypothesis.strategies.one_of
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

.. autofunction:: hypothesis.strategies.builds
.. autofunction:: hypothesis.strategies.functions
.. autofunction:: hypothesis.strategies.slices

.. autofunction:: hypothesis.strategies.sampled_from
.. autofunction:: hypothesis.strategies.permutations



Provisional
-----------

.. automodule:: hypothesis.provisional
  :members:
  :exclude-members: DomainNameStrategy


Related
-------

.. autoclass:: hypothesis.strategies.DataObject
.. autoclass:: hypothesis.strategies.DrawFn

.. autoclass:: hypothesis.strategies.SearchStrategy

  .. automethod:: hypothesis.strategies.SearchStrategy.filter
