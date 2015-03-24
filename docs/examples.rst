==================
Some more examples
==================

This is a collection of examples of how to use Hypothesis in interesting ways.
It's small for now but will grow over time.

All of these examples are designed to be run under py.test (nose should probably
work too).

----------------------------------
How not to sort by a partial order
----------------------------------

The following is an example that's been extracted and simplified from a real
bug that occurred in an earlier version of Hypothesis. The real bug was a lot
harder to find.

Suppose we've got the following type:

.. code:: python

    class Node(object):
        def __init__(self, label, value):
            self.label = label
            self.value = tuple(value)

        def __repr__(self):
            return "Node(%r, %r)" % (self.label, self.value)

        def sorts_before(self, other):
            if len(self.value) >= len(other.value):
                return False
            return other.value[:len(self.value)] == self.value


Each node is a label and a sequence of some data, and we have the relationship
sorts_before meaning the data of the left is an initial segment of the right.
So e.g. a node with value [1, 2] will sort before a node with value [1, 2, 3],
but neither of [1, 2] nor [1, 3] will sort before the other.

We have a list of nodes, and we want to topologically sort them with respect to
this ordering. That is, we want to arrange the list so that if x.sorts_before(y)
then x appears earlier in the list than y. We naively think that the easiest way
to do this is to extend the  partial order defined here to a total order by
breaking ties arbitrarily and then using a normal sorting algorithm. So we
define the following code:

.. code:: python

    from functools import total_ordering


    @total_ordering
    class TopoKey(object):
        def __init__(self, node):
            self.value = node

        def __lt__(self, other):
            if self.value.sorts_before(other.value):
                return True
            if other.value.sorts_before(self.value):
                return False

            return self.value.label < other.value.label


    def sort_nodes(xs):
        xs.sort(key=TopoKey)

This takes the order defined by sorts_before and extends it by breaking ties by
comparing the node labels.

But now we want to test that it works.

First we right a function to verify that our desired outcome holds:

.. code:: python

  def is_prefix_sorted(xs):
      for i in range(len(xs)):
          for j in range(i+1, len(xs)):
              if xs[j].sorts_before(xs[i]):
                  return False
      return True

This will return false if it ever finds a pair in the wrong order and
return true otherwise.

Given this function, what we want to do with Hypothesis is assert that for all
sequences of nodes, the result of calling sort_nodes on it is sorted.

First we need to define a strategy for Node:

.. code:: python

  from hypothesis import Settings, strategy

  @strategy.extend_static(Node)
  def node_strategy(_, settings):
      with settings:
          values = strategy([bool], Settings(average_list_length=5.0))
      return strategy((int, values), settings).map(
          lambda kv: Node(*kv)
      )

What we're doing is a little subtle here: We want to generate *short* lists of values
so that there's a decent chance of one being a prefix of the other (this is also why
the choice of bool as the elements), so we explicitly create a strategy that overrides
a setting that controls the list length. We use the passed in settings as a context
manager to inherit its defaults.

Once we have the strategy for the values, we map over a strategy for a tuple of a label 
and the values to produce a node. We then install this as the strategy for nodes.

We can now write a test:

.. code:: python

  from hypothesis import given

  @given([Node])
  def test_sorting_nodes_is_prefix_sorted(xs):
      sort_nodes(xs)
      assert is_prefix_sorted(xs)

this immediately fails with the following example:

.. code:: python

  [Node(0, (False, True)), Node(0, (True,)), Node(0, (False,))]


The reason for this is that because False is not a prefix of (True, True) nor vice
versa, sorting things the first two nodes are equal because they have equal labels.
This makes the whole order non-transitive and produces basically nonsense results.

But this is pretty unsatisfying. It only works because they have the same label. Perhaps
we actually wanted our labels to be unique. Lets change the test to do that.

.. code:: python

    def deduplicate_nodes_by_label(nodes):
        table = {}
        for node in nodes:
            table[node.label] = node
        return list(table.values())


    NodeSet = strategy([Node]).map(deduplicate_nodes_by_label)

We define a function to deduplicate nodes by labels, and then map that over a strategy
for lists of nodes to give us a strategy for lists of nodes with unique labels. We can
now rewrite the test to use that:


.. code:: python

    @given(NodeSet)
    def test_sorting_nodes_is_prefix_sorted(xs):
        sort_nodes(xs)
        assert is_prefix_sorted(xs)

This example will take a while to run (it takes about a minute for me). Hypothesis has
some trouble getting a good minimization of this example because a lot of the things it
tries to speed up the minimization don't work. This is partly because the condition we
are trying to minimimize for is tricky - it depends in detail on the exact edge cases 
you hit in sorting - 

Hypothesis has a bit more trouble minimizing a good example for this (mostly in that
it takes it rather a lot longer because some of the shortcuts it takes in minimization
are blocked off because they would cause duplicates) but it finds us a new example:


.. code:: python

  [Node(0, (False,)), Node(-1, (True,)), Node(-2, (False, False))])


Now this is a more interesting example. None of the nodes will sort equal. What is
happening here is that the first node is strictly less than the last node because
(False,) is a prefix of (False, False). This is in turn strictly less than the middle
node because neither is a prefix of the other and -2 < -1. The middle node is then
less than the first node because -1 < 0.

So, convinced that our implementation is broken, we write a better one:

.. code:: python

    def sort_nodes(xs):
        for i in xrange(1, len(xs)):
            j = i - 1
            while j >= 0:
                if xs[j].sorts_before(xs[j+1]):
                    break
                xs[j], xs[j+1] = xs[j+1], xs[j]
                j -= 1

This is just insertion sort slightly modified - we swap a node backwards until swapping
it further would violate the order constraints. The reason this works is because our
order is a partial order already (this wouldn't produce a valid result for a general
topological sorting - you need the transitivity).

We now run our test again and it passes, telling us that this time we've successfully
managed to sort some nodes without getting it completely wrong. Go us.

--------------------
Time zone arithmetic
--------------------

This is an example of some tests for pytz which check that various timezone
conversions behave as you would expect them to. These tests should all pass,
and are mostly a demonstration of some useful sorts of thing to test with
Hypothesis, and how the hypothesis-datetime extra package works.

.. code:: python

    from hypothesis import given, Settings
    from hypothesis.extra.datetime import naive_datetime, timezone_aware_datetime
    from hypothesis.specifiers import sampled_from
    import pytz
    from datetime import timedelta

    ALL_TIMEZONES = list(map(pytz.timezone, pytz.all_timezones))

    # There are a lot of fiddly edge cases in dates, so we run a larger number of
    # examples just to be sure
    with Settings(max_examples=1000):
        @given(
            timezone_aware_datetime,
            sampled_from(ALL_TIMEZONES), sampled_from(ALL_TIMEZONES),
        )
        def test_convert_via_intermediary(dt, tz1, tz2):
            """
            Test that converting between timezones is not affected by a detour via
            another timezone.
            """
            assert dt.astimezone(tz1).astimezone(tz2) == dt.astimezone(tz2)

        @given(
            naive_datetime,
            sampled_from(ALL_TIMEZONES), sampled_from(ALL_TIMEZONES),
        )
        def test_convert_to_and_fro(dt, tz1, tz2):
            """
            If we convert to a new timezone and back to the old one this should
            leave the result unchanged.
            """
            dt = tz1.localize(dt)
            assert dt == dt.astimezone(tz2).astimezone(tz1)

        @given(
            timezone_aware_datetime,
            sampled_from(ALL_TIMEZONES),
        )
        def test_adding_an_hour_commutes(dt, tz):
            """
            When converting between timezones it shouldn't matter if we add an hour
            here or add an hour there.
            """
            an_hour = timedelta(hours=1)
            assert (dt + an_hour).astimezone(tz) == dt.astimezone(tz) + an_hour

        @given(
            timezone_aware_datetime,
            sampled_from(ALL_TIMEZONES),
        )
        def test_adding_a_day_commutes(dt, tz):
            """
            When converting between timezones it shouldn't matter if we add a day
            here or add a day there.
            """
            a_day = timedelta(days=1)
            assert (dt + a_day).astimezone(tz) == dt.astimezone(tz) + a_day

------------------------
A classic voting paradox
------------------------

A classic paradox in voting theory is that majority preferences are not
transitive. That is, there is a population and a set of three candidates A, B
and C such that the majority of the population prefer A to B, B to C and C to
A.

Wouldn't it be neat if we could use Hypothesis to provide an example of this?

Well as you can probably guess from the presence in this section, we can! This
is slightly surprising because it's not really obvious how we would generate an
election given the types that Hypothesis knows about.

The trick here turns out to be twofold:

1. We can generate a type that is *much larger* than an election, extract an election out of that, and rely on minimization to throw away all the extraneous detail.
2. We can use assume and rely on Hypothesis's adaptive exploration to focus on the examples that turn out to generate interesting elections

Without further ado, here is the code:

.. code:: python

    from hypothesis import given, assume
    from hypothesis.specifiers import integers_in_range
    from collections import Counter


    def candidates(votes):
        return {candidate for vote in votes for candidate in vote}


    def build_election(votes):
        """
        Given a list of lists we extract an election out of this. We do this
        in two phases:

        1. First of all we work out the full set of candidates present in all
           votes and throw away any votes that do not have that whole set.
        2. We then take each vote and make it unique, keeping only the first
           instance of any candidate.

        This gives us a list of total orderings of some set. It will usually
        be a lot smaller than the starting list, but that's OK.
        """
        all_candidates = candidates(votes)
        votes = list(filter(lambda v: set(v) == all_candidates, votes))
        if not votes:
            return []
        rebuilt_votes = []
        for vote in votes:
            rv = []
            for v in vote:
                if v not in rv:
                    rv.append(v)
            assert len(rv) == len(all_candidates)
            rebuilt_votes.append(rv)
        return rebuilt_votes


    @given([[integers_in_range(1, 5)]])
    def test_elections_are_transitive(election):
        election = build_election(election)
        # Small elections are unlikely to be interesting
        assume(len(election) >= 3)
        all_candidates = candidates(election)
        # Elections with fewer than three candidates certainly can't exhibit
        # intransitivity
        assume(len(all_candidates) >= 3)

        # Now we check if the election is transitive

        # First calculate the pairwise counts of how many prefer each candidate
        # to the other
        counts = Counter()
        for vote in election:
            for i in range(len(vote)):
                for j in range(i+1, len(vote)):
                    counts[(vote[i], vote[j])] += 1

        # Now look at which pairs of candidates one has a majority over the
        # other and store that.
        graph = {}
        all_candidates = candidates(election)
        for i in all_candidates:
            for j in all_candidates:
                if counts[(i, j)] > counts[(j, i)]:
                    graph.setdefault(i, set()).add(j)

        # Now for each triple assert that it is transitive.
        for x in all_candidates:
            for y in graph.get(x, ()):
                for z in graph.get(y, ()):
                    assert x not in graph.get(z, ())

The example Hypothesis gives me on my first run (your mileage may of course
vary) is:

.. code:: python

    [[3, 1, 4], [4, 3, 1], [1, 4, 3]]

Which does indeed do the job: The majority (votes 0 and 1) prefer 3 to 1, the
majority (votes 0 and 2) prefer 1 to 4 and the majority (votes 1 and 2) prefer
4 to 3. This is in fact basically the canonical example of the voting paradox,
modulo variations on the names of candidates.
