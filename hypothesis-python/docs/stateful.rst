================
Stateful testing
================

With :func:`@given <hypothesis.given>`, your tests are still something that
you mostly write yourself, with Hypothesis providing some data.
With Hypothesis's *stateful testing*, Hypothesis instead tries to generate
not just data but entire tests. You specify a number of primitive
actions that can be combined together, and then Hypothesis will
try to find sequences of those actions that result in a failure.

.. tip::

    Before reading this reference documentation, we recommend reading
    `How not to Die Hard with Hypothesis <https://hypothesis.works/articles/how-not-to-die-hard-with-hypothesis/>`__
    and `An Introduction to Rule-Based Stateful Testing <https://hypothesis.works/articles/rule-based-stateful-testing/>`__,
    in that order. The implementation details will make more sense once you've seen
    them used in practice, and know *why* each method or decorator is available.

.. note::

  This style of testing is often called *model-based testing*, but in Hypothesis
  is called *stateful testing* (mostly for historical reasons - the original
  implementation of this idea in Hypothesis was more closely based on
  `ScalaCheck's stateful testing <https://github.com/typelevel/scalacheck/blob/main/doc/UserGuide.md#stateful-testing>`_
  where the name is more apt).
  Both of these names are somewhat misleading: You don't really need any sort of
  formal model of your code to use this, and it can be just as useful for pure APIs
  that don't involve any state as it is for stateful ones.

  It's perhaps best to not take the name of this sort of testing too seriously.
  Regardless of what you call it, it is a powerful form of testing which is useful
  for most non-trivial APIs.


.. _data-as-state-machine:

-------------------------------
You may not need state machines
-------------------------------

The basic idea of stateful testing is to make Hypothesis choose actions as
well as values for your test, and state machines are a great declarative way
to do just that.

For simpler cases though, you might not need them at all - a standard test
with :func:`@given <hypothesis.given>` might be enough, since you can use
:func:`~hypothesis.strategies.data` in branches or loops.  In fact, that's
how the state machine explorer works internally.  For more complex workloads
though, where a higher level API comes into it's own, keep reading!


.. _rulebasedstateful:

-------------------------
Rule-based state machines
-------------------------

.. autoclass:: hypothesis.stateful.RuleBasedStateMachine

A rule is very similar to a normal ``@given`` based test in that it takes
values drawn from strategies and passes them to a user defined test function,
which may use assertions to check the system's behavior.
The key difference is that where ``@given`` based tests must be independent,
rules can be chained together - a single test run may involve multiple rule
invocations, which may interact in various ways.

Rules can take normal strategies as arguments, but normal strategies, with
the exception of  :func:`~hypothesis.strategies.runner` and
:func:`~hypothesis.strategies.data`, cannot take into account
the current state of the machine. This is where bundles come in.

A rule can, in place of a normal strategy, take a :class:`~hypothesis.stateful.Bundle`.
A :class:`hypothesis.stateful.Bundle` is a named collection of generated values that can
be reused by other operations in the test.
They are populated with the results of rules, and may be used as arguments to
rules, allowing data to flow from one rule to another, and rules to work on
the results of previous computations or actions.

Specifically, a rule that specifies ``target=a_bundle`` will cause its return
value to be added to that bundle. A rule that specifies ``an_argument=a_bundle``
as a strategy will draw a value from that bundle.  A rule can also specify
that an argument chooses a value from a bundle and removes that value by using
:func:`~hypothesis.stateful.consumes` as in ``an_argument=consumes(a_bundle)``.

.. note::
    There is some overlap between what you can do with Bundles and what you can
    do with instance variables. Both represent state that rules can manipulate.
    If you do not need to draw values that depend on the machine's state, you
    can simply use instance variables. If you do need to draw values that depend
    on the machine's state, Bundles provide a fairly straightforward way to do
    this. If you need rules that draw values that depend on the machine's state
    in some more complicated way, you will have to abandon bundles. You can use
    :func:`~hypothesis.strategies.runner` and :ref:`.flatmap() <flatmap>`
    to access the instance from a rule: the strategy
    ``runner().flatmap(lambda self: sampled_from(self.a_list))``
    will draw from the instance variable ``a_list``. If you need something more
    complicated still, you can use  :func:`~hypothesis.strategies.data` to
    draw data from the instance (or anywhere else) based on logic in the rule.

The following rule based state machine example is a simplified version of a
test for Hypothesis's example database implementation. An example database
maps keys to sets of values, and in this test we compare one implementation of
it to a simplified in memory model of its behaviour, which just stores the same
values in a Python ``dict``. The test then runs operations against both the
real database and the in-memory representation of it and looks for discrepancies
in their behaviour.

.. code:: python

  import shutil
  import tempfile
  from collections import defaultdict

  import hypothesis.strategies as st
  from hypothesis.database import DirectoryBasedExampleDatabase
  from hypothesis.stateful import Bundle, RuleBasedStateMachine, rule


  class DatabaseComparison(RuleBasedStateMachine):
      def __init__(self):
          super().__init__()
          self.tempd = tempfile.mkdtemp()
          self.database = DirectoryBasedExampleDatabase(self.tempd)
          self.model = defaultdict(set)

      keys = Bundle("keys")
      values = Bundle("values")

      @rule(target=keys, k=st.binary())
      def add_key(self, k):
          return k

      @rule(target=values, v=st.binary())
      def add_value(self, v):
          return v

      @rule(k=keys, v=values)
      def save(self, k, v):
          self.model[k].add(v)
          self.database.save(k, v)

      @rule(k=keys, v=values)
      def delete(self, k, v):
          self.model[k].discard(v)
          self.database.delete(k, v)

      @rule(k=keys)
      def values_agree(self, k):
          assert set(self.database.fetch(k)) == self.model[k]

      def teardown(self):
          shutil.rmtree(self.tempd)


  TestDBComparison = DatabaseComparison.TestCase

In this we declare two bundles - one for keys, and one for values.
We have two trivial rules which just populate them with data (``k`` and ``v``),
and three non-trivial rules:
``save`` saves a value under a key and ``delete`` removes a value from a key,
in both cases also updating the model of what *should* be in the database.
``values_agree`` then checks that the contents of the database agrees with the
model for a particular key.

.. note::
    While this could have been simplified by not using bundles, generating
    keys and values directly in the ``save`` and ``delete`` rules, using bundles
    encourages Hypothesis to choose the same keys and values for multiple
    operations. The bundle operations establish a "universe" of keys and values
    that are used in the rules.

We can now integrate this into our test suite by getting a unittest TestCase
from it:

.. code:: python

  TestTrees = DatabaseComparison.TestCase

  # Or just run with pytest's unittest support
  if __name__ == "__main__":
      unittest.main()

This test currently passes, but if we comment out the line where we call ``self.model[k].discard(v)``,
we would see the following output when run under pytest::

    AssertionError: assert set() == {b''}

    ------------ Hypothesis ------------

    state = DatabaseComparison()
    var1 = state.add_key(k=b'')
    var2 = state.add_value(v=var1)
    state.save(k=var1, v=var2)
    state.delete(k=var1, v=var2)
    state.values_agree(k=var1)
    state.teardown()

Note how it's printed out a very short program that will demonstrate the
problem. The output from a rule based state machine should generally be pretty
close to Python code - if you have custom ``repr`` implementations that don't
return valid Python then it might not be, but most of the time you should just
be able to copy and paste the code into a test to reproduce it.

You can control the detailed behaviour with a settings object on the TestCase
(this is a normal hypothesis settings object using the defaults at the time
the TestCase class was first referenced). For example if you wanted to run
fewer examples with larger programs you could change the settings to:

.. code:: python

  DatabaseComparison.TestCase.settings = settings(
      max_examples=50, stateful_step_count=100
  )

Which doubles the number of steps each program runs and halves the number of
test cases that will be run.

-----
Rules
-----

As said earlier, rules are the most common feature used in RuleBasedStateMachine.
They are defined by applying the :func:`~hypothesis.stateful.rule` decorator
on a function.
Note that RuleBasedStateMachine must have at least one rule defined and that
a single function cannot be used to define multiple rules (this to avoid having
multiple rules doing the same things).
Due to the stateful execution method, rules generally cannot take arguments
from other sources such as fixtures or ``pytest.mark.parametrize`` - consider
providing them via a strategy such as :func:`~hypothesis.strategies.sampled_from`
instead.

.. autofunction:: hypothesis.stateful.rule

.. autofunction:: hypothesis.stateful.consumes

.. autofunction:: hypothesis.stateful.multiple

.. autoclass:: hypothesis.stateful.Bundle

-----------
Initializes
-----------

Initializes are a special case of rules, which are guaranteed to be run exactly
once before any normal rule is called.
Note if multiple initialize rules are defined, they will all be called but in any order,
and that order will vary from run to run.

Initializes are typically useful to populate bundles:

.. autofunction:: hypothesis.stateful.initialize

.. code:: python

    import hypothesis.strategies as st
    from hypothesis.stateful import Bundle, RuleBasedStateMachine, initialize, rule

    name_strategy = st.text(min_size=1).filter(lambda x: "/" not in x)


    class NumberModifier(RuleBasedStateMachine):
        folders = Bundle("folders")
        files = Bundle("files")

        @initialize(target=folders)
        def init_folders(self):
            return "/"

        @rule(target=folders, parent=folders, name=name_strategy)
        def create_folder(self, parent, name):
            return f"{parent}/{name}"

        @rule(target=files, parent=folders, name=name_strategy)
        def create_file(self, parent, name):
            return f"{parent}/{name}"

Initializes can also allow you to initialize the system under test in a way that depends on
values chosen from a strategy. You could do this by putting an instance variable in the
state machine that indicates whether the system under test has been initialized or not,
and then using preconditions (below) to ensure that exactly one of the rules that
initialize it get run before any rules that depend on it being initialized.

-------------
Preconditions
-------------

While it's possible to use :func:`~hypothesis.assume` in RuleBasedStateMachine rules, if you
use it in only a few rules you can quickly run into a situation where few or
none of your rules pass their assumptions. Thus, Hypothesis provides a
:func:`~hypothesis.stateful.precondition` decorator to avoid this problem. The :func:`~hypothesis.stateful.precondition`
decorator is used on ``rule``-decorated functions, and must be given a function
that returns True or False based on the RuleBasedStateMachine instance.

.. autofunction:: hypothesis.stateful.precondition

.. code:: python

    from hypothesis.stateful import RuleBasedStateMachine, precondition, rule


    class NumberModifier(RuleBasedStateMachine):
        num = 0

        @rule()
        def add_one(self):
            self.num += 1

        @precondition(lambda self: self.num != 0)
        @rule()
        def divide_with_one(self):
            self.num = 1 / self.num


By using :func:`~hypothesis.stateful.precondition` here instead of :func:`~hypothesis.assume`, Hypothesis can filter the
inapplicable rules before running them. This makes it much more likely that a
useful sequence of steps will be generated.

Note that currently preconditions can't access bundles; if you need to use
preconditions, you should store relevant data on the instance instead.

----------
Invariants
----------

Often there are invariants that you want to ensure are met after every step in
a process.  It would be possible to add these as rules that are run, but they
would be run zero or multiple times between other rules. Hypothesis provides a
decorator that marks a function to be run after every step.

.. autofunction:: hypothesis.stateful.invariant

.. code:: python

    from hypothesis.stateful import RuleBasedStateMachine, invariant, rule


    class NumberModifier(RuleBasedStateMachine):
        num = 0

        @rule()
        def add_two(self):
            self.num += 2
            if self.num > 50:
                self.num += 1

        @invariant()
        def divide_with_one(self):
            assert self.num % 2 == 0


    NumberTest = NumberModifier.TestCase

Invariants can also have :func:`~hypothesis.stateful.precondition`\ s applied to them, in which case
they will only be run if the precondition function returns true.

Note that currently invariants can't access bundles; if you need to use
invariants, you should store relevant data on the instance instead.

-------------------------
More fine grained control
-------------------------

If you want to bypass the TestCase infrastructure you can invoke these
manually. The stateful module exposes the function ``run_state_machine_as_test``,
which takes an arbitrary function returning a RuleBasedStateMachine and an
optional settings parameter and does the same as the class based runTest
provided.

This is not recommended as it bypasses some important internal functions,
including reporting of statistics such as runtimes and :func:`~hypothesis.event`
calls.  It was originally added to support custom ``__init__`` methods, but
you can now use :func:`~hypothesis.stateful.initialize` rules instead.
