---
layout: post
tags: python technical intro
date: 2017-04-05 10:00
title: Solving the Water Jug Problem from Die Hard 3 with TLA+ and Hypothesis
published: true
author: nchammas
---

_This post was originally published on [the author's personal site](http://nchammas.com/writing/how-not-to-die-hard-with-hypothesis).
It is reproduced here with permission from the author._

In the movie [Die Hard with a Vengeance](https://en.wikipedia.org/wiki/Die_Hard_with_a_Vengeance)
(aka Die Hard 3), there is
[this famous scene](https://www.youtube.com/watch?v=6cAbgAaEOVE) where
John McClane (Bruce Willis) and Zeus Carver (Samuel L. Jackson)
are forced to solve a problem or be blown up: Given a 3 gallon jug and
5 gallon jug, how do you measure out exactly 4 gallons of water?

<div style="text-align: center;">
<iframe
    width="560"
    height="315"
    src="https://www.youtube.com/embed/6cAbgAaEOVE?rel=0"
    frameborder="0"
    allowfullscreen>
</iframe>
<p>
(The video title is wrong. It's Die Hard 3.)
</p>
</div>

Apparently, you can solve this problem using a formal specification
language like [TLA+](https://en.wikipedia.org/wiki/TLA%2B). I don't know
much about this topic, but it appears that a [formal specification language](https://en.wikipedia.org/wiki/Formal_specification)
is much like a programming language in that it lets you describe the
behavior of a system. However, it's much more rigorous and builds
on mathematical techniques that enable you to reason more effectively
about the behavior of the system you're describing than you can with
a typical programming language.

In a recent discussion on Hacker News about TLA+,
I came across [this comment](https://news.ycombinator.com/item?id=13919251)
which linked to a fun and simple example
showing [how to solve the Die Hard 3 problem with TLA+](https://github.com/tlaplus/Examples/blob/master/specifications/DieHard/DieHard.tla).
I had to watch the first two lectures from [Leslie Lamport's video course on TLA+](http://lamport.azurewebsites.net/video/videos.html)
to understand the example well, but once I did I was reminded of the
idea of property-based testing and, specifically, [Hypothesis](http://hypothesis.works/).

So what's property-based testing? It's a powerful way of testing your
logic by giving your machine a high-level description of how your code
should behave and letting it generate test cases automatically to see
if that description holds. Compare that to traditional unit testing,
for example, where you manually code up specific inputs and outputs
and make sure they match.

## How not to Die Hard with Hypothesis

Hypothesis has an excellent implementation of property-based testing
[for Python](https://github.com/HypothesisWorks/hypothesis-python).
I thought to myself: I wonder if you can write that
Die Hard specification using Hypothesis? As it turns out, Hypothesis
supports [stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html),
and I was able to port the [TLA+ example](https://github.com/tlaplus/Examples/blob/master/specifications/DieHard/DieHard.tla)
to Python pretty easily:

```python
from hypothesis import note, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant


class DieHardProblem(RuleBasedStateMachine):
    small = 0
    big = 0

    @rule()
    def fill_small(self):
        self.small = 3

    @rule()
    def fill_big(self):
        self.big = 5

    @rule()
    def empty_small(self):
        self.small = 0

    @rule()
    def empty_big(self):
        self.big = 0

    @rule()
    def pour_small_into_big(self):
        old_big = self.big
        self.big = min(5, self.big + self.small)
        self.small = self.small - (self.big - old_big)

    @rule()
    def pour_big_into_small(self):
        old_small = self.small
        self.small = min(3, self.small + self.big)
        self.big = self.big - (self.small - old_small)

    @invariant()
    def physics_of_jugs(self):
        assert 0 <= self.small <= 3
        assert 0 <= self.big <= 5

    @invariant()
    def die_hard_problem_not_solved(self):
        note("> small: {s} big: {b}".format(s=self.small, b=self.big))
        assert self.big != 4


# The default of 200 is sometimes not enough for Hypothesis to find
# a falsifying example.
with settings(max_examples=2000):
    DieHardTest = DieHardProblem.TestCase
```

Calling `pytest` on this file quickly digs up a solution:

```
self = DieHardProblem({})

    @invariant()
    def die_hard_problem_not_solved(self):
        note("> small: {s} big: {b}".format(s=self.small, b=self.big))
>       assert self.big != 4
E       AssertionError: assert 4 != 4
E        +  where 4 = DieHardProblem({}).big

how-not-to-die-hard-with-hypothesis.py:17: AssertionError
----------------------------- Hypothesis -----------------------------
> small: 0 big: 0
Step #1: fill_big()
> small: 0 big: 5
Step #2: pour_big_into_small()
> small: 3 big: 2
Step #3: empty_small()
> small: 0 big: 2
Step #4: pour_big_into_small()
> small: 2 big: 0
Step #5: fill_big()
> small: 2 big: 5
Step #6: pour_big_into_small()
> small: 3 big: 4
====================== 1 failed in 0.22 seconds ======================
```

## What's Going on Here

The code and test output are pretty self-explanatory, but here's a
recap of what's going on:

We're defining a state machine. That state machine has an initial
state (two empty jugs) along with some possible transitions. Those
transitions are captured with the `rule()` decorator. The initial
state and possible transitions together define how our system works.

Next we define invariants, which are properties that must always hold
true in our system. Our first invariant, `physics_of_jugs`, says that
the jugs must hold an amount of water that makes sense. For example,
the big jug can never hold more than 5 gallons of water.

Our next invariant, `die_hard_problem_not_solved`, is where it gets
interesting. Here we're declaring that the problem of getting exactly
4 gallons in the big jug _cannot_ be solved. Since Hypothesis's job
is to test our logic for bugs, it will give our state machine a
thorough shake down and see if we ever violate our invariants.
In other words, we're basically goading Hypothesis into solving the
Die Hard problem for us.

I'm not entirely clear on how Hypothesis does its work, but I know
the basic summary is this: It takes the program properties we've
specified -- including things like rules, invariants, data types, and
function signatures -- and generates data or actions to probe the
behavior of our program. If Hypothesis finds a piece of data or
sequence of actions that get our program to violate its stated properties, it
tries to whittle that down to a _minimum falsifying example_---i.e.
something that exposes the same problem but with a minimum number of
steps. This makes it much easier for you to understand how Hypothesis
broke your code.

Hypothesis's output above tells us that it was able to violate the
`die_hard_problem_not_solved` invariant and provides us with a
minimal reproduction showing exactly how it did so. That reproduction
is our solution to the problem. It's also how McClane and Carver did
it in the movie!

## Final Thoughts

All in all, I was pretty impressed with how straightforward it was to
translate the TLA+ example into Python using Hypothesis. And when
Hypothesis spit out the solution, I couldn't help but smile. It's
pretty cool to see your computer essentially generate a program that
solves a problem for you. And the Python version of the Die Hard
"spec" is not much more verbose than the
original in TLA+, though TLA+'s notation for current vs. next value
(e.g. `small` vs. `small'`) is elegant and cuts out the need to have
variables like `old_small` and `old_big`.

I don't know how Hypothesis compares to TLA+ in a general sense. I've
only just started to learn about property-based testing and TLA+, and
I wonder if they have a place in the work that I do these days, which
is mostly Data Engineering-type stuff. Still, I found this little
exercise fun, and I hope you learned something interesting from it.

_Thanks to [Julia], [Dan], Laura, Anjana, and Cip for reading drafts
of this post._

[Julia]: http://jvns.ca/
[Dan]: https://danluu.com/
