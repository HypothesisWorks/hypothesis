================
Stateful testing
================

Hypothesis offers support for a stateful style of test, where instead of
trying to produce a single data value that causes a specific test to fail, it
tries to generate a program that errors. In many ways, this sort of testing is
to classical property based testing as property based testing is to normal
example based testing.

The idea doesn't originate with Hypothesis, though Hypothesis's implementation
and approach is mostly not based on an existing implementation and should be
considered some mix of novel and independent reinventions.

This style of testing is useful both for programs which involve some sort
of mutable state and for complex APIs where there's no state per se but the
actions you perform involve e.g. taking data from one function and feeding it
into another.

The idea is that you teach Hypothesis how to interact with your program: Be it
a server, a python API, whatever. All you need is to be able to answer the
question "Given what I've done so far, what could I do now?". After that,
Hypothesis takes over and tries to find sequences of actions which cause a
test failure.

Right now the stateful testing is a bit new and experimental and should be
considered as a semi-public API: It may break between minor versions but won't
break between patch releases, and there are still some rough edges in the API
that will need to be filed off.

This shouldn't discourage you from using it. Although it's not as robust as the
rest of Hypothesis, it's still pretty robust and more importantly is extremely
powerful. I found a number of really subtle bugs in Hypothesis by turning the
stateful testing onto a subset of the Hypothesis API, and you likely will find
the same.

Enough preamble, lets see how to use it.

The first thing to note is that there are two levels of API: The low level
but more flexible API and the higher level rule based API which is both
easier to use and also produces a much better display of data due to its
greater structure. We'll start with the more structured one.

.. _rulebasedstateful:

-------------------------
Rule based state machines
-------------------------

Rule based state machines are the ones you're most likely to want to use.
They're significantly more user friendly and should be good enough for most
things you'd want to do.

The two main ingredients of a rule based state machine are rules and bundles.

A rule is very similar to a normal ``@given`` based test in that it takes
values drawn from strategies and passes them to a user defined test function.
The key difference is that where ``@given`` based tests must be independent,
rules can be chained together - a single test run may involve multiple rule
invocations, which may interact in various ways.

A Bundle is a named collection of generated values that can be reused by other
operations in the test.
They are populated with the results of rules, and may be used as arguments to
rules, allowing data to flow from one rule to another, and rules to work on
the results of previous computations or actions.

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
          super(DatabaseComparison, self).__init__()
          self.tempd = tempfile.mkdtemp()
          self.database = DirectoryBasedExampleDatabase(self.tempd)
          self.model = defaultdict(set)

      keys = Bundle('keys')
      values = Bundle('values')

      @rule(target=keys, k=st.binary())
      def k(self, k):
          return k

      @rule(target=values, v=st.binary())
      def v(self, v):
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

We can then integrate this into our test suite by getting a unittest TestCase
from it:

.. code:: python

  TestTrees = DatabaseComparison.TestCase

  # Or just run with pytest's unittest support
  if __name__ == '__main__':
      unittest.main()

This test currently passes, but if we comment out the line where we call ``self.in_memory_db.delete(k, v)``,
we would see the following output when run under pytest:

::

    AssertionError: assert set() == {b''}

    ------------ Hypothesis ------------

    state = DatabaseComparison()
    v1 = state.k(k=b'')
    v2 = state.v(v=v1)
    state.save(k=v1, v=v2)
    state.delete(k=v1, v=v2)
    state.values_agree(k=v1)
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

  DatabaseComparison.settings = settings(max_examples=50, stateful_step_count=100)

Which doubles the number of steps each program runs and halves the number of
test cases that will be run.

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

    from hypothesis.stateful import RuleBasedStateMachine, rule, precondition

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

    from hypothesis.stateful import RuleBasedStateMachine, rule, invariant

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

----------------------
Generic state machines
----------------------

The class GenericStateMachine is the underlying machinery of stateful testing
in Hypothesis. In execution it looks much like the RuleBasedStateMachine but
it allows the set of steps available to depend in essentially arbitrary
ways on what has happened so far. For example, if you wanted to
use Hypothesis to test a game, it could choose each step in the machine based
on the game to date and the set of actions the game program is telling it it
has available.

It essentially executes the following loop:

.. code:: python

    machine = MyStateMachine()
    try:
        machine.check_invariants()
        for _ in range(n_steps):
            step = machine.steps().example()
            machine.execute_step(step)
            machine.check_invariants()
    finally:
        machine.teardown()

Where ``steps`` and ``execute_step`` are methods you must implement, and
``teardown`` and ``check_invarants`` are methods you can implement if required.
``steps`` returns a strategy, which is allowed to depend arbitrarily on the
current state of the test execution. *Ideally* a good steps implementation
should be robust against minor changes in the state. Steps that change a lot
between slightly different executions will tend to produce worse quality
examples because they're hard to simplify.

The steps method *may* depend on external state, but it's not advisable and
may produce flaky tests.

If any of ``execute_step``, ``check_invariants`` or ``teardown`` produces an
exception, Hypothesis will try to find a minimal sequence of values steps such
that the following throws an exception:

.. code:: python

    machine = MyStateMachine()
    try:
        machine.check_invariants()
        for step in steps:
            machine.execute_step(step)
            machine.check_invariants()
    finally:
        machine.teardown()

and such that at every point, the step executed is one that could plausible
have come from a call to ``steps`` in the current state.

Here's an example of using stateful testing to test a broken implementation
of a set in terms of a list (note that you could easily do something close to
this example with the rule based testing instead, and probably should. This
is mostly for illustration purposes):

.. code:: python

    import unittest

    from hypothesis.stateful import GenericStateMachine
    from hypothesis.strategies import tuples, sampled_from, just, integers


    class BrokenSet(GenericStateMachine):
        def __init__(self):
            self.data = []

        def steps(self):
            add_strategy = tuples(just("add"), integers())
            if not self.data:
                return add_strategy
            else:
                return (
                    add_strategy |
                    tuples(just("delete"), sampled_from(self.data)))

        def execute_step(self, step):
            action, value = step
            if action == 'delete':
                try:
                    self.data.remove(value)
                except ValueError:
                    pass
                assert value not in self.data
            else:
                assert action == 'add'
                self.data.append(value)
                assert value in self.data


    TestSet = BrokenSet.TestCase

    if __name__ == '__main__':
        unittest.main()


Note that the strategy changes each time based on the data that's currently
in the state machine.

Running this gives us the following:

.. code:: bash

  Step #1: ('add', 0)
  Step #2: ('add', 0)
  Step #3: ('delete', 0)
  F
  ======================================================================
  FAIL: runTest (hypothesis.stateful.BrokenSet.TestCase)
  ----------------------------------------------------------------------
  Traceback (most recent call last):
  (...)
      assert value not in self.data
  AssertionError

So it adds two elements, then deletes one, and throws an assertion when it
finds out that this only deleted one of the copies of the element.


-------------------------
More fine grained control
-------------------------

If you want to bypass the TestCase infrastructure you can invoke these
manually. The stateful module exposes the function run_state_machine_as_test,
which takes an arbitrary function returning a GenericStateMachine and an
optional settings parameter and does the same as the class based runTest
provided.

In particular this may be useful if you wish to pass parameters to a custom
__init__ in your subclass.
