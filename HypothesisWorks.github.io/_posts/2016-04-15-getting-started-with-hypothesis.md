---
layout: post
tags: intro python
date: 2016-04-15 13:00
title: Getting started with Hypothesis
published: true
---


There seems to be a common impression that property based testing is really for when you have code that manipulates perfect platonic objects with elegant algebraic relationships between them.

And, well, don’t get me wrong. When you <em>do</em> have those, property-based testing really shines. It’s an incredibly powerful way to test them, and it works really well.

But… that’s mostly because this is a realm that is incredibly easy to test compared to the complexity of getting it right, so almost <em>anything</em> you can do to improve your testing will help it. It’s less that that’s what property based testing is good for, and more that it’s easy to try new things when you’re playing testing on easy mode.

Here’s a recipe for getting started when you’re <em>not</em> playing testing on easy mode.

<!--more-->

It consists of two steps:

1. Pick a function in your code base that you want to be better tested.
2. Call it with random data.

This will possibly require you to figure out how to generate your domain objects. Hypothesis <a href="http://hypothesis.readthedocs.org/en/release/data.html">has a pretty extensive library of tools for generating custom types</a>, but if you can try to start somewhere where the types you need aren’t <em>too</em> complicated to generate.

Chances are actually pretty good that you’ll find something wrong this way if you pick a sufficiently interesting entry point. For example, there’s a long track record of people trying to test interesting properties with their text handling and getting unicode errors when text() gives them something that their code didn’t know how to handle (The astral plane: It’s not just for D&amp;D).

You’ll probably get exceptions here you don’t care about. e.g. some arguments to functions may not be valid. Set up your test to ignore those.

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

This is already a pretty good starting point and does have a decent tendency to flush out bugs. You’ll often find cases where you forgot some boundary condition and your code misbehaves as a result. But there’s still plenty of room to improve.

There are now two directions you can go in from here:

1. Try to assert some things about the function’s result. Anything at all. What type is it? Can it be None? Does it have any relation at all to the input values that you can check? It doesn’t have to be clever – even very trivial properties are useful here.</li>
2. Start making your code more defensive.

The second part is probably the most productive one.

The goal is to turn faulty assumptions in your code into crashes instead of silent corruption of your application state. You can do this in a couple ways:

1. Add argument checking to your functions (Hypothesis uses a dedicated InvalidArgumentException for this case, but you can raise whatever errors you find appropriate).
2. Add a whole bunch of assertions into your code itself.
Even when it’s hard to reason about formal properties of your code, it’s usually relatively easy to add local properties, and assertions are a great way to encode them. I like <a href="http://blog.regehr.org/archives/1091">this post by John Regehr on the subject</a>.

This approach will make your code more robust even if you don’t find any bugs in it during testing (and you’ll probably find bugs in it during testing), and it gives you a nice easy route into property based testing by letting you focus on only one half of the problem at a time.

And, of course, if you’re still having trouble getting started with property-based testing, the other easy way is to persuade your company <a href="/training/">to hire us for a training course</a>. <a href="mailto:training@hypothesis.works">Drop us an email</a> if you’re interested.
