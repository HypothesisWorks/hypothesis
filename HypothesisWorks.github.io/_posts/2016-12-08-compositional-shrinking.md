---
layout: post
tags: technical details python alternatives
date: 2016-12-08 9:00
title: Compositional shrinking
published: true
author: drmaciver
---

In [my last article about shrinking]({{site.url}}{% post_url 2016-12-05-integrated-shrinking %}),
I discussed the problems with basing shrinking on the type of the values
to be shrunk.

In writing it though I forgot that there was a halfway house which is
also somewhat bad (but significantly less so) that you see in a couple
of implementations.

This is when the shrinking is not type based, but still follows the
classic shrinking API that takes a value and returns a lazy list of
shrinks of that value. Examples of libraries that do this are
[theft](https://github.com/silentbicycle/theft) and
[QuickTheories](https://github.com/NCR-CoDE/QuickTheories).

This works reasonably well and solves the major problems with type
directed shrinking, but it's still somewhat fragile and importantly
does not compose nearly as well as the approaches that Hypothesis
or test.check take.

Ideally, as well as not being based on the types of the values being
generated, shrinking should not be based on the actual values generated
at all.

This may seem counter-intuitive, but it actually works pretty well.

<!--more-->

The way this works in Hypothesis or test.check works a bit differently,
so I'll hold off explaining on how this works for a minute, but lets
start with why this is important.

Consider the example from the last post:


```python

from hypothesis import given
from hypothesis.strategies import integers

even_numbers = integers().map(lambda x: x * 2)

@given(even_numbers)
def test_even_numbers_are_even(n):
  assert n % 2 == 0
```

We took a strategy and composed it with a function mapping over
the values that that strategy produced to get a new strategy.

Suppose the Hypothesis strategy implementation looked something
like the following:

```python

class SearchStrategy(object):
    def generate(self, random):
        raise NotImplementedErro()

    def shrink(self, value):
        return ()
```

i.e. we can generate a value and we can shrink a value that we've
previously generated. By default we don't know how to generate values
(subclasses have to implement that) and we can't shrink anything,
which subclasses are able to fix if they want or leave as is if
they're fine with that.

(This is in fact how a very early implementation of it looked)

This is essentially the approach taken by theft or QuickTheories,
and the problem with it is that under this implementation the
'map' function we used above is impossible to define in a way
that preserves shrinking: In order to shrink a generated value,
you need some way to invert the function you're composing with
(which is in general impossible even if your language somehow
exposed the facilities to do it, which it almost certainly
doesn't) so you could take the generated value, map it back
to the value that produced it, shrink that and then compose
with the mapping function.

Hypothesis and test.check both support even more complicated
composition of strategies (Hypothesis somewhat better than
test.check - both support the same operations, but Hypothesis's
underlying implementation works somewhat better for more
complicated compositions), but even the simplest of compositions
fails if you need to be able to shrink arbitrary values.

The key idea for fixing this is as follows: In order to shrink
*outputs* it almost always suffices to shrink *inputs*. Although
in theory you can get functions where simpler input leads to more
complicated output, in practice this seems to be rare enough
that it's OK to just shrug and accept more complicated test
output in those cases.

Given that, the way to shrink the output of a mapped strategy
is to just shrink the value generated from the first strategy
and feed it to the mapping function.

Which means that you need an API that can support that sort
of shrinking.

The way this works in test.check is that instead of generating
a single value it generates an entire (lazy) tree of values
with shrinks for them. See [Reid Draper's article on the
subject](http://reiddraper.com/writing-simple-check/) for slightly
more detail.

This supports mapping fairly easily: We just apply the mapping
function to the rose tree - both the initial generated value,
and all the shrunk child values.

Hypothesis's implementation is more complicated so will have to
wait for another article, but the key idea behind it is that
Hypothesis takes the "Shrinking outputs can be done by shrinking
inputs" idea to its logical conclusion and has a single unified
intermediate representation that *all* generation is based off.
Strategies can provide hints about possibly useful shrinks to
perform on that representation, but otherwise have very little
control over the shrinking process at all. This supports mapping
even more easily, because a strategy is just a function which
takes an IR object and returns a value, so the mapped strategy
just does the same thing and applies the mapping function.

Obviously I think Hypothesis's implementation is better, but
test.check's implementation is entirely respectable too and
is probably easier to copy right now if you're implementing
a property based testing system from scratch.

But I do think that whichever one you start from it's important
to take away the key idea: You can shrink outputs by shrinking
inputs, and strategies should compose in a way that preserves
shrinking.

The result is significantly more convenient to use because it
means that users will rarely or never have to write their own
shrinking functions, and there are fewer posssible places for
shrinking and generation to get out of sync.
