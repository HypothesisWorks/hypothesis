================
Stateful testing
================

With :func:`@given <hypothesis.given>`, your tests are still something that
you mostly write yourself, with Hypothesis providing some data.
With Hypothesis's *stateful testing*, Hypothesis instead tries to generate
not just data but entire tests. You specify a number of primitive
actions that can be combined together, and then Hypothesis will
try to find sequences of those actions that result in a failure.

.. note::

  This style of testing is often called *model-based testing*, but in Hypothesis
  is called *stateful testing* (mostly for historical reasons - the original
  implementation of this idea in Hypothesis was more closely based on
  `ScalaCheck's stateful testing <https://github.com/rickynils/scalacheck/blob/master/doc/UserGuide.md#stateful-testing>`_
  where the name is more apt).
  Both of these names are somewhat misleading: You don't really need any sort of
  formal model of your code to use this, and it can be just as useful for pure APIs
  that don't involve any state as it is for stateful ones.

  It's perhaps best to not take the name of this sort of testing too seriously.
  Regardless of what you call it, it is a powerful form of testing which is useful
  for most non-trivial APIs.

Hypothesis has two stateful testing APIs: A high level one, providing what
we call *rule based state machines*, and a low level one, providing what we call
*generic state machines*.

You probably want to use the rule based state machines - they provide a high
level API for describing the sort of actions you want to perform, based on a
structured representation of actions. However the generic state machines are
more flexible, and are particularly useful if you want the set of currently
possible actions to depend primarily on external state.

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

This test currently passes, but if we comment out the line where we call ``self.model[k].discard(v)``,
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

The class :class:`~hypothesis.stateful.GenericStateMachine` is the underlying machinery of stateful testing
in Hypothesis. Chances are you will want to use the rule based stateful testing
for most things, but the generic state machine functionality can be useful e.g. if
you want to test things where the set of actions to be taken is more closely
tied to the state of the system you are testing.

.. module:: hypothesis.stateful
.. autoclass:: GenericStateMachine
    :members: steps, execute_step, check_invariants, teardown

For example, here we use stateful testing as a sort of link checker, to test
`hypothesis.works <https://hypothesis.works>`_ for broken links or links that
use HTTP instead of HTTPS.

.. code:: python

  from hypothesis.stateful import GenericStateMachine
  import hypothesis.strategies as st
  from requests_html import HTMLSession


  class LinkChecker(GenericStateMachine):
      def __init__(self):
          super(LinkChecker, self).__init__()
          self.session = HTMLSession()
          self.result = None

      def steps(self):
          if self.result is None:
              # Always start on the home page
              return st.just("https://hypothesis.works/")
          else:
              return st.sampled_from([
                  l
                  for l in self.result.html.absolute_links
                  # Don't try to crawl to other people's sites
                  if l.startswith("https://hypothesis.works") and
                  # Avoid Cloudflare's bot protection. We are a bot but we don't
                  # care about the info it's hiding.
                  '/cdn-cgi/' not in l
              ])

      def execute_step(self, step):
          self.result = self.session.get(step)

          assert self.result.status_code == 200

          for l in self.result.html.absolute_links:
              # All links should be HTTPS
              assert "http://hypothesis.works" not in l


  TestLinks = LinkChecker.TestCase

Running this (at the time of writing this documentation) produced the following
output:

::

  AssertionError: assert 'http://hypothesis.works' not in 'http://hypoth...test-fixtures/'
  'http://hypothesis.works' is contained here:
    http://hypothesis.works/articles/hypothesis-pytest-fixtures/
  ? +++++++++++++++++++++++

    ------------ Hypothesis ------------

  Step #1: 'https://hypothesis.works/'
  Step #2: 'https://hypothesis.works/articles/'


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
