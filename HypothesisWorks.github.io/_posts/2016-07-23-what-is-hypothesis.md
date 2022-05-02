---
layout: post
tags: python intro
date: 2016-07-24 00:00
title: What is Hypothesis?
published: true
author: drmaciver
---

Hypothesis is a library designed to help you write what are called
*property-based tests*.

The key idea of property based testing is that rather than writing a test
that tests just a single scenario, you write tests that describe a range
of scenarios and then let the computer explore the possibilities for you
rather than having to hand-write every one yourself.

In order to contrast this with the sort of tests you might be used to, when
talking about property-based testing we tend to describe the normal sort of
testing as *example-based testing*.

Property-based testing can be significantly more powerful than example based
testing, because it automates the most time consuming part of writing tests
- coming up with the specific examples - and will usually perform it better
than a human would. This allows you to focus on the parts that humans are
better at - understanding the system, its range of acceptable behaviours,
and how they might break.

You don't *need* a library to do property-based testing. If you've ever
written a test which generates some random data and uses it for testing,
that's a property-based test. But having a library can help you a lot,
making your tests easier to write, more robust, and better at finding
bugs. In the rest of this article we'll see how.

<!--more-->

### How to use it

The key object of Hypothesis is a *strategy*. A strategy is a recipe for
describing the sort of data you want to generate. The existence of a rich
and comprehensive strategy library is the first big advantage of Hypothesis
over a more manual process: Rather than having to hand-write generators
for the data you want, you can just compose the ones that Hypothesis
provides you with to get the data you want. e.g. if you want a lists of
floats, you just use the strategy lists(floats()). As well as being
easier to write, the resulting data will usually have a distribution
that is much better at finding edge cases than all but the most heavily
tuned manual implementations.

As well as the basic out of the box strategy implementations, Hypothesis
has a number of tools for composing strategies with user defined functions
and constraints, making it fairly easy to generate the data you want.

Note: For the remainder of this article I'll focus on the Hypothesis for
Python implementation. The Java implementation is similar, but has a number
of small differences that I'll discuss in a later article.

Once you know how to generate your data, the main entry point to Hypothesis
is the @given decorator. This takes a function that accepts some arguments
and turns it into a normal test function.

An important consequence of that is that Hypothesis is not itself a test
runner. It works inside your normal testing framework - it will work fine
with nose, py.test, unittest, etc. because all it does is expose a function
of the right name that the test runner can then pick up.

Using it with a py.test or nose style test looks like this:

```python
from mercurial.encoding import fromutf8b, toutf8b

from hypothesis import given
from hypothesis.strategies import binary

@given(binary())
def test_decode_inverts_encode(s):
    assert fromutf8b(toutf8b(s)) == s 
```

(This is an example from testing Mercurial which found two bugs:
[4927](https://bz.mercurial-scm.org/show_bug.cgi?id=4927) and 
[5031](https://bz.mercurial-scm.org/show_bug.cgi?id=5031)).

In this test we are asserting that for any binary string, converting
it to its utf8b representation and back again should result in the
same string we started with. The @given decorator then handles
executing this test over a range of different binary strings without
us having to explicitly specify any of the examples ourself.

When this is first run, you will see an error that looks something
like this:

```
Falsifying example: test_decode_inverts_encode(s='\xc2\xc2\x80')

Traceback (most recent call last):
  File "/home/david/.pyenv/versions/2.7/lib/python2.7/site-packages/hypothesis/core.py", line 443, in evaluate_test_data
    search_strategy, test,
  File "/home/david/.pyenv/versions/2.7/lib/python2.7/site-packages/hypothesis/executors.py", line 58, in default_new_style_executor
    return function(data)
  File "/home/david/.pyenv/versions/2.7/lib/python2.7/site-packages/hypothesis/core.py", line 110, in run
    return test(*args, **kwargs)
  File "/home/david/hg/test_enc.py", line 8, in test_decode_inverts_encode
    assert fromutf8b(toutf8b(s)) == s
  File "/home/david/hg/mercurial/encoding.py", line 485, in fromutf8b
    u = s.decode("utf-8")
  File "/home/david/.pyenv/versions/2.7/lib/python2.7/encodings/utf_8.py", line 16, in decode
    return codecs.utf_8_decode(input, errors, True)
UnicodeDecodeError: 'utf8' codec can't decode byte 0xc2 in position 1: invalid continuation byte
```

Note that the falsifying example is quite small. Hypothesis has a
"simplification" process which runs behind the scenes and generally
tries to give the impression that the test simply failed with one
example that happened to be a really nice one.

Another important thing to note is that because of the random nature
of Hypothesis and because this bug is relatively hard to find, this
test may run successfully a couple of times before finding it.

However, once that happens, when we rerun the test it will keep failing
with the same example. This is because Hypothesis has a local test
database that it saves failing examples in. When you rerun the test,
it will first try the previous failure.

This is pretty important: It means that although Hypothesis is at its
heart random testing, it is *repeatable* random testing: A bug will
never go away by chance, because a test will only start passing if
the example that previously failed no longer failed.

(This isn't entirely true because a bug could be caused by random
factors such as timing or hash randomization. However in these cases
it's true for example-based testing as well. If anything Hypothesis
is *more* robust here because it will tend to find these cases with
higher probability).

Ultimately that's "all" Hypothesis does: It provides repeatability,
reporting and simplification for randomized tests, and it provides
a large library of generators to make it easier to write them.

Because of these features, the workflow is a huge improvement on
writing your own property-based tests by hand, and thanks to the
library of generators it's often even easier than writing your
own example based tests by hand.

### What now?

If you want to read more on the subject, there are a couple places
you could go:

* If you want to know more of the details of the process I described
  when a test executes, you can check out the
  [Anatomy of a test]({{site.url}}{% post_url 2016-04-16-anatomy-of-a-test %})
  article which will walk you through the steps in more detail.
* If you'd like more examples of how to use it, check out the rest of the
  [intro section]({{site.url}}/articles/intro/).

But really the best way to learn more is to try to use it!
As you've hopefully seen in this article, it's quite approachable to
get started with. Try writing some tests and see what happens.
