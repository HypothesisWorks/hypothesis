===================================
Extending Hypothesis with new types
===================================

You can build new strategies out of other strategies. For example:

.. code:: python

  >>> s = strategy(int).map(Decimal)
  >>> s.example()
  Decimal('6029418')

map takes a function which takes a value produced by the original strategy and
returns a new value. It returns a strategy whose values are values from the
original strategy with that function applied to them, so here we have a strategy
which produces Decimals by first generating an int and then calling Decimal on
that int.

This is generally the encouraged way to define your own strategies: The details of how SearchStrategy
works are not currently considered part of the public API and may be liable to change.

If you want to register this so that strategy works for your custom types you
can do this by extending the strategy method:

.. code:: python

  >>> @strategy.extend_static(Decimal)
  ... def decimal_strategy(d, settings):
  ...   return strategy(int, settings).map(pack=Decimal)
  >>> strategy(Decimal).example()
  Decimal('13')

You can also define types for your own custom data generation if you need something
more specific. For example here is a strategy that lets you specify the exact length
of list you want:

.. code:: python

  >>> from collections import namedtuple
  >>> ListsOfFixedLength = namedtuple('ListsOfFixedLength', ('length', 'elements'))
  >>> @strategy.extend(ListsOfFixedLength)
     ....: def fixed_length_lists_strategy(descriptor, settings):
     ....:     return strategy((descriptor.elements,) * descriptor.length, settings).map(
     ....:        pack=list)
     ....: 
  >>> strategy(ListsOfFixedLength(5, int)).example()
  [0, 2190, 899, 2, -1326]

(You don't have to use namedtuple for this, but I tend to because they're
convenient)

Hypothesis also provides a standard test suite you can use for testing strategies
you've defined.


.. code:: python

  from hypothesis.strategytests import strategy_test_suite
  TestDecimal = strategy_test_suite(Decimal)

TestDecimal is a unitest.TestCase class that will run a bunch of tests against the
strategy you've provided for Decimal to make sure it works correctly.

~~~~~~~~~~~~~~~~~~~~~
Extending a function?
~~~~~~~~~~~~~~~~~~~~~

The way this works is that Hypothesis has something that looks suspiciously
like its own object system, called ExtMethod.

It mirrors the Python object system as closely as possible and has the
same method resolution order, but allows for methods that are defined externally
to the class that uses them. This allows extensibly doing different things
based on the type of an argument without worrying about the namespacing problems
caused by MonkeyPatching.

strategy is the main ExtMethod you are likely to interact with directly, but
there are a number of others that Hypothesis uses under the hood.
