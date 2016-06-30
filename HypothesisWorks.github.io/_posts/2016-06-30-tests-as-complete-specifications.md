---
layout: post
tags: technical python properties into
date: 2016-06-30 00:00
title: Testing as a Complete Specification
published: true
author: drmaciver
---

Sometimes you're lucky enough to have problems where the result is
completely specified by a few simple properties.

This doesn't necessarily correspond to them being easy! Many such
problems are actually extremely fiddly to implement.

It does mean that they're easy to *test* though. Lets see how.

<!--more-->

Lets look at the problem of doing a binary search. Specifically we'll
look at a left biased binary search: Given a sorted list and some value,
we want to find the smallest index that we can insert that value at and
still have the result be sorted.

So we've got the following properties:

1. binary_search must always return a valid index to insert the value
   at.
2. If we insert the value at that index the result must be sorted.
3. If we insert the value at any *smaller* index, the result must *not*
   be sorted.

Using Hypothesis we can write down tests for all these properties:

```python
from hypothesis import given, strategies as st

@given(lists(integers()).map(sorted), integers())
def test_binary_search_gives_valid_index(ls, v):
    i = binary_search(ls, v)
    assert 0 <= i <= len(ls)

@given(lists(integers()).map(sorted), integers())
def test_inserting_at_binary_search_remains_sorted(ls, v):
    i = binary_search(ls, v)
    ls.insert(i, v)
    assert sorted(ls) == ls

@given(lists(integers()).map(sorted), integers())
def test_inserting_at_smaller_index_gives_unsorted(ls, v):
    for i in range(binary_search(ls, v)):
        ls2 = list(ls)
        ls2.insert(i, v)
        assert sorted(ls2) != ls
```

If these tests pass, our implementation must be perfectly correct,
right? They capture the specification of the binary_search function
exactly, so they should be enough.

And they mostly are, but they suffer from one problem that will
sometimes crop up with property-based testing: They don't hit all bugs
with quite high enough probability.

This is the difference between testing and mathematical proof: A proof
will guarantee that these properties *always* hold, while a test can
only guarantee that they hold in the areas that it's checked. A test
using Hypothesis will check a much wider area than most hand-written
tests, but it's still limited to a finite set of examples.

Lets see how this can cause us problems. Consider the following
implementation of binary search:

```python

def binary_search(list, value):
    if not list:
        return 0
    if value > list[-1]:
        return len(list)
    if value <= list[0]:
        return 0
    lo = 0
    hi = len(list) - 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        pivot = list[mid]
        if value < pivot:
            hi = mid
        elif value == pivot:
            return mid
        else:
            lo = mid
    return hi
```

This implements the common check that if our pivot index ever has
exactly the right value we return early there. Unfortunately in this
case that check is wrong: It violates the property that we should
always find the *smallest* property, so the third test should fail.

And sure enough, if you run the test enough times it eventually *does*
fail:

```
Falsifying example: test_inserting_at_smaller_index_gives_unsorted(
    ls=[0, 1, 1, 1, 1], v=1
 )
```

(you may also get `(ls=[-1, 0, 0, 0, 0], v=0)`)

However when I run it it usually *doesn't* fail the first time. It
usually takes somewhere between two and five runs before it fails. This
is because in order to trigger this behaviour being wrong you need
quite specific behaviour: `value` needs to appear in `ls` at least
twice, and it needs to do so in such a way that one of the indices where
it appears that is *not* the first one gets chosen as `mid` at some
point in the process. Hypothesis does some things that boost the
chances of this happening, but they don't boost it *that* much.

Of course, once it starts failing Hypothesis's test database kicks in,
and the test keeps failing until the bug is fixed, but low probability
failures are still annoying because they move the point at which you
discover the problem further away from when you introduced it. This is
especically true when you're using [stateful testing
]({{site.url}}{% post_url 2016-04-19-rule-based-stateful-testing %}),
because the search space is so large that there are a lot of low
probability bugs.

Fortunately there's an easy fix for this case: You can write additional
tests that are more likely to discover bugs because they are less
sensitively dependent on the example chosen by Hypothesis to exhibit
interesting behaviours.

Consider the following test:

```python

@given(lists(integers()).map(sorted), integers())
def test_inserting_at_result_point_and_searching_again(ls, v):
    i = binary_search(ls, v)
    ls.insert(i, v)
    assert binary_search(ls, v) == i
```

The idea here is that by doing a search, inserting the value at that
index, and searching again we cannot have moved the insert point:
Inserting there again would still result in a sorted list, and inserting
any earlier would still have resulted in an unsorted list, so this must
still be the same insert point (this should remind you a bit of 
[the approach for testing optimizers we used before](
{{site.url}}{% post_url 2016-05-29-testing-optimizers-with-hypothesis %})
).

This test fails pretty consistently because it doesn't rely nearly so
much on finding duplicates: Instead it deliberately creates them in a
place where they are likely to be problematic.

So, in conclusion:

1. When the problem is fully specified, this gives you a natural source
   of tests that you can easily write using Hypothesis.
2. However this is where your tests should *start* rather than finish,
   and you still need to think about other intersting ways to test your
   software.
