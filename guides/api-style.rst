===============
House API Style
===============

Here are some guidelines for how to write strategies so that they "feel" like
a Hypothesis API. This is particularly focused on writing new strategies, as
that's the major place where we add APIs, but also applies more generally.

The Hypothesis style evolves over time, and earlier strategies in particular
may not be consistent with this style, and we've tried some experiments
that didn't work out, so this style guide is more normative than descriptive
and existing APIs may not match it. Where relevant, backwards compatibility is
much more important than conformance to the style.

~~~~~~~~~~~~~~~~~~
General Guidelines
~~~~~~~~~~~~~~~~~~

* When writing extras modules, consistency with Hypothesis trumps consistency
  with the library you're integrating with.
* *Absolutely no subclassing as part of the public API*
* We should not strive too hard to be pythonic, but if an API seems weird to a
  normal Python user we should see if we can come up with an API we like as
  much but is less weird.
* Code which adds a dependency on a third party package should be put in a
  hypothesis.extra module.
* Complexity should not be pushed onto the user. An easy to use API is more]
  important than a simple implementation.

~~~~~~~~~~~~~~~~~~~~~~~~~
Guidelines for strategies
~~~~~~~~~~~~~~~~~~~~~~~~~

* A strategy function should be somewhere between a recipe for how to build a
  value and a range of valid values.
* It should not include distribution hints. The arguments should only specify
  how to produce a valid value, not statistical properties of values.
* Strategies should try to paper over non-uniformity in the underlying types
  as much as possible (e.g. ``hypothesis.extra.numpy`` has a number of
  workarounds for numpy's odd behaviour around object arrays).

~~~~~~~~~~~~~~~~~
Argument handling
~~~~~~~~~~~~~~~~~

We have a reasonably distinctive style when it comes to handling arguments:

* Arguments must be validated to the greatest extent possible. Hypothesis
  should reject bad arguments with an InvalidArgument error, not fail with an
  internal exception.
* We make extensive use of default arguments. If an argument could reasonably
  have a default, it should.
* Exception to the above: Strategies for collection types should *not* have a
  default argument for element strategies.
* Interacting arguments (e.g. arguments that must be in a particular order, or
  where at most one is valid, or where one argument restricts the valid range
  of the other) are fine, but when this happens the behaviour of defaults
  should automatically be adjusted. e.g. if the normal default of an argument
  would become invalid, the function should still do the right thing if that
* It's worth thinking about the order of arguments: the first one or two
  arguments are likely to be passed positionally, so try to put values there
  where this is useful and not too confusing.
* Arguments should not be "a value or a strategy for generating that value"
  unless there is some highly compelling reason for that. Hypothesis has good
  composition mechanisms and people should use them instead of adding them on
  an ad hoc basis to individual API functions.

~~~~~~~~~~~~~~
Function Names
~~~~~~~~~~~~~~

We don't have any real consistency here. The rough approach we follow is:

* Names are `snake_case` as is standard in Python.
* Strategies for a particular type are typically named as a plural name for
  that type. Where that type has some truncated form (e.g. int, str) we use a
  longer form name.
* Other strategies have no particular common naming convention.

~~~~~~~~~~~~~~
Argument Names
~~~~~~~~~~~~~~

We should try to use the same argument names and orders across different
strategies wherever possible. In particular:

* For collection types, the element strategy (or strategies) should always be
  the first argument. It does not have a specific common name.
* For ordered types, the first two arguments should be a lower and an upper
  bound. They should be called ``min_value`` and ``max_value``.
* Collection types should have a ``min_size`` and a ``max_size`` parameter that
  controls the range of their size. ``min_size`` should default to zero and
  ``max_size`` to ``None`` (even if internally it is bounded).


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A catalogue of current violations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following are places where we currently deviate from this style. Some of
these should be considered targets for deprecation and/or improvement.

* most of the collections in ``hypothesis.strategies`` have an ``average_size``
  distribution hint.
* many of the collections in ``hypothesis.strategies`` allow a default of
  ``None`` for their elements strategy (meaning only generate empty
  collections).
* the date and time handling strategies in ``hypothesis.strategies`` has
  bound names that match the strategy name rather than being ``min_value`` and
  ``max_value``
* ``hypothesis.extra.numpy`` has a lot of arguments which can be either
  strategies or values.
* ``hypothesis.extra.numpy`` assumes arrays are fixed size and doesn't have
  ``min_size`` and ``max_size`` arguments.
* ``hypothesis.stateful`` is a great big subclassing based train wreck.
