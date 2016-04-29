---
layout: post
tags: technical intro python
date: 2016-04-29 11:00
title: Testing performance optimizations
published: true
---

Once you've 
[flushed out the basic crashing bugs]({{site.url}}{% post_url 2016-04-15-getting-started-with-hypothesis %})
in your code, you're going to want to look for more interesting things to test.

The next easiest thing to test is code where you know what the right answer is for every input.

Obviously in theory you think you know what the right answer is - you can just run the code. That's not very
helpful though, as that's the answer you're trying to verify.

But sometimes there is more than one way to get the right answer, and you choose the one you run in production
not because it gives a different answer but because it gives the same answer *faster*.

<!--more-->

For example:

* There might be a fancy but fast version of an algorithm and a simple but slow version of an algorithm.
* You might have a caching layer and be able to run the code with and without caching turned on, or with a
  different cache timeout.
* You might be moving to a new database backend to improve your scalability, but you still have the code for
  the old backend until you've completed your migration.

There are plenty of other ways this can crop up, but those are the ones that seem the most common.

Anyway, this creates an *excellent* use case for property based testing, because if two functions are supposed
to always return the same answer, you can test that: Just call both functions with the same data and assert
that their answer is the same.

Lets look at this in the fancy algorithm case. Suppose we implemented [merge sort](
https://en.wikipedia.org/wiki/Merge_sort):

```python
def merge_sort(ls):
    if len(ls) <= 1:
        return ls
    else:
        k = len(ls) // 2
        return merge_sorted_lists(
            merge_sort(ls[:k]), merge_sort(ls[k:])
        )


def merge_sorted_lists(x, y):
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
    return result

```

We want a reference implementation to test it against, so lets also implement [bubble sort](
https://en.wikipedia.org/wiki/Bubble_sort):

```python
def bubble_sort(ls):
    ls = list(ls)
    needs_sorting = True
    while needs_sorting:
        needs_sorting = False
        for i in range(1, len(ls)):
            if ls[i - 1] > ls[i]:
                needs_sorting = True
                ls[i - 1], ls[i] = ls[i], ls[i - 1]
    return ls
```

These *should* always give the same answer,  so lets test that:

```python
@given(lists(integers()))
def test_bubble_sorting_is_same_as_merge_sorting(ls):
    assert bubble_sort(ls) == merge_sort(ls)
```

This gives us an error:

```
    @given(lists(integers()))
    def test_bubble_sorting_is_same_as_merge_sorting(ls):
>       assert bubble_sort(ls) == merge_sort(ls)
E       assert [0, 0] == [0]
E         Left contains more items, first extra item: 0
E         Use -v to get the full diff

foo.py:43: AssertionError
----- Hypothesis -----
Falsifying example: test_bubble_sorting_is_same_as_merge_sorting(ls=[0, 0])
```

What's happened is that we messed up our implementation of merge\_sorted\_lists, because we forgot
to include the elements left over in the other list once we've reached the end of one of them. As a
result we ended up losing elements from the list, a problem that our simpler implementation lacks.
We can fix this as follows and then the test passes:

```python
def merge_sorted_lists(x, y):
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

This technique combines especially well with 
[Hypothesis's stateful testing]({{site.url}}{% post_url 2016-04-19-rule-based-stateful-testing %}), because
you can use it to then test different implementations of complex APIs. For example, Hypothesis uses this
property together with stateful testing to [verify that the different implementations of its example database
behave identically](https://github.com/HypothesisWorks/hypothesis-python/blob/master/tests/cover/test_database_agreement.py).
