===============
House API Style
===============

Note: Currently this guide is very specific to the *Python* version of Hypothesis.
It needs updating for the Ruby version (and, in future, other versions).

Here are some guidelines for how to write APIs so that they "feel" like
a Hypothesis API. This is particularly focused on writing new strategies, as
that's the major place where we add APIs, but also applies more generally.

Note that it is not a guide to *code* style, only API design.

The Hypothesis style evolves over time, and earlier strategies in particular
may not be consistent with this style, and we've tried some experiments
that didn't work out, so this style guide is more normative than descriptive
and existing APIs may not match it. Where relevant, backwards compatibility is
much more important than conformance to the style.

We also encourage `third-party extensions <https://hypothesis.readthedocs.io/en/latest/strategies.html>`_
to follow this style guide, for consistent and user-friendly testing APIs,
or get in touch to discuss changing it if it doesn't fit their domain.

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
* Complexity should not be pushed onto the user. An easy to use API is more
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
* Strategies should usually default to allowing generation of any example they
  can support.  The only exceptions should be cases where certain inputs would
  trigger test failures which are almost never of interest: currently just
  non-UTF8 characters in ``st.text()``, and Numpy array shapes with zero
  dimensions or sides of length zero.  In each case opting in should be trivial.

~~~~~~~~~~~~~~~~~
Argument handling
~~~~~~~~~~~~~~~~~

We have a reasonably distinctive style when it comes to handling arguments:

* Arguments must be validated to the greatest extent possible. Hypothesis
  should reject bad arguments with an InvalidArgument error, not fail with an
  internal exception.
* We make extensive use of default arguments. If an argument could reasonably
  have a default, it should.
* Exception to the above: strategies for collection types should *not* have a
  default argument for element strategies.
* Arguments which have a default value should also be keyword-only, with the
  exception of ``min_value`` and ``max_value`` (see "Argument Names" below).
* ``min_value`` and ``max_value`` should default to None for unbounded types
  such as integers, and the minimal or maximal values for bounded types such
  as datetimes.  ``floats()`` is an explicit exception to this rule due to
  special handling for infinities and not-a-number.
* Interacting arguments (e.g. arguments that must be in a particular order, or
  where at most one is valid, or where one argument restricts the valid range
  of the other) are fine, but when this happens the behaviour of defaults
  should automatically be adjusted. e.g. if the normal default of an argument
  would become invalid, the function should still do the right thing if that
  default is used.
* Where the actual default used depends on other arguments, the default parameter
  should be None.
* It's worth thinking about the order of arguments: the first one or two
  arguments are likely to be passed positionally, so try to put values there
  where this is useful and not too confusing.
* When adding arguments to strategies, think carefully about whether the user
  is likely to want that value to vary often. If so, make it a strategy instead
  of a value. In particular if it's likely to be common that they would want to
  write ``some_strategy.flatmap(lambda x: my_new_strategy(argument=x))`` then
  it should be a strategy.
* Arguments should not be "a value or a strategy for generating that value".
  If you find yourself inclined to write something like that, instead make it
  take a strategy. If a user wants to pass a value they can wrap it in a call
  to ``just``.
* If a combination of arguments make it impossible to generate anything,
  ``raise InvalidArgument`` instead of ``return nothing()``.  Returning the
  null strategy is conceptually nice, but can lead to silently dropping parts
  from composed strategies and thus unexpectedly weak tests.

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
  the first arguments. Where there is only one element strategy it should be
  called ``elements`` (but e.g. ``dictionaries`` has element strategies named
  ``keys`` and ``values`` and that's fine).
* For ordered types, the first two arguments should be a lower and an upper
  bound. They should be called ``min_value`` and ``max_value``.
* Collection types should have a ``min_size`` and a ``max_size`` parameter that
  controls the range of their size. ``min_size`` should default to zero and
  ``max_size`` to ``None`` (even if internally it is bounded).


~~~~~~~~~~~~~~~
Deferred Errors
~~~~~~~~~~~~~~~

As far as is reasonable, functions should raise errors when the test is run
(typically by deferring them until you try to draw from the strategy),
not when they are called.
This mostly applies to strategy functions and some error conditions in
``@given`` itself.

Generally speaking this should be taken care of automatically by use of the
``@defines_strategy`` decorator.

We do not currently do this for the ``TypeError`` that you will get from
calling the function incorrectly (e.g. with invalid keyword arguments or
missing required arguments).
In principle we could, but it would result in much harder to read function
signatures, so we would be trading off one form of comprehensibility for
another, and so far that hasn't seemed to be worth it.

The main reasons for preferring this style are:

* Errors at test import time tend to throw people and be correspondingly hard
  for them to debug.
  There's an expectation that errors in your test code result in failures in
  your tests, and the fact that that test code happens to be defined in a
  decorator doesn't seem to change that expectation for people.
* Things like deprecation warnings etc. localize better when they happen
  inside the test - test runners will often swallow them or put them in silly
  places if they're at import time, but will attach any output that happens
  in the test to the test itself.
* There are a lot of cases where raising an error, deprecation warning, etc.
  is *only* possible in a test - e.g. if you're using the inline style with
  `data <https://hypothesis.readthedocs.io/en/latest/data.html#drawing-interactively-in-tests>`_,
  or if you're using
  `flatmap <https://hypothesis.readthedocs.io/en/latest/data.html#chaining-strategies-together>`_
  or
  `@composite <https://hypothesis.readthedocs.io/en/latest/data.html#composite-strategies>`_
  then the strategy won't actually get evaluated until we run the test,
  so that's the only place they can happen.
  It's nice to be consistent, and it's weird if sometimes strategy errors result in
  definition time errors and sometimes they result in test errors.


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Inferring strategies from specifications
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Functions which infer a strategy from some specification or schema are both
convenient for users, and offer a single source of truth about what inputs
are allegedly valid and actually tested for correctness.

* Such functions should be named "``from_foo()``" and the first argument should
  be the thing from which a strategy is inferred - like ``st.from_type()``,
  ``st.from_regex()``, ``extra.lark.from_lark()``, ``extra.numpy.from_dtype()``,
  etc.  Any other arguments should be optional keyword-only parameters.
* There should be a smooth path to customise *parts* of an inferred strategy,
  i.e. not require the user to start from scratch if they need something a
  little more specific.  ``from_dtype()`` does this well; ``from_type()`` supports
  it by `pointing users to builds() instead <https://hypothesis.works/articles/types-and-properties/>`_.
* Where practical, ensure that the ``repr`` of the returned strategy shows
  how it was constructed - only using e.g. ``@st.composite`` if required.
  For example, ``repr(from_type(int)) == "integers()"``.


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A catalogue of current violations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following are places where we currently deviate from this style. Some of
these should be considered targets for deprecation and/or improvement.

* ``hypothesis.extra.numpy`` has some arguments which can be either
  strategies or values.
* ``hypothesis.extra.numpy`` assumes arrays are fixed size and doesn't have
  ``min_size`` and ``max_size`` arguments (but this is probably OK because of
  more complicated shapes of array).
* ``hypothesis.stateful`` is a great big subclassing based train wreck.
