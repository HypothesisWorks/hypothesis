---
layout: post
tags: technical details faq python
date: 2016-08-31 00:00
title: How many times will Hypothesis run my test?
published: true
author: drmaciver
---

This is one of the most common first questions about Hypothesis.

People generally assume that the number of tests run will depend on
the specific strategies used, but that's generally not the case.
Instead Hypothesis has a fairly fixed set of heuristics to determine
how many times to run, which are mostly independent of the data
being generated.

But how many runs is *that*?

The short answer is 200. Assuming you have a default configuration
and everything is running smoothly, Hypothesis will run your test
200 times.

The longer answer is "It's complicated". It will depend on the exact
behaviour of your tests and the value of some settings. In this article
I'll try to clear up some of the specifics of which
[settings](http://hypothesis.readthedocs.io/en/latest/settings.html)
affect the answer and how.

<!--more-->

Advance warning: This is a set of heuristics built up over time. It's
probably not the best choice of heuristics, but it mostly seems
to work well in practice. It will hopefully be replaced with a
simpler set of rules at some point.

The first setting that affects how many times the test function will
be called is the timeout setting. This specifies a maximum amount of
time for Hypothesis to run your tests for. Once that has exceeded it
will stop and not run any more (note: This is a soft limit, so it
won't interrupt a test midway through).

The result of this is that slow tests may get run fewer times. By
default the timeout is one minute, which is high enough that most
tests shouldn't hit it, if your tests take somewhere in the region
of 300-400ms on average they will start to hit the timeout.

The timeout is respected regardless of whether the test passes or
fails, but other than that the behaviour for a passing test is
very different from a failing one.

### Passing tests

For the passing case there are two other settings that affect the
answer: max\_examples and max\_iterations.

In the normal case, max\_examples is what you can think of as the
number of test runs. The difference comes when you start using
assume or filter (and a few other cases).

Hypothesis distinguishes between a *valid* test run and an invalid one
- if assume has been called with a falsey value or at some point in
the generation process it got stuck (e.g. because filter couldn't
find any satisfying examples) it aborts the example and starts
again from the beginning. max\_examples counts only valid examples
while max\_iterations counts all examples, valid or otherwise. Some
duplicate tests will also be considered invalid (though Hypothesis
can't distinguish all duplicates. e.g. if you did
integers().map(lambda x: 1) it would think you had many distinct values
when you only had one). The default value for max_iterations
is currently 1000.

To see why it's important to have the max\_iterations limit,
consider something like:

```python
from hypothesis import given, assume, strategies as st

@given(st.integers())
def test_stuff(i):
    assume(False)
```

Then without a limit on invalid examples this would run forever.

Conversely however, treating valid examples specially is useful because
otherwise even casual use of assume would reduce the number of tests
you run, reducing the quality of your testing.

Another thing to note here is that the test with assume(False) will
actually fail, raising:

```
hypothesis.errors.Unsatisfiable: Unable to satisfy assumptions of hypothesis test_stuff. Only 0 examples considered satisfied assumptions
```

This is because of the min\_satisfying\_examples setting: If
Hypothesis couldn't find enough valid test cases then it will
fail the test rather than silently doing the wrong thing.

min\_satisfying\_examples will never increase the number of tests
run, only fail the test if that number of valid examples haven't
been run. If you're hitting this failure you can either turn it
down or turn the timeout or max\_iterations up. Better, you can
figure out *why* you're hitting that and fix it, because it's
probably a sign you're not getting much benefit out of Hypothesis.


### Failing tests

If in the course of normal execution Hypothesis finds an example
which causes your test to fail, it switches into shrinking mode.

Shrinking mode tries to take your example and produce a smaller
one. It ignores max\_examples and max\_iterations but respects
timeout. It also respects one additional setting: max\_shrinks.

max\_shrinks is the maximum number of *failing* tests that Hypothesis
will see before it stops. It may try any number of valid or invalid
examples in the course of shrinking. This is because failing
examples tend to be a lot rarer than passing or invalid examples,
so it makes more sense to limit based on that if we want to get
good examples out at the end.

Once Hypothesis has finished shrinking it will run your test once
more to replay it for display: In the final run only it will print
out the example and any notes, and will let the exception bubble
up to the test runner to be handled as normal.


### In Conclusion

"It's complicated".

These heuristics are probably not the best. They've evolved
over time, and are definitely not the ones that you or I would
obviously come up with if you sat down and designed the system
from scratch.

Fortunately, you're not expected to know these heuristics by heart
and mostly shouldn't have to. I'm working on a new feature that
will help show how many examples Hypothesis has tried and help
debug why it's stopped at that point. Hopefully it will be coming
in a release in the near future.
