API Reference
=============

Reference for non-strategy objects that are part of the Hypothesis API. For documentation on strategies, see the :doc:`strategies reference </reference/strategies>`.

|@given|
--------

.. autofunction:: hypothesis.given

.. data:: hypothesis.infer

Arguments to |@given|
~~~~~~~~~~~~~~~~~~~~~

The |@given| decorator may be used to specify which arguments of a function should be parametrized over. You can use either positional or keyword arguments, but not a mixture of both.

For example, all of the following are valid uses:

.. code:: python

  @given(integers(), integers())
  def a(x, y):
      pass

  @given(integers())
  def b(x, y):
      pass

  @given(y=integers())
  def c(x, y):
      pass

  @given(x=integers())
  def d(x, y):
      pass

  @given(x=integers(), y=integers())
  def e(x, **kwargs):
      pass

  @given(x=integers(), y=integers())
  def f(x, *args, **kwargs):
      pass

  class SomeTest(TestCase):
      @given(integers())
      def test_a_thing(self, x):
          pass

The following are not:

.. code:: python

  @given(integers(), integers(), integers())
  def g(x, y):
      pass

  @given(integers())
  def h(x, *args):
      pass

  @given(integers(), x=integers())
  def i(x, y):
      pass

  @given()
  def j(x, y):
      pass

The rules for determining what are valid uses of ``given`` are as follows:

1. You may pass any keyword argument to ``given``.
2. Positional arguments to ``given`` are equivalent to the rightmost named arguments for the test function.
3. Positional arguments may not be used if the underlying test function has ``*args``, ``**kwargs``, or keyword-only arguments.
4. Functions tested with ``given`` may not have any defaults.

The reason for the "rightmost named arguments" behaviour is so that using |@given| with instance methods works: ``self`` will be passed to the function as normal and not be parametrized over.

The function returned by given has all the same arguments as the original test, minus those that are filled in by |@given|. Check :ref:`the notes on framework compatibility <framework-compatibility>` to see how this affects other testing libraries you may be using.

Inferred strategies
~~~~~~~~~~~~~~~~~~~

In some cases, Hypothesis can work out what to do when you omit arguments. This is based on introspection, *not* magic, and therefore has well-defined limits.

|st.builds| will check the signature of the ``target`` (using :func:`python:inspect.signature`). If there are required arguments with type annotations and
no strategy was passed to |st.builds|, |st.from_type| is used to fill them in. You can also pass the value ``...`` (``Ellipsis``) as a keyword argument, to force this inference for arguments with a default value.

.. code-block:: pycon

    >>> def func(a: int, b: str):
    ...     return [a, b]
    ...
    >>> builds(func).example()
    [-6993, '']

|@given| does not perform any implicit inference for required arguments, as this would break compatibility with pytest fixtures. ``...`` (:obj:`python:Ellipsis`), can be used as a keyword argument to explicitly fill in an argument from its type annotation.  You can also use the :obj:`hypothesis.infer` alias if writing a literal ``...`` seems too weird.

.. code:: python

    @given(a=...)  # or @given(a=infer)
    def test(a: int):
        pass

    # is equivalent to
    @given(a=from_type(int))
    def test(a):
        pass

``@given(...)`` can also be specified to fill all arguments from their type annotations.

.. code:: python

    @given(...)
    def test(a: int, b: str):
        pass

    # is equivalent to
    @given(a=..., b=...)
    def test(a, b):
        pass

Limitations
^^^^^^^^^^^

Hypothesis does not inspect :pep:`484` type comments at runtime. While |st.from_type| will work as usual, inference in |st.builds| and |@given| will only work if you manually create the ``__annotations__`` attribute (e.g. by using ``@annotations(...)`` and ``@returns(...)`` decorators).

The :mod:`python:typing` module changes between different Python releases, including at minor versions.  These are all supported on a best-effort basis, but you may encounter problems.  Please report them to us, and consider updating to a newer version of Python as a workaround.


.. _providing-explicit-examples:

|@example|
----------

The simplest way to reproduce a failed test is to ask Hypothesis to run the
failing example it printed.  For example, if ``Falsifying example: test(n=1)``
was printed you can decorate ``test`` with ``@example(n=1)``.

``@example`` can also be used to ensure a specific example is *always* executed
as a regression test or to cover some edge case - basically combining a
Hypothesis test and a traditional parametrized test.

.. autoclass:: hypothesis.example

Hypothesis will run all examples you've asked for first. If any of them fail it
will not go on to look for more examples.

It doesn't matter whether you put the example decorator before or after given.
Any permutation of the decorators in the above will do the same thing.

Note that examples can be positional or keyword based. If they're positional then
they will be filled in from the right when calling, so either of the following
styles will work as expected:

.. code:: python

  @given(text())
  @example("Hello world")
  @example(x="Some very long string")
  def test_some_code(x):
      pass

  from unittest import TestCase

  class TestThings(TestCase):
      @given(text())
      @example("Hello world")
      @example(x="Some very long string")
      def test_some_code(self, x):
          pass

As with |@given|, it is not permitted for a single example to be a mix of
positional and keyword arguments.

.. automethod:: hypothesis.example.xfail

.. automethod:: hypothesis.example.via


Control
-------

Functions that can be called from anywhere inside a test, to either modify how Hypothesis treats the current test case, or to give Hypothesis more information about the current test case.

.. autofunction:: hypothesis.assume

.. autofunction:: hypothesis.note

.. autofunction:: hypothesis.event

You can mark custom events in a test using |event|:

.. code:: python

  from hypothesis import event, given, strategies as st

  @given(st.integers().filter(lambda x: x % 2 == 0))
  def test_even_integers(i):
      event(f"i mod 3 = {i%3}")

These events appear in :ref:`observability <observability>` output, as well as the output of :ref:`our pytest plugin <pytest-plugin>` when run with ``--hypothesis-show-statistics``.

For instance, in the latter case, you would see output like:

.. code-block:: none

  test_even_integers:

    - during generate phase (0.09 seconds):
        - Typical runtimes: < 1ms, ~ 59% in data generation
        - 100 passing examples, 0 failing examples, 32 invalid examples
        - Events:
          * 54.55%, Retried draw from integers().filter(lambda x: x % 2 == 0) to satisfy filter
          * 31.06%, i mod 3 = 2
          * 28.79%, i mod 3 = 0
          * 24.24%, Aborted test because unable to satisfy integers().filter(lambda x: x % 2 == 0)
          * 15.91%, i mod 3 = 1
    - Stopped because settings.max_examples=100

Arguments to ``event`` can be any hashable type, but two events will be considered the same
if they are the same when converted to a string with :obj:`python:str`.

.. _targeted:

Targeted property-based testing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Targeted property-based testing combines the advantages of both search-based and property-based testing.  Instead of being completely random, targeted PBT uses a search-based component to guide the input generation towards values that have a higher probability of falsifying a property.  This explores the input space more effectively and requires fewer tests to find a bug or achieve a high confidence in the system being tested than random PBT. (`Löscher and Sagonas <http://proper.softlab.ntua.gr/Publications.html>`__)

This is not *always* a good idea - for example calculating the search metric might take time better spent running more uniformly-random test cases, or your target metric might accidentally lead Hypothesis *away* from bugs - but if there is a natural metric like "floating-point error", "load factor" or "queue length", we encourage you to experiment with targeted testing.

.. code-block:: python

  from hypothesis import given, strategies as st, target

  @given(st.floats(0, 1e100), st.floats(0, 1e100), st.floats(0, 1e100))
  def test_associativity_with_target(a, b, c):
      ab_c = (a + b) + c
      a_bc = a + (b + c)
      difference = abs(ab_c - a_bc)
      target(difference)  # Without this, the test almost always passes
      assert difference < 2.0

.. autofunction:: hypothesis.target

We recommend that users also skim the papers introducing targeted PBT; from `ISSTA 2017 <http://proper.softlab.ntua.gr/papers/issta2017.pdf>`__ and `ICST 2018 <http://proper.softlab.ntua.gr/papers/icst2018.pdf>`__. For the curious, the initial implementation in Hypothesis uses hill-climbing search via a mutating fuzzer, with some tactics inspired by simulated annealing to avoid getting stuck and endlessly mutating a local maximum.



Settings
--------

.. autoclass:: hypothesis.settings
    :members:
    :exclude-members: register_profile, get_profile, load_profile

.. autoclass:: hypothesis.Phase
    :members:

.. autoclass:: hypothesis.Verbosity
    :members:

Building settings objects
~~~~~~~~~~~~~~~~~~~~~~~~~

Settings can be created by calling :class:`~hypothesis.settings` with any of the available settings
values. Any absent ones will be set to defaults:

.. code-block:: pycon

    >>> from hypothesis import settings
    >>> settings().max_examples
    100
    >>> settings(max_examples=10).max_examples
    10

You can also pass a 'parent' settings object as the first argument,
and any settings you do not specify as keyword arguments will be
copied from the parent settings:

.. code-block:: pycon

    >>> parent = settings(max_examples=10)
    >>> child = settings(parent, deadline=None)
    >>> parent.max_examples == child.max_examples == 10
    True
    >>> parent.deadline
    200
    >>> child.deadline is None
    True

Default settings
~~~~~~~~~~~~~~~~

At any given point in your program there is a current default settings,
available as ``settings.default``. As well as being a settings object in its own
right, all newly created settings objects which are not explicitly based off
another settings are based off the default, so will inherit any values that are
not explicitly set from it.

You can change the defaults by using profiles.

.. _settings_profiles:

Settings profiles
~~~~~~~~~~~~~~~~~

Depending on your environment you may want different default settings.
For example: during development you may want to lower the number of examples
to speed up the tests. However, in a CI environment you may want more examples
so you are more likely to find bugs.

Hypothesis allows you to define different settings profiles. These profiles
can be loaded at any time.

.. automethod:: hypothesis.settings.register_profile
.. automethod:: hypothesis.settings.get_profile
.. automethod:: hypothesis.settings.load_profile

Loading a profile changes the default settings but will not change the behaviour
of tests that explicitly change the settings.

.. code-block:: pycon

    >>> from hypothesis import settings
    >>> settings.register_profile("ci", max_examples=1000)
    >>> settings().max_examples
    100
    >>> settings.load_profile("ci")
    >>> settings().max_examples
    1000

Instead of loading the profile and overriding the defaults you can retrieve profiles for
specific tests.

.. code-block:: pycon

    >>> settings.get_profile("ci").max_examples
    1000

Optionally, you may define the environment variable to load a profile for you.
This is the suggested pattern for running your tests on CI.
The code below should run in a ``conftest.py`` or any setup/initialization section of your test suite.
If this variable is not defined the Hypothesis defined defaults will be loaded.

.. code-block:: pycon

    >>> import os
    >>> from hypothesis import settings, Verbosity
    >>> settings.register_profile("ci", max_examples=1000)
    >>> settings.register_profile("dev", max_examples=10)
    >>> settings.register_profile("debug", max_examples=10, verbosity=Verbosity.verbose)
    >>> settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))

If you are using the hypothesis pytest plugin and your profiles are registered
by your conftest you can load one with the command line option ``--hypothesis-profile``.

.. code:: bash

    $ pytest tests --hypothesis-profile <profile-name>


Hypothesis comes with two built-in profiles, ``ci`` and ``default``.
``ci`` is set up to have good defaults for running in a CI environment, so emphasizes determinism, while the
``default`` settings are picked to be more likely to find bugs and to have a good workflow when used for local development.

Hypothesis will automatically detect certain common CI environments and use the ci profile automatically
when running in them.
In particular, if you wish to use the ``ci`` profile, setting the ``CI`` environment variable will do this.

This will still be the case if you register your own ci profile. For example, if you wanted to run more examples in CI, you might configure it as follows:

.. code-block:: python

    settings.register_profile(
        "ci",
        settings(
            settings.get_profile("ci"),
            max_examples=1000,
        ),
    )

This will configure your CI to run 1000 examples per test rather than the default of 100, and this change will automatically be picked up when running on a CI server.

.. _healthchecks:

Health checks
~~~~~~~~~~~~~

Hypothesis' health checks are designed to detect and warn you about performance
problems where your tests are slow, inefficient, or generating very large examples.

If this is expected, e.g. when generating large arrays or dataframes, you can selectively
disable them with the :obj:`~hypothesis.settings.suppress_health_check` setting.
The argument for this parameter is a list with elements drawn from any of
the class-level attributes of the HealthCheck class.
Using a value of ``list(HealthCheck)`` will disable all health checks.

.. autoclass:: hypothesis.HealthCheck
   :undoc-members:
   :inherited-members:
   :exclude-members: all


.. _database:

Database
--------

When Hypothesis finds a bug, it stores enough information in its database to reproduce it. The next
time the test is run, Hypothesis will start by trying the stored example that failed last time.

The database is best thought of as a cache that you never need to invalidate. Entries may be
transparently dropped when upgrading your Hypothesis version or changing your test. You shouldn't
rely on the database for correctness; to ensure Hypothesis always tries an example, use |@example|.

Hypothesis is designed so that arbitrary data can be placed in the database without causing incorrect
behavior. It can never be the case that changing the strategy for a test gives you incorrect stored
data from the previous strategy, for instance.

ExampleDatabase implementations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: hypothesis.database.ExampleDatabase
    :members:
    :private-members: _broadcast_change, _start_listening, _stop_listening

.. autoclass:: hypothesis.database.InMemoryExampleDatabase
.. autoclass:: hypothesis.database.DirectoryBasedExampleDatabase
.. autoclass:: hypothesis.database.GitHubArtifactDatabase
.. autoclass:: hypothesis.database.ReadOnlyDatabase
.. autoclass:: hypothesis.database.MultiplexedDatabase
.. autoclass:: hypothesis.database.BackgroundWriteDatabase
.. autoclass:: hypothesis.extra.redis.RedisExampleDatabase

.. _custom-database:

Implementing your own database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To define your own |ExampleDatabase| class, implement the |ExampleDatabase.save|, |ExampleDatabase.fetch|, and |ExampleDatabase.delete| methods.

For example, here's a simple database class that uses :mod:`sqlite <sqlite3>` as the backing data store:

.. code-block:: python

    import sqlite3
    from collections.abc import Iterable

    from hypothesis.database import ExampleDatabase

    class SQLiteExampleDatabase(ExampleDatabase):
        def __init__(self, db_path: str):
            self.conn = sqlite3.connect(db_path)

            self.conn.execute(
                """
                CREATE TABLE examples (
                    key BLOB,
                    value BLOB,
                    UNIQUE (key, value)
                )
            """
            )

        def save(self, key: bytes, value: bytes) -> None:
            self.conn.execute(
                "INSERT OR IGNORE INTO examples VALUES (?, ?)",
                (key, value),
            )

        def fetch(self, key: bytes) -> Iterable[bytes]:
            cursor = self.conn.execute("SELECT value FROM examples WHERE key = ?", (key,))
            yield from [value[0] for value in cursor.fetchall()]

        def delete(self, key: bytes, value: bytes) -> None:
            self.conn.execute(
                "DELETE FROM examples WHERE key = ? AND value = ?",
                (key, value),
            )

Database classes are not required to implement |ExampleDatabase.move|. The default implementation of a move is a |ExampleDatabase.delete| of the value in the old key, followed by a |ExampleDatabase.save| of the value in the new key. You can override |ExampleDatabase.move| in a database class to override this behavior, if for instance the backing store offers a more efficient move implementation.

Change listening
^^^^^^^^^^^^^^^^

To support change listening in a database class, you should call ``self._broadcast_change(event)`` whenever a value is saved, deleted, or moved in the backing database store. How you track this depends on the details of the database class. For instance, in |DirectoryBasedExampleDatabase|, Hypothesis installs a filesystem monitor via :pypi:`watchdog` in order to broadcast change events.

Two related useful methods are ``ExampleDatabase._start_listening`` and ``ExampleDatabase._stop_listening``, which a database class can override to know when to start or stop expensive listening operations. See source code for documentation.

.. _stateful:

Stateful tests
--------------

.. autoclass:: hypothesis.stateful.RuleBasedStateMachine

Rules
~~~~~

.. autofunction:: hypothesis.stateful.rule

.. autofunction:: hypothesis.stateful.consumes

.. autofunction:: hypothesis.stateful.multiple

.. autoclass:: hypothesis.stateful.Bundle

.. autofunction:: hypothesis.stateful.initialize

.. autofunction:: hypothesis.stateful.precondition

.. autofunction:: hypothesis.stateful.invariant

Running state machines
~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: hypothesis.stateful.run_state_machine_as_test

If you want to bypass the TestCase infrastructure you can invoke these manually. The stateful module exposes the function ``run_state_machine_as_test``, which takes an arbitrary function returning a RuleBasedStateMachine and an optional settings parameter and does the same as the class based runTest provided.


.. _reproducing-failures:

Reproducing failures
--------------------

One of the things that is often concerning for people using randomized testing
is the question of how to reproduce failing test cases. Hypothesis has a number of features to support this. The one you
will use most commonly when developing locally is :ref:`the example database <database>`,
which means that you shouldn't have to think about the problem at all for local
use - test failures will just automatically reproduce without you having to do
anything.

The example database is perfectly suitable for sharing between machines, but
there currently aren't very good work flows for that, so Hypothesis provides a
number of ways to make examples reproducible by adding them to the source code
of your tests. This is particularly useful when e.g. you are trying to run an
example that has failed on your CI, or otherwise share them between machines.

.. _reproducing-with-seed:

Reproducing a test run with ``@seed``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: hypothesis.seed

When a test fails unexpectedly, usually due to a health check failure,
Hypothesis will print out a seed that led to that failure, if the test is not
already running with a fixed seed. You can then recreate that failure using either
the ``@seed`` decorator or (if you are running :pypi:`pytest`) with
``--hypothesis-seed``.  For example, the following test function and
:class:`~hypothesis.stateful.RuleBasedStateMachine` will each check the
same examples each time they are executed, thanks to ``@seed()``:

.. code-block:: python

    @seed(1234)
    @given(x=...)
    def test(x): ...

    @seed(6789)
    class MyModel(RuleBasedStateMachine): ...

The seed will not be printed if you could simply use ``@example`` instead.

.. _reproduce_failure:

Reproducing an example with ``@reproduce_failure``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Hypothesis has an opaque binary representation that it uses for all examples it
generates. This representation is not intended to be stable across versions or
with respect to changes in the test, but can be used to to reproduce failures
with the ``@reproduce_failure`` decorator.

.. autofunction:: hypothesis.reproduce_failure

The intent is that you should never write this decorator by hand, but it is
instead provided by Hypothesis.
When a test fails with a falsifying example, Hypothesis may print out a
suggestion to use ``@reproduce_failure`` on the test to recreate the problem
as follows:

.. code-block:: pycon

    >>> from hypothesis import settings, given, PrintSettings
    >>> import hypothesis.strategies as st
    >>> @given(st.floats())
    ... @settings(print_blob=True)
    ... def test(f):
    ...     assert f == f
    ...
    >>> try:
    ...     test()
    ... except AssertionError:
    ...     pass
    ...
    Falsifying example: test(f=nan)

    You can reproduce this example by temporarily adding @reproduce_failure(..., b'AAAA//AAAAAAAAEA') as a decorator on your test case

Adding the suggested decorator to the test should reproduce the failure (as
long as everything else is the same - changing the versions of Python or
anything else involved, might of course affect the behaviour of the test! Note
that changing the version of Hypothesis will result in a different error -
each ``@reproduce_failure`` invocation is specific to a Hypothesis version).

By default these messages are not printed.
If you want to see these you can set the :attr:`~hypothesis.settings.print_blob` setting to ``True``.


.. _hypothesis-django:

Django
------

.. seealso::

    See the :ref:`Django strategies reference <django-strategies>` for documentation on strategies in the ``hypothesis.extra.django`` module.

Hypothesis offers a number of features specific for Django testing, available
in the ``hypothesis[django]`` :doc:`extra </extras>`.  This is tested
against each supported series with mainstream or extended support -
if you're still getting security patches, you can test with Hypothesis.

.. autoclass:: hypothesis.extra.django.TestCase

Using it is quite straightforward: All you need to do is subclass
:class:`hypothesis.extra.django.TestCase` or
:class:`hypothesis.extra.django.TransactionTestCase` or
:class:`~hypothesis.extra.django.LiveServerTestCase` or
:class:`~hypothesis.extra.django.StaticLiveServerTestCase`
and you can use :func:`@given <hypothesis.given>` as normal,
and the transactions will be per example
rather than per test function as they would be if you used :func:`@given <hypothesis.given>` with a normal
django test suite (this is important because your test function will be called
multiple times and you don't want them to interfere with each other). Test cases
on these classes that do not use
:func:`@given <hypothesis.given>` will be run as normal for :class:`django:django.test.TestCase` or :class:`django:django.test.TransactionTestCase`.

.. autoclass:: hypothesis.extra.django.TransactionTestCase
.. autoclass:: hypothesis.extra.django.LiveServerTestCase
.. autoclass:: hypothesis.extra.django.StaticLiveServerTestCase

We recommend avoiding :class:`~hypothesis.extra.django.TransactionTestCase`
unless you really have to run each test case in a database transaction.
Because Hypothesis runs this in a loop, the performance problems :class:`django:django.test.TransactionTestCase` normally has
are significantly exacerbated and your tests will be really slow.
If you are using :class:`~hypothesis.extra.django.TransactionTestCase`,
you may need to use ``@settings(suppress_health_check=[HealthCheck.too_slow])``
to avoid :ref:`errors due to slow example generation <healthchecks>`.

Having set up a test class, you can now pass :func:`@given <hypothesis.given>`
a strategy for Django models with |django.from_model|.
For example, using :gh-file:`the trivial django project we have for testing
<hypothesis-python/tests/django/toystore/models.py>`:

.. code-block:: pycon

    >>> from hypothesis.extra.django import from_model
    >>> from toystore.models import Customer
    >>> c = from_model(Customer).example()
    >>> c
    <Customer: Customer object>
    >>> c.email
    'jaime.urbina@gmail.com'
    >>> c.name
    '\U00109d3d\U000e07be\U000165f8\U0003fabf\U000c12cd\U000f1910\U00059f12\U000519b0\U0003fabf\U000f1910\U000423fb\U000423fb\U00059f12\U000e07be\U000c12cd\U000e07be\U000519b0\U000165f8\U0003fabf\U0007bc31'
    >>> c.age
    -873375803

Hypothesis has just created this with whatever the relevant type of data is.

Obviously the customer's age is implausible, which is only possible because
we have not used (eg) :class:`~django:django.core.validators.MinValueValidator`
to set the valid range for this field (or used a
:class:`~django:django.db.models.PositiveSmallIntegerField`, which would only
need a maximum value validator).

If you *do* have validators attached, Hypothesis will only generate examples
that pass validation.  Sometimes that will mean that we fail a
:class:`~hypothesis.HealthCheck` because of the filtering, so let's explicitly
pass a strategy to skip validation at the strategy level:

.. code-block:: pycon

    >>> from hypothesis.strategies import integers
    >>> c = from_model(Customer, age=integers(min_value=0, max_value=120)).example()
    >>> c
    <Customer: Customer object>
    >>> c.age
    5

Custom field types
~~~~~~~~~~~~~~~~~~

If you have a custom Django field type you can register it with Hypothesis's
model deriving functionality by registering a default strategy for it:

.. code-block:: pycon

    >>> from toystore.models import CustomishField, Customish
    >>> from_model(Customish).example()
    hypothesis.errors.InvalidArgument: Missing arguments for mandatory field
        customish for model Customish
    >>> from hypothesis.extra.django import register_field_strategy
    >>> from hypothesis.strategies import just
    >>> register_field_strategy(CustomishField, just("hi"))
    >>> x = from_model(Customish).example()
    >>> x.customish
    'hi'

Note that this mapping is on exact type. Subtypes will not inherit it.

Generating child models
~~~~~~~~~~~~~~~~~~~~~~~

For the moment there's no explicit support in hypothesis-django for generating
dependent models. i.e. a Company model will generate no Shops. However if you
want to generate some dependent models as well, you can emulate this by using
the |.flatmap| function as follows:

.. code:: python

  from hypothesis.strategies import just, lists

  def generate_with_shops(company):
      return lists(from_model(Shop, company=just(company))).map(lambda _: company)

  company_with_shops_strategy = from_model(Company).flatmap(generate_with_shops)

Let's unpack what this is doing:

The way flatmap works is that we draw a value from the original strategy, then
apply a function to it which gives us a new strategy. We then draw a value from
*that* strategy. So in this case we're first drawing a company, and then we're
drawing a list of shops belonging to that company: The |st.just| strategy is a
strategy such that drawing it always produces the individual value, so
``from_model(Shop, company=just(company))`` is a strategy that generates a Shop belonging
to the original company.

So the following code would give us a list of shops all belonging to the same
company:

.. code:: python

  from_model(Company).flatmap(lambda c: lists(from_model(Shop, company=just(c))))

The only difference from this and the above is that we want the company, not
the shops. This is where the inner map comes in. We build the list of shops
and then throw it away, instead returning the company we started for. This
works because the models that Hypothesis generates are saved in the database,
so we're essentially running the inner strategy purely for the side effect of
creating those children in the database.


.. _django-generating-primary-key:

Generating primary key values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your model includes a custom primary key that you want to generate
using a strategy (rather than a default auto-increment primary key)
then Hypothesis has to deal with the possibility of a duplicate
primary key.

If a model strategy generates a value for the primary key field,
Hypothesis will create the model instance with
:meth:`~django:django.db.models.query.QuerySet.update_or_create`,
overwriting any existing instance in the database for this test case
with the same primary key.


On the subject of ``MultiValueField``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Django forms feature the :class:`~django:django.forms.MultiValueField`
which allows for several fields to be combined under a single named field, the
default example of this is the :class:`~django:django.forms.SplitDateTimeField`.

.. code:: python

  class CustomerForm(forms.Form):
      name = forms.CharField()
      birth_date_time = forms.SplitDateTimeField()

|django.from_form| supports ``MultiValueField`` subclasses directly, however if you
want to define your own strategy be forewarned that Django binds data for a
``MultiValueField`` in a peculiar way. Specifically each sub-field is expected
to have its own entry in ``data`` addressed by the field name
(e.g. ``birth_date_time``) and the index of the sub-field within the
``MultiValueField``, so form ``data`` for the example above might look
like this:

.. code:: python

  {
      "name": "Samuel John",
      "birth_date_time_0": "2018-05-19",  # the date, as the first sub-field
      "birth_date_time_1": "15:18:00",  # the time, as the second sub-field
  }

Thus, if you want to define your own strategies for such a field you must
address your sub-fields appropriately:

.. code:: python

  from_form(CustomerForm, birth_date_time_0=just("2018-05-19"))

.. _fuzz_one_input:

Use with external fuzzers
-------------------------

.. tip::

    | Want an integrated workflow for your team's local tests, CI, and continuous fuzzing?
    | Use `HypoFuzz <https://hypofuzz.com/>`__ to fuzz your whole test suite, and find more bugs without more tests!

Sometimes, you might want to point a traditional fuzzer such as `python-afl <https://github.com/jwilk/python-afl>`__, :pypi:`pythonfuzz`, or Google's :pypi:`atheris` (for Python *and* native extensions) at your code. Wouldn't it be nice if you could use any of your |@given| tests as fuzz targets, instead of converting bytestrings into your objects by hand?

.. code:: python

    @given(st.text())
    def test_foo(s): ...

    # This is a traditional fuzz target - call it with a bytestring,
    # or a binary IO object, and it runs the test once.
    fuzz_target = test_foo.hypothesis.fuzz_one_input

    # For example:
    fuzz_target(b"\x00\x00\x00\x00\x00\x00\x00\x00")
    fuzz_target(io.BytesIO(...))

Depending on the input to ``fuzz_one_input``, one of three things will happen:

- If the bytestring was invalid, for example because it was too short or
  failed a filter or :func:`~hypothesis.assume` too many times,
  ``fuzz_one_input`` returns ``None``.

- If the bytestring was valid and the test passed, ``fuzz_one_input`` returns a canonicalised and pruned buffer which will replay that test case.  This is provided as an option to improve the performance of mutating fuzzers, but can safely be ignored.

- If the test *failed*, i.e. raised an exception, ``fuzz_one_input`` will add the pruned buffer to :ref:`the Hypothesis example database <database>` and then re-raise that exception.  All you need to do to reproduce, minimize, and de-duplicate all the failures found via fuzzing is run your test suite!

Note that the interpretation of both input and output bytestrings is specific to the exact version of Hypothesis you are using and the strategies given to the test, just like the :ref:`example database <database>` and :func:`@reproduce_failure <hypothesis.reproduce_failure>` decorator.

.. tip::

  For usages of ``fuzz_one_input`` which expect to discover many failures, consider wrapping your database with :class:`~hypothesis.database.BackgroundWriteDatabase` for low-overhead writes of failures.

Interaction with settings
~~~~~~~~~~~~~~~~~~~~~~~~~

``fuzz_one_input`` uses just enough of Hypothesis' internals to drive your test function with a fuzzer-provided bytestring, and most settings therefore have no effect in this mode.  We recommend running your tests the usual way before fuzzing to get the benefits of healthchecks, as well as afterwards to replay, shrink, deduplicate, and report whatever errors were discovered.

- The :obj:`~hypothesis.settings.database` setting *is* used by fuzzing mode - adding failures to the database to be replayed when you next run your tests is our preferred reporting mechanism and response to `the 'fuzzer taming' problem <https://blog.regehr.org/archives/925>`__.
- The :obj:`~hypothesis.settings.verbosity` and :obj:`~hypothesis.settings.stateful_step_count` settings work as usual.

The |settings.deadline|, |settings.derandomize|, |settings.max_examples|, |settings.phases|, |settings.print_blob|, |settings.report_multiple_bugs|, and |settings.suppress_health_check| settings do not affect fuzzing mode.


.. _custom-function-execution:

Custom function execution
-------------------------

Hypothesis provides you with a hook that lets you control how it runs examples.

This lets you do things like set up and tear down around each example, run examples in a subprocess, transform coroutine tests into normal tests, etc. For example, :class:`~hypothesis.extra.django.TransactionTestCase` in the Django extra runs each example in a separate database transaction.

The way this works is by introducing the concept of an executor. An executor is essentially a function that takes a block of code and run it. The default executor is:

.. code:: python

    def default_executor(function):
        return function()

You define executors by defining a method ``execute_example`` on a class. Any test methods on that class with :func:`@given <hypothesis.given>` used on them will use ``self.execute_example`` as an executor with which to run tests. For example, the following executor runs all its code twice:

.. code:: python

    from unittest import TestCase

    class TestTryReallyHard(TestCase):
        @given(integers())
        def test_something(self, i):
            perform_some_unreliable_operation(i)

        def execute_example(self, f):
            f()
            return f()

Note: The functions you use in map, etc. will run *inside* the executor. i.e. they will not be called until you invoke the function passed to ``execute_example``.

An executor must be able to handle being passed a function which returns None, otherwise it won't be able to run normal test cases. So for example the following executor is invalid:

.. code:: python

    from unittest import TestCase

    class TestRunTwice(TestCase):
        def execute_example(self, f):
            return f()()

and should be rewritten as:

.. code:: python

    from unittest import TestCase

    class TestRunTwice(TestCase):
        def execute_example(self, f):
            result = f()
            if callable(result):
                result = result()
            return result

An alternative hook is provided for use by test runner extensions such as :pypi:`pytest-trio`, which cannot use the ``execute_example`` method. This is **not** recommended for end-users - it is better to write a complete test function directly, perhaps by using a decorator to perform the same transformation before applying :func:`@given <hypothesis.given>`.

.. code:: python

    @given(x=integers())
    @pytest.mark.trio
    async def test(x): ...

    # Illustrative code, inside the pytest-trio plugin
    test.hypothesis.inner_test = lambda x: trio.run(test, x)

For authors of test runners however, assigning to the ``inner_test`` attribute of the ``hypothesis`` attribute of the test will replace the interior test.

.. note::
    The new ``inner_test`` must accept and pass through all the ``*args``
    and ``**kwargs`` expected by the original test.

If the end user has also specified a custom executor using the ``execute_example`` method, it - and all other execution-time logic - will be applied to the *new* inner test assigned by the test runner.

Detecting Hypothesis tests
--------------------------

To determine whether a test has been defined with Hypothesis or not, use |is_hypothesis_test|:

.. autofunction:: hypothesis.is_hypothesis_test

If you're working with :pypi:`pytest`, the :ref:`Hypothesis pytest plugin <pytest-plugin>` automatically adds the ``@pytest.mark.hypothesis`` mark to all Hypothesis tests. You can use ``node.get_closest_marker("hypothesis")`` or similar methods to detect the existence of this mark.
