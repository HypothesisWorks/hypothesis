---
layout: post
tags: technical python
date: 2016-05-29 21:00
title: Testing Optimizers
published: true
author: drmaciver
---

We've [previously looked into testing performance optimizations]
({{site.url}}{% post_url 2016-04-29-testing-performance-optimizations %})
using Hypothesis, but this
article is about something quite different: It's about testing code
that is designed to optimize a value. That is, you have some function
and you want to find arguments to it that maximize (or minimize) its
value.

As well as being an interesting subject in its own right, this will also
nicely illustrate the use of Hypothesis's data() functionality, which
allows you to draw more data after the test has started, and will
introduce a useful general property that can improve your testing in
a much wider variety of settings.

<!--more-->

We'll use [the Knapsack Packing Problem](https://en.wikipedia.org/wiki/Knapsack_problem)
as our example optimizer. We'll use the greedy approximation algorithm
described in the link, and see if Hypothesis can show us that it's
merely an approximation and not in fact optimal.

```python
def pack_knapsack(items, capacity):
    """Given items as a list [(value, weight)], with value and weight
    strictly positive integers, try to find a maximum value subset of
    items with total weight <= capacity"""
    remaining_capacity = capacity
    result = []

    # Sort in order of decreasing value per unit weight, breaking
    # ties by taking the lowest weighted items first.
    items = sorted(items, key=lambda x: (x[1] / x[0], x[1]))
    for value, weight in items:
        if weight <= remaining_capacity:
            result.append((value, weight))
            remaining_capacity -= weight
    return result
```

So how are we going to test this?

If we had another optimizer we could test by comparing the two results,
but we don't, so we need to figure out properties it should satisfy in
the absence of that.

The trick we will used to test this is to look for responses to change.

That is, we will run the function, we will make a change to the data
that should cause the function's output to change in a predictable way,
and then we will run the function again and see if it did.

But how do we figure out what changes to make?

The key idea is that we will look at the output of running the optimizer
and use that to guide what changes we make. In particular we will test
the following two properties:

1. If we remove an item that was previously chosen as part of the
   optimal solution, this should not improve the score.
2. If we add an extra copy of an item that was previously chosen as part
   of the optimal solution, this should not make the score worse.

In the first case, any solution that is found when running with one
fewer item would also be a possible solution when running with the full
set, so if the optimizer is working correctly then it should have found
that one if it were an improvement.

In the second case, the opposite is true: Any solution that was
previously available is still available, so if the optimizer is working
correctly it can't find a worse one than it previously found.

The two tests look very similar:

```python

from hypothesis import given, assume, settings, Verbosity
import hypothesis.strategies as st


def score_items(items):
    return sum(value for value, _ in items)


PositiveIntegers = st.integers(min_value=1, max_value=10)
Items = st.lists(st.tuples(PositiveIntegers, PositiveIntegers), min_size=1)
Capacities = PositiveIntegers


@given(Items, Capacities, st.data())
def test_cloning_an_item(items, capacity, data):
    original_solution = pack_knapsack(items, capacity)
    assume(original_solution)
    items.append(data.draw(st.sampled_from(original_solution)))
    new_solution = pack_knapsack(items, capacity)
    assert score_items(new_solution) >= score_items(original_solution)


@given(Items, Capacities, st.data())
def test_removing_an_item(items, capacity, data):
    original_solution = pack_knapsack(items, capacity)
    assume(original_solution)
    item = data.draw(st.sampled_from(original_solution))
    items.remove(item)
    new_solution = pack_knapsack(items, capacity)
    assert score_items(new_solution) <= score_items(original_solution)
```

(The max_value parameter for integers is inessential but results in
nicer example quality).

The *data* strategy simply provides an object you can use for drawing
more data interactively during the test. This allows us to make our
choices dependent on the output of the function when we run it. The
draws made will be printed as additional information in the case of a
failing example.

In fact, both of these tests fail:

```

Falsifying example: test_cloning_an_item(items=[(1, 1), (1, 1), (2, 5)], capacity=7, data=data(...))
Draw 1: (1, 1)

```

In this case what happens is that when Hypothesis clones an item of
weight and value 1, the algorithm stuffs its knapsack with all three
(1, 1) items, at which point it has spare capacity but no remaining
items that are small enough to fit in it.

```

Falsifying example: test_removing_a_chosen_item(items=[(1, 1), (2, 4), (1, 2)], capacity=6, data=data(...))
Draw 1: (1, 1)

```

In this case what happens is the opposite: Previously the greedy
algorithm was reaching for the (1, 1) item as the most appealing because
it had the highest value to weight ratio, but by including it it only
had space for one of the remaining two. When Hypothesis removed that
option, it could fit the remaining two items into its knapsack and thus
scored a higher point.

In this case these failures were more or less expected: As described in
the Wikipedia link, for the relatively small knapsacks we're exploring
here the greedy approximation algorithm turns out to in fact be quite
bad, and Hypothesis can easily expose that.

This technique however can be more widely applied: e.g. You can try
changing permissions and settings on a user and asserting that they
always have more options, or increasing the capacity of a subsystem and
seeing that it is always allocated more tasks.
