---
layout: post
tags: python details technical
date: 2016-12-10 11:00
title: How Hypothesis Works
published: true
author: drmaciver
---

Hypothesis has a very different underlying implementation to any other
property-based testing system. As far as I know, it's an entirely novel
design that I invented.

Central to this design is the following feature set which *every*
Hypothesis strategy supports automatically (the only way to break
this is by having the data generated depend somehow on external
global state):

1. All generated examples can be safely mutated
2. All generated examples can be saved to disk (this is important because
   Hypothesis remembers and replays previous failures).
3. All generated examples can be shrunk
4. All invariants that hold in generation must hold during shrinking (
   though the probability distribution can of course change, so things
   which are only supported with high probability may not be).

(Essentially no other property based systems manage one of these claims,
let alone all)

The initial mechanisms for supporting this were fairly complicated, but
after passing through a number of iterations I hit on a very powerful
underlying design that unifies all of these features.

It's still fairly complicated in implementation, but most of that is
optimisations and things needed to make the core idea work. More
importantly, the complexity is quite contained: A fairly small kernel
handles all of the complexity, and there is little to no additional
complexity (at least, compared to how it normally looks) in defining
new strategies, etc.

This article will give a high level overview of that model and how
it works.

<!--more-->

Hypothesis consists of essentially three parts, each built on top
of the previous:

1. A low level interactive byte stream fuzzer called *Conjecture*
2. A strategy library for turning Conjecture's byte streams into
   high level structured data.
3. A testing interface for driving test with data from Hypothesis's
   strategy library.

I'll focus purely on the first two here, as the latter is complex
but mostly a matter of plumbing.

The basic object exposed by Conjecture is a class called TestData,
which essentially looks like an open file handle you can read
bytes from:

```python

class TestData(object):
    def draw_bytes(self, n):
        ...
```

(note: The Python code in this article isn't an exact copy of what's
found in Hypothesis, but has been simplified for pedagogical reasons).

A strategy is then just an object which implements a single abstract
method from the strategy class:

```python

class SearchStrategy(object):
    def do_draw(self, data):
        raise NotImplementedError()
```

The testing interface then turns test functions plus the strategies
they need into something that takes a TestData object and returns
True if the test fails and False if it passes.

For a simple example, we can implement a strategy for unsigned
64-bit integers as follows:


```python

class Int64Strategy(object):
    def do_draw(self, data):
        return int.from_bytes(
            data.draw_bytes(8),
            byteorder='big', signed=False
        )

```

As well as returning bytes, draw_bytes can raise an exception
that stops the test. This is useful as a way to stop examples
from getting too big (and will also be necessary for shrinking,
as we'll see in a moment).

From this it should be fairly clear how we support saving and
mutation: Saving every example is possible because we can just
write the bytes that produced it to disk, and mutation is possible
because strategies are just returning values that we don't
in any way hang on to.

But how does shrinking work?

Well the key idea is the one I mentioned in
[my last article about shrinking
]({{site.url}}{% post_url 2016-12-08-compositional-shrinking %}) -
shrinking inputs suffices to shrink outputs. In this case the
input is the byte stream.

Once Hypothesis has found a failure it begins shrinking the
byte stream using a TestData object that looks like the following:

```python

class ShrinkingTestData(object):
    def __init__(self, data):
        self.data = data
        self.index = 0

    def draw_bytes(self, n):
        if self.index + n > len(self.data):
            raise StopTest()
        result = self.data[self.index:self.index+n]
        self.index += n
        return result
```

Shrinking now reduces to shrinking the byte array that gets
passed in as data, subject to the condition that our transformed
test function still returns True.

Shrinking of the byte array is designed to try to minimize it
according to the following rules:

1. Shorter is always simpler.
2. Given two byte arrays of the same length, the one which is
   lexicographically earlier (considering bytes as unsigned 8
   bit integers) is simpler.

You can imagine that some variant of [Delta Debugging](https://en.wikipedia.org/wiki/Delta_Debugging)
is used for the purpose of shrinking the byte array,
repeatedly deleting data and lowering bytes until no
byte may be deleted or lowered. It's a lot more complicated
than that, but I'm mostly going to gloss over that part
for now.

As long as the strategy is well written (and to some extent
even when it's not - it requires a certain amount of active
sabotage to create strategies that produce more complex data
given fewer bytes) this results in shrinks to the byte array
giving good shrinks to the generated data. e.g. our 64-bit
unsigned integers are chosen to be big endian so that
shrinking the byte data lexicographically shrinks the integer
towards zero.

In order to get really good deleting behaviour in our strategies
we need to be a little careful about how we arrange things, so
that deleting in the underlying bytestream corresponds to
deleting in generated data.

For example, suppose we tried to implement lists as follows:


```python

class ListStrategy(SearchStrategy):
    def __init__(self, elements):
        self.elements = elements

    def do_draw(self, data):
        n_elements = integers(0, 10).do_draw(
            self.elements)
        return [
            self.elements.do_draw(data)
            for _ in range(n_elements)
        ]
```

The problem with this is that deleting data doesn't actually
result in deleting elements - all that will happen is that
drawing will run off the end of the buffer. You can
potentially shrink n_elmements, but that only lets you
delete things from the end of the list and will leave a
bunch of left over data at the end if you do - if this is
the last data drawn that's not a problem, and it might be
OK anyway if the data usefully runs into the next strategy,
but it works fairly unreliably.

I am in fact working on an improvement to how shrinking works
for strategies that are defined like this - they're quite
common in user code, so they're worth supporting - but it's
better to just have deletion of elements correspond to
deletion of data in the underlying bytestream. We can do
this as follows:


```python

class ListStrategy(SearchStrategy):
    def __init__(self, elements):
        self.elements = elements

    def do_draw(self, data):
        result = []
        while booleans().do_draw(data):
            result.append(self.elements.do_draw(data))
        return result
```

We now draw lists as a series True, element,
True, element, ..., False, etc. So if you delete the
interval in the byte stream that starts with a True
and finishes at the end of an element, that just deletes
that element from the list and shifts everything afterwards
left one space.

Given some careful strategy design this ends up working
pretty well. It does however run into problems in two
minor cases:

1. It doesn't generate very good data
2. It doesn't shrink very well

Fortunately both of these are fixable.

The reason for the lack of good data is that Conjecture
doesn't know enough to produce a good distribution of bytes
for the specific special values for your strategy. e.g. in
our unsigned 64 bit integer examples above it can probably
guess that 0 is a special value, but it's not necessarily
obvious that e.g. focusing on small values is quite useful.

This gets worse as you move further away from things that
look like unsigned integers. e.g. if you're turning bytes
into floats, how is Conjecture supposed to know that
Infinity is an interesting value?

The simple solution is to allow the user to provide a
distribution hint:


```python

class TestData(object):
    def draw_bytes(self, n, distribution=None):
        ...
```

Where a distribution function takes a Random object
and a number of bytes.

This lets users specify the distribution of bytes. It
won't necessarily be respected - e.g. it certainly isn't
in shrinking, but the fuzzer can and does mutate the
values during generation too - but it provides a good
starting point which allows you to highlight special
values, etc.

So for example we could redefine our integer strategy
as:


```python

class Int64Strategy(object):
    def do_draw(self, data):
        def biased_distribution(random, n):
            if random.randint(0, 1):
                return random.randint(0, 100).to_bytes(
                    n, byteorder='big', signed=False
                )
            else:
                return uniform(random, n)
        return int.from_bytes(
            data.draw_bytes(8, biased_distribution),
            byteorder='big', signed=False
        )

```

Now we have a biased integer distribution which will
produce integers between 0 and 100 half the time.

We then use the strategies to generate our initial
buffers. For example we could pass in a TestData
implementation that looked like this:

```python

class GeneratingTestData(TestData):
    def __init__(self, random, max_bytes):
        self.max_bytes = max_bytes
        self.random = random
        self.record = bytearray()

    def draw_bytes(self, n, distribution):
        if n + len(self.record) > self.max_bytes:
            raise StopTest()
        result = distribution(self.random, n)
        self.record.extend(result)
        return result
```

This draws data from the provided distribution
and records it, so at the end we have a record of
all the bytes we've drawn so that we can replay
the test afterwards.

This turns out to be mostly enough. I've got some
pending research to replace this API with something
a bit more structured (the ideal would be that instead
of opaque distribution objects you draw from an explicit
mixture of grammars), but for the moment research on
big changes like that is side lined because nobody is
funding Hypothesis development, so I've not got very far
with it.

Initial designs tried to avoid this approach by using
data from the byte stream to define the distribution,
but this ended up producing quite opaque structures in
the byte stream that didn't shrink very well, and this
turned out to be simpler.

The second problem of it not shrinking well is also
fairly easily resolved: The problem is not that we
*can't* shrink it well, but that shrinking ends up
being slow because we can't tell what we need to
do: In our lists example above, the only way we
currently have to delete elements is to delete the
corresponding intervals, and the only way we have
to find the right intervals is to try *all* of them.
This potentially requires O(n^2) deletions to get the
right one.

The solution is just to do a bit more book keeping as we
generate data to mark useful intervals. TestData now
looks like this:

```python

class TestData(object):
    def start_interval(self):
        ...

    def stop_interval(self):
        ...

    def draw_bytes(self, n):
        ...


    def draw(self, strategy):
        self.start_interval()
        result = strategy.do_draw(self)
        self.stop_interval()
        return result
```


We then pass everything through data.draw instead
of strategy.do_draw to maintain this bookkeeping.

These mark useful boundaries in the bytestram that
we can try deleting: Intervals which don't cross a
value boundary are much more likely to be useful to
delete.

There are a large number of other details that are
required to make Hypothesis work: The shrinker and
the strategy library are both carefully developed
to work together, and this requires a fairly large
number of heuristics and special cases to make things
work, as well as a bunch of book keeping beyond the
intervals that I've glossed over.

It's not a perfect system, but it works and works well:
This has been the underlying implementation of Hypothesis
since the 3.0 relase in early 2016, and the switch over
was nearly transparent to end users: the previous
implementation was much closer to a classic QuickCheck
model (with a great deal of extra complexity to support
the full Hypothesis feature set).

In a lot of cases it even works better than heavily
customized solutions: For example, a benefit of the byte
based approach is that all parts of the data are
fully comprehensible to it. Often more structured
shrinkers get stuck in local minima because shrinking
one part of the data requires simultaneously shrinking
another part of the data, whileas Hypothesis can just
spot patterns in the data and speculatively shrink
them together to see if it works.

The support for chaining data generation together
is another thing that benefits here. In Hypothesis
you can chain strategies together like this:


```python

class SearchStrategy(object):
    def do_draw(self, data):
        raise NotImplementedError()

    def flatmap(self, bind):
        return FlatmappedStrategy(self, bind)


class FlatmappedStrategy(SearchStrategy):
    def __init__(self, base, bind):
        self.base = base
        self.bind = bind

    def do_draw(self, data):
        value = data.draw(self.base)
        return data.draw(self.bind(value))
```

The idea is that flatmap lets you chain strategy definitions together by
drawing data that is dependent on a value from other strategies.

This works fairly well in modern Hypothesis, but has historically (e.g. in
test.check or pre 3.0 Hypothesis) been a problem for integrated testing and
generation.

The reason this is normally a problem is that if you shrink the first value
you've drawn then you essentially *have* to invalidate the value drawn from
bind(value): There's no real way to retain it because it came from a completely
different generator. This potentially results in throwing away a lot of
previous work if a shrink elsewhere suddenly makes it to shrink the
initial value.

With the Hypothesis byte stream approach this is mostly a non-issue: As long as
the new strategy has roughly the same shape as the old strategy it will just
pick up where the old shrinks left off because they operate on the same
underlying byte stream.

This sort of structure *does* cause problems for Hypothesis if shrinking the
first value would change the structure of the bound strategy too much, but
in practice it usually seems to work out pretty well because there's enough
flexibility in how the shrinks happen that the shrinker can usually work past
it.

This model has proven pretty powerful even in its current form, but there's
also a lot of scope to expand it.

But hopefully not by too much. One of the advantages of the model in its
current form though is its simplicity. The [Hypothesis for Java
prototype](https://github.com/HypothesisWorks/hypothesis-java) was written in
an afternoon and is pretty powerful. The whole of the Conjecture implementation
in Python is a bit under a thousand significant lines of fairly portable code.
Although the strategy library and testing interface are still a fair bit of
work, I'm still hopeful that the Hypothesis/Conjecture approach is the tool
needed to bring an end to the dark era of property based testing libraries
that don't implement shrinking at all.
