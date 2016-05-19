---
layout: post
tags: intro python technical properties
date: 2016-04-15 13:00
title: Getting started with Hypothesis
published: true
author: drmaciver
---

Hypothesis will speed up your testing process and improve your software quality,
but when first starting out people often struggle to figure out exactly how to use it.

Until you're used to thinking in this style of testing, it's not always obvious what the invariants of your
code actually *are*, and people get stuck trying to come up with interesting ones to test.

Fortunately, there's a simple invariant which every piece of software should satisfy, and which can be
remarkably powerful as a way to uncover surprisingly deep bugs in your software.

<!--more-->

That invariant is simple: The software shouldn't crash. Or sometimes, it should only crash in defined
ways.

There is then a standard test you can write for most of your code that asserts this
invariant.

It consists of two steps:

1. Pick a function in your code base that you want to be better tested.
2. Call it with random data.

This style of testing is usually called *fuzzing*.

This will possibly require you to figure out how to generate your domain objects. Hypothesis
[has a pretty extensive library of tools for generating custom types]({{site.url}}{% post_url 2016-05-11-generating-the-right-data %})
but if you can, try to start somewhere where the types you need aren’t *too* complicated to generate.

Chances are actually pretty good that you’ll find something wrong this way if you pick a
sufficiently interesting entry point. For example, there’s a long track record of people trying to
test interesting properties with their text handling and getting unicode errors when text()
gives them something that their code didn’t know how to handle.

You’ll probably get exceptions here you don’t care about. e.g. some arguments to functions may not be valid.
Set up your test to ignore those.

So at this point you’ll have something like this:

```python
from hypothesis import given, reject


@given(some(), strategies())
def test_some_stuff(x, y):
    try:
        my_function(x, y)
    except (Ignorable, Exceptions):
        reject()
```

(reject simply filters out the example – you’re trying to find a large number of examples that don’t raise any of those exceptions).

This is already a pretty good starting point and does have a decent tendency to flush out bugs. You’ll often
find cases where you forgot some boundary condition and your code misbehaves as a result. But there’s still plenty of room to improve.

There are now two directions you can go in from here:

1. Try to assert some things about the function’s result. Anything at all. What type is it?
   Can it be None? Does it have any relation at all to the input values that you can check?
   It doesn’t have to be clever - even very trivial properties are useful here.
2. Start making your code more defensive.

The second part is probably the most productive one.

The goal is to turn faulty assumptions in your code into crashes instead of silent corruption of your application state. You can do this in a couple ways:

1. Add argument checking to your functions (Hypothesis uses a dedicated InvalidArgumentException for this case, but you can raise whatever errors you find appropriate).
2. Add a whole bunch of assertions into your code itself.
Even when it’s hard to reason about formal properties of your code, it’s usually relatively easy to add local properties, and assertions are a great way to encode them. John Regehr has [a good post on this subject](http://blog.regehr.org/archives/1091) if you want to know more about it.

This approach will make your code more robust even if you don’t find any bugs in it during testing (and you’ll probably find bugs in it during testing), and it gives you a nice easy route into property based testing by letting you focus on only one half of the problem at a time.

Once you think you've got the hang of this, a good next step is to start looking for 
[places with complex optimizations]({{site.url}}{% post_url 2016-04-29-testing-performance-optimizations %}) or
[Encode/Decode pairs]({{site.url}}{% post_url 2016-04-16-encode-decode-invariant %}) in
your code, as they're a fairly easy properties to test and are both rich sources of bugs.

And, of course, if you’re still having trouble getting started with Hypothesis, the other easy way is to persuade your company [to hire us for a training course](/training/). Drop us an email at [training@hypothesis.works](mailto:training@hypothesis.works])
