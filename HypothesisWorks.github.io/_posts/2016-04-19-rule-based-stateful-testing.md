---
layout: post
tags: python technical intro
date: 2016-04-19 07:00
title: Rule Based Stateful Testing
published: true
---

Hypothesis's standard testing mechanisms are very good for testing things that can be
considered direct functions of data. But supposed you have some complex stateful
system or object that you want to test. How can you do that?

In this post we'll see how to use Hypothesis's *rule based state mahines* to define
tests that generate not just simple data, but entire programs using some stateful
object. These will give the same level of boost to testing the behaviour of the
object as you get to testing the data it accepts.

<!--more-->

The model of a stateful system we'll be using is a [priority queue](https://en.wikipedia.org/wiki/Priority_queue)
implemented as a binary heap.

We have the following operations:

* newheap() - returns a new heap
* heappush(heap, value) - place a new value into the heap
* heappop(heap) - remove and return the smallest value currently on the heap. Error if heap is empty.
* heapempty(heap) - return True if the heap has no elements, else False.

We'll use the following implementation of these:

```python
def heapnew():
    return []


def heapempty(heap):
  return not heap


def heappush(heap, value):
    heap.append(value)
    index = len(heap) - 1
    while index > 0:
        parent = (index - 1) // 2
        if heap[parent] > heap[index]:
            heap[parent], heap[index] = heap[index], heap[parent]
            index = parent
        else:
            break


def heappop(heap):
    return heap.pop(0)
```

(Note that this implementation is *wrong*. heappop as implemented will return the smallest element
if the heap currently satisfies the heap property, but it will not rebalance the heap afterwards
so it may leave the heap in an invalid state)

We could test this readily enough using @given with something like the following:


```
from hypothesis.strategies import integers, lists
from hypothesis import given


@given(lists(integers()))
def test_pop_in_sorted_order(ls):
    h = heapnew()
    for l in ls:
        heappush(h, l)
    r = []
    while not heapempty(h):
        r.append(heappop(h))
    assert r == sorted(ls)
```

And this indeed finds the bug:

```
>       assert r == sorted(ls)
E       assert [0, 1, 0] == [0, 0, 1]
E         At index 1 diff: 1 != 0
E         Use -v to get the full diff

binheap.py:74: AssertionError
----- Hypothesis -----
Falsifying example: test_pop_in_sorted_order(ls=[0, 1, 0])
```

So we replace heappop with a correct implementation which rebalances the heap:

```python
def heappop(heap):
    if len(heap) == 0:
        raise ValueError("Empty heap")
    if len(heap) == 1:
        return heap.pop()
    result = heap[0]
    heap[0] = heap.pop()
    index = 0
    while index * 2 + 1 < len(heap):
        children = [index * 2 + 1, index * 2 + 2]
        children = [i for i in children if i < len(heap)]
        assert children
        children.sort(key=lambda x: heap[x])
        for c in children:
            if heap[index] > heap[c]:
                heap[index], heap[c] = heap[c], heap[index]
                index = c
                break
        else:
            break
    return result
```

But how do we know this is enough? Might some combination of mixing pushes and pops break the
invariants of the heap in a way that this simple pattern of pushing everything then popping
everything cannot witness?

This is where the rule based state machines come in. Instead of just letting Hypothesis give
us data which we feed into a fixed structure of test, we let Hypothesis choose which operations
to perform on our data structure:

```python
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine

class HeapMachine(RuleBasedStateMachine):
    def __init__(self):
        super(HeapMachine1, self).__init__()
        self.heap = []

    @rule(value=integers())
    def push(self, value):
        heappush(self.heap, value)

    @rule()
    @precondition(lambda self: self.heap)
    def pop(self):
        correct = min(self.heap)
        result = heappop(self.heap)
        assert correct == result
```

@rule is a slightly restricted version of @given that only works for methods on a RuleBasedStateMachine.

However it has one *major* difference from @given, which is that multiple rules can be chained together:
A test using this state machine doesn't just run each rule in isolation, it instantiates an instance of
the machine and then runs multiple rules in succession.

The @precondition decorator constrains when a rule is allowed to fire: We are not allowed to pop from
an empty heap, so the pop rule may only fire when there is data to be popped.

We can run this by getting a standard unit test TestCase object out of it to be picked up by unittest
or py.test as normal:

```python
TestHeaps = HeapMachine.TestCase
```

With our original broken heappop we find the same bug as before:

```python
E       AssertionError: assert 0 == 1

binheap.py:90: AssertionError
----- Captured stdout call -----
Step #1: push(value=1)
Step #2: push(value=0)
Step #3: push(value=0)
Step #4: pop()
Step #5: pop()
```

With the fixed implementation the test passes.

As it currently stands, this is already very useful. It's particularly good for testing single standalone
objects or services like storage systems.

But one limitation of it as we have written it is that it only concerns ourselves with a single heap. What
if we wanted to combine two heaps? For example, suppose we wanted a heap merging operation that takes two
heaps and returns a new heap containing the values in either of the original two.

As before, we'll start with a broken implementation:

```python

```

We can't just write a strategy for heaps, because each heap would be a fresh object and thus it would not
preserve the stateful aspect.

What we instead do is use the other big feature of Hypothesis's rule bases state machines: Bundles.

Bundles allow rules to return as well as accept values. A bundle is a strategy which generates anything
a rule has previously provided to it. Using them is as follows:


```python
class HeapMachine(RuleBasedStateMachine):
    Heaps = Bundle('heaps')

    @rule(target=Heaps)
    def newheap(self):
        return []

    @rule(heap=Heaps, value=integers())
    def push(self, heap, value):
        heappush(heap, value)

    @rule(heap=Heaps.filter(bool))
    def pop(self, heap):
        correct = min(heap)
        result = heappop(heap)
        assert correct == result

    @rule(target=Heaps, heap1=Heaps, heap2=Heaps)
    def merge(self, heap1, heap2):
        return heapmerge(heap1, heap2)
```

So now instead of a single heap we manage a collection of heaps. All of our previous operations become
constrained by an instance of a heap.

Note the use of filter: A bundle is a strategy you can use like any other. In this case the filter replaces
our use of a precondition because we now only care about whether this *specific* heap is empty.

This is sufficient to find the fact that our implementation is wrong:

```
    @rule(heap=Heaps.filter(bool))
    def pop(self, heap):
        correct = min(heap)
        result = heappop(heap)
>       assert correct == result
E       AssertionError: assert 0 == 1

binheap.py:105: AssertionError

----- Captured stdout call -----

Step #1: v1 = newheap()
Step #2: push(heap=v1, value=0)
Step #3: push(heap=v1, value=1)
Step #4: push(heap=v1, value=1)
Step #5: v2 = merge(heap2=v1, heap1=v1)
Step #6: pop(heap=v2)
Step #7: pop(heap=v2)
```

We create a small heap, merge it with itself, and rapidly discover that it has become unbalanced.

We can fix this by fixing our heapmerge to be correct:

```python
def heapmerge(x, y):
    result = list(heap1)
    for v in heap2:
        heappush(result, v)
    return result
```

But that's boring. Lets introduce a more *interestingly* broken implementation instead:

```python
def heapmerge(x, y):
    result = []
    i = 0
    j = 0
    while i < len(x) and j < len(y):
        if x[i] <= y[j]:
            result.append(x[i])
            i += 1
        else:
            result.append(y[j])
            j += 1
    result.extend(x[i:])
    result.extend(y[j:])
    return result
```

This merge operation selectively splices two heaps together as if we were merging two
sorted lists (heaps aren't actually sorted, but the code still works regardless it
just doesn't do anything very meaningful).

This is wrong, but it turns out to work surprisingly well for small heaps and it's
not completely straightforward to find an example showing that it's wrong.

Here's what Hypothesis comes up with:

```
Step #1: v1 = newheap()
Step #2: push(heap=v1, value=0)
Step #3: v2 = merge(heap1=v1, heap2=v1)
Step #4: v3 = merge(heap1=v2, heap2=v2)
Step #5: push(heap=v3, value=-1)
Step #6: v4 = merge(heap1=v1, heap2=v2)
Step #7: pop(heap=v4)
Step #8: push(heap=v3, value=-1)
Step #9: v5 = merge(heap1=v1, heap2=v2)
Step #10: v6 = merge(heap1=v5, heap2=v4)
Step #11: v7 = merge(heap1=v6, heap2=v3)
Step #12: pop(heap=v7)
Step #13: pop(heap=v7)
```

Through a careful set of heap creation and merging, Hypothesis manages to find a series
of merges that produce an unbalanced heap. Every heap prior to v7 is balanced, but v7 looks
like this:

```pycon
>>> v7
[-1, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0]
```

Which doesn't satisfy the heap property because of that -1 far down in the list.

I don't know about you, but I would never have come up with that example. There's probably
a simpler one given a different set of operations - e.g. one thing that would probably improve
the quality of this test is to let Hypothesis instantiate a new heap with a list of elements
which it pops onto it.

But the nice thing about rule based stateful testing is that I don't *have* to come up with
the example. Instead Hypothesis is able to guarantee that every combination of operations
on my objects works, and can flush out some remarkably subtle bugs in the process.

Because after all, if it takes this complicated an example to demonstrate that a completely
wrong implementation is wrong, how hard can it sometimes be to demonstrate subtle bugs?

### Real world usage

This feature is currently somewhat under-documented so hasn't seen as widespread adoption as
it could. However, there are at least two interesting real world examples:

1. Hypothesis uses it to test itself. Hypothesis has [tests of its example database](
   https://github.com/HypothesisWorks/hypothesis-python/blob/master/tests/cover/test_database_agreement.py)
   which work very much like the above, and [a small model of its test API](
   https://github.com/HypothesisWorks/hypothesis-python/blob/master/tests/nocover/test_strategy_state.py)
   which generates random strategies and runs tests using them.
2. It's being used to [test Mercurial](https://www.mercurial-scm.org/pipermail/mercurial-devel/2016-February/080037.html)
   generating random. So far it's found [bug 5112](https://bz.mercurial-scm.org/show_bug.cgi?id=5112) and
   [bug 5113](https://bz.mercurial-scm.org/show_bug.cgi?id=5113). The usage pattern on Mercurial is one
   such that the stateful testing probably needs more resources, more rules and more work on deployment
   before it's going to find much more than that though.
