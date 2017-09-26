---
layout: post
tags: technical details python
date: 2017-09-26 12:00
title: When multiple bugs attack
published: true
author: drmaciver
---

When Hypothesis finds an example triggering a bug, it tries to shrink the example
down to something simpler that triggers it. This is a pretty common feature, and
most property-based testing libraries implement something similar (though there
are a number of differences between them). Stand-alone test case reducers are
also fairly common, as it's a useful thing to be able to do when reporting bugs
in external projects - rather than submitting a giant file triggering the bug,
a good test case reducer can often shrink it down to a couple of lines.

But there's a problem with doing this: How do you know that the bug you started
with is the same as the bug you ended up with?

This isn't just an academic question. [It's very common for the bug you started
with to slip to another one](https://blog.regehr.org/archives/1284).

Consider for example, the following test:

```python
from hypothesis import given, strategies as st

def mean(ls):
    return sum(ls) / len(ls)


@given(st.lists(st.floats()))
def test(ls):
    assert min(ls) <= mean(ls) <= max(ls)
```

This has a number of interesting ways to fail: We could pass `NaN`, we could
pass `[-float('inf'), +float('inf')]`, we could pass numbers which trigger a
precision error, etc.

But after test case reduction, we'll pass the empty list and it will fail
because we tried to take the min of an empty sequence.

This isn't necessarily a huge problem - we're still finding a bug after all
(though in this case as much in the test as in the code under test) -
and sometimes it's even desirable - you find more bugs this way, and sometimes
they're ones that Hypothesis would have missed - but often it's not, and an
interesting and rare bug slips to a boring and common one.

Historically Hypothesis has had a better answer to this than most - because
of the Hypothesis example database, all intermediate bugs are saved and a
selection of them will be replayed when you rerun the test. So if you fix
one bug then rerun the test, you'll find the other bugs that were previously
being hidden from you by that simpler bug.

But that's still not a great user experience - it means that you're not getting
nearly as much information as you could be, and you're fixing bugs in
Hypothesis's priority order rather than yours. Wouldn't it be better if Hypothesis
just told you about all of the bugs it found and you could prioritise them yourself?

Well, as of Hypothesis 3.29.0, released a few weeks ago, now it does!

If you run the above test now, you'll get the following:

```
Falsifying example: test(ls=[nan])
Traceback (most recent call last):
  File "/home/david/hypothesis-python/src/hypothesis/core.py", line 671, in run
    print_example=True, is_final=True
  File "/home/david/hypothesis-python/src/hypothesis/executors.py", line 58, in default_new_style_executor
    return function(data)
  File "/home/david/hypothesis-python/src/hypothesis/core.py", line 120, in run
    return test(*args, **kwargs)
  File "broken.py", line 8, in test
    def test(ls):
  File "/home/david/hypothesis-python/src/hypothesis/core.py", line 531, in timed_test
    result = test(*args, **kwargs)
  File "broken.py", line 9, in test
    assert min(ls) <= mean(ls) <= max(ls)
AssertionError

Falsifying example: test(ls=[])
Traceback (most recent call last):
  File "/home/david/hypothesis-python/src/hypothesis/core.py", line 671, in run
    print_example=True, is_final=True
  File "/home/david/hypothesis-python/src/hypothesis/executors.py", line 58, in default_new_style_executor
    return function(data)
  File "/home/david/hypothesis-python/src/hypothesis/core.py", line 120, in run
    return test(*args, **kwargs)
  File "broken.py", line 8, in test
    def test(ls):
  File "/home/david/hypothesis-python/src/hypothesis/core.py", line 531, in timed_test
    result = test(*args, **kwargs)
  File "broken.py", line 9, in test
    assert min(ls) <= mean(ls) <= max(ls)
ValueError: min() arg is an empty sequence

You can add @seed(67388524433957857561882369659879357765) to this test to reproduce this failure.
Traceback (most recent call last):
  File "broken.py", line 12, in <module>
    test()
  File "broken.py", line 8, in test
    def test(ls):
  File "/home/david/hypothesis-python/src/hypothesis/core.py", line 815, in wrapped_test
    state.run()
  File "/home/david/hypothesis-python/src/hypothesis/core.py", line 732, in run
    len(self.falsifying_examples,)))
hypothesis.errors.MultipleFailures: Hypothesis found 2 distinct failures.
```

(The stack traces are a bit noisy, I know.
[We have an issue open about cleaning them up](https://github.com/HypothesisWorks/hypothesis-python/issues/848)).

All of the different bugs are minimized simultaneously and take full advantage of Hypothesis's
example shrinking, so each bug is as easy (or hard) to read as if it were the only bug we'd found.

This isn't perfect: The heuristic we use for determining if two bugs are the same is whether they
have the same exception type and the exception is thrown from the same line. This will necessarily
conflate some bugs that are actually different - for example, `[float('nan')]`,
`[-float('inf'), float('inf')]` and `[3002399751580415.0, 3002399751580415.0, 3002399751580415.0]`
each trigger the assertion in the test, but they are arguably "different" bugs.

But that's OK. The heuristic is deliberately conservative - the point is not that it can
distinguish whether any two examples are the same bug, just that any two examples it distinguishes
are different enough that it's interesting to show both, and this heuristic definitely manages that.

As far as I know this is a first in property-based testing libraries (though something like it is
common in fuzzing tools, and [theft is hot on our tail with something similar](
https://github.com/silentbicycle/theft/compare/develop-failure_tagging)) and there's been
[some interesting related but mostly orthogonal research](
http://www.cse.chalmers.se/~nicsma/papers/more-bugs.pdf) in Erlang QuickCheck.

It was also surprisingly easy.

A lot of things went right in writing this feature, some of them technical, some of them social,
somewhere in between.

The technical ones are fairly straightforward: Hypothesis's core model turned out to be very
well suited to this feature. Because Hypothesis has a single unified intermediate representation
which defines a total ordering for simplicity, adapting Hypothesis to shrink multiple things at
once was quite easy - whenever we attempt a shrink and it produces a different bug than the one
we were looking for, we compare it to our existing best example for that bug and replace it if
the current one is better (or we've discovered a new bug). We then just repeatedly run the shrinking
process for each bug we know about until they've all been fully shrunk.

This is in a sense not surprising - I've been thinking about the problem of multiple-shrinking for
a long time and, while this is the first time it's actually appeared in Hypothesis, the current
choice of model was very much informed by it.

The social ones are perhaps more interesting. Certainly I'm very pleased with how they turned
out here.

The first is that this work emerged tangentially from
[the recent Stripe funded work](https://stripe.com/blog/hypothesis) - Stripe paid me
to develop some initial support for testing Pandas code with Hypothesis, and I observed
a bunch of bug slippage happening in the wild while I was testing that (it turns out there
are quite a lot of ways to trigger exceptions from Pandas - they weren't really Pandas
bugs so much as bugs in the Pandas integration, but they still slipped between several
different exception types), so that was what got me thinking about this problem again.

Not by accident, this feature also greatly simplified the implementation
of [the new deadline feature](https://hypothesis.readthedocs.io/en/latest/settings.html#hypothesis.settings.deadline)
that [Smarkets](https://smarkets.com/) funded, which was going to have to have a lot of
logic about how deadlines and bugs interacted, but all that went away as soon as we were
able to handle multiple bugs sensibly.

This has been a relatively consistent theme in Hypothesis development - practical problems
tend to spark related interesting theoretical developments. It's not a huge exaggeration
to say that the fundamental Hypothesis model exists because I wanted to support testing
Django nicely. So the recent funded development from Stripe and Smarkets has been a
great way to spark a lot of seemingly unrelated development and improve Hypothesis
for everyone, even outside the scope of the funded work.

Another thing that really helped here is our review process, and [the review from Zac
in particular](https://github.com/HypothesisWorks/hypothesis-python/pull/836).

This wasn't the feature I originally set out to develop. It started out life as a
much simpler feature that used much of the same machinery, and just had a goal of
avoiding slipping to new errors all together. Zac pushed back with some good questions
around whether this was really the correct thing to do, and after some experimentation
and feedback I eventually hit on the design that lead to displaying all of the errors.

Our [review handbook](https://github.com/HypothesisWorks/hypothesis-python/blob/master/guides/review.rst)
emphasises that code review is a collaborative design process, and I feel this was
a particularly good example of that. We've created a great culture of code review,
and we're reaping the benefits (and if you want to get in on it, we could always
use more people able and willing to do review...).

All told, I'm really pleased with how this turned out. I think it's a nice example
of getting a lot of things right up front and this resulting in a really cool new
feature.

I'm looking forward to seeing how it behaves in the wild. If you notice any
particularly fun examples, do [let me know](mailto:david@drmaciver.com), or write
up a post about them yourself!
