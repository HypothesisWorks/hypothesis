---
layout: post
tags: technical details python alternatives
date: 2017-07-16 10:00
title: Moving Beyond Types
published: true
author: drmaciver
---

If you look at the original property-based testing library, the Haskell version of QuickCheck,
tests are very closely tied to types: The way you typically specify a property is by inferring
the data that needs to be generated from the types the test function expects for its arguments.

This is a bad idea.

<!--more-->

The first part of why I've talked about already.
[I've talked about already]({{site.url}}{% post_url 2016-12-05-integrated-shrinking %}) -
you don't want to tie the shrinking of the data to its type, because it makes testing
significantly more brittle.

But you could solve that and still have data generation be tied to type, and it would still
be a bad idea.

The reason for this is very simple: Often you want to generate something much more specific
than any value of a given type.

If you look at the [Hypothesis strategies module](https://hypothesis.readthedocs.io/en/latest/data.html)
and what you can generate, many of these look like types. But if you look closer, nearly
every single one of them has options to configure them to be more specific.

Consider something like the following:

```python
from hypothesis import given, strategies as st
from statistics import mean


@given(st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=1))
def test_mean_is_in_bounds(ls):
  assert min(ls) <= mean(ls) <= max(ls)
```

In this test we've restricted the domain we're testing on so we can focus on a property
that doesn't hold in generality. This often happens: The mean of an empty list is an
error, so that needs a special case test for it, and calculations with `NaN` or infinity
are special cases that don't always have a well-defined result and even when they do
don't necessarily satisfy this property.

This happens a lot: Frequently there are properties that only hold in some restricted
domain, and so you want more specific tests for that domain to complement your other
tests for the larger range of data.

When this happens you need tools to generate something more specific, and those requirements
don't match naturally to types.

Consider writing this code based on types instead:

```python
from hypothesis import infer, given, strategies as st
from statistics import mean
from typing import List


@given(ls=infer)
def test_mean_is_in_bounds(ls: List[float]):
  assert min(ls) <= mean(ls) <= max(ls)
```

(this code doesn't work at the time of this writing, but it will soon -
[the pull request to implement it](https://github.com/HypothesisWorks/hypothesis-python/pull/643)
is in fairly late-stage review).

But this doesn't do the right thing: We've dropped the conditions from the
previous test that our floats are all finite and our lists are all non-empty. So now
we have to add a precondition to make the test valid:

```python
from hypothesis import infer, given, assume, strategies as st
from statistics import mean
from typing import List
import math


@given(ls=infer)
def test_mean_is_in_bounds(ls: List[float]):
  assume(len(ls) > 1)
  assume(all(math.isfinite(x) for x in ls))
  assert min(ls) <= mean(ls) <= max(ls)
```

But this is now substantially longer and less readable than the original approach!

In Haskell, traditionally we would fix this with a newtype declaration which wraps the type.
We could find a newtype NonEmptyList and a newtype FiniteFloat and then say that we actually
wanted a NonEmptyList[FiniteFloat] there.

In Python we could probably do more or less the same thing, either by creating new wrapper
types or by subclassing list and float (which you shouldn't do. Subclassing builtins in Python
leads to really weird behaviour) if we wanted to save a few lines, but it's much more noisy.

But why should we bother? Especially if we're only using these in one test, we're not actually
interested in these types at all, and it just adds a whole bunch of syntactic noise when you
could just pass the data generators directly. Defining new types for the data you want to generate
is purely a workaround for a limitation of the API.

If you were working in a dependently typed language where you could already naturally express
this in the type system it *might* be OK (I don't believe such a language currently
exists - you can certainly express the non-emptiness in the type system of some
languages, but the constraints on the floats not so much). I'm sceptical of being able to
make it work well - you're unlikely to be able to automatically derive data generators in the
general case, which I suspect will leave you with a bunch of sharp edges. I would be interested
to see experiments in this direction though.

But it's not the situation with any of the current generation of languages and property based
testing libraries. Here, using data generators for this is a clear improvement, and just as well-typed
(in a statically typed language each data generator has a return type after all).

You *can* use dta generators directly in Haskell QuickCheck too, with an explicit
[forAll](https://hackage.haskell.org/package/QuickCheck-2.10.0.1/docs/Test-QuickCheck-Property.html#v:forAll)
but it's almost as awkward as the newtype approach, particularly if you want more than one
data generator (it's even more awkward if you want shrinking - you have to use forAllWithShrink and
explicitly pass a shrink function).

This is more or less intrinsic to the type based approach. If you want tinkering with the 
data generation to be non-awkward, starting from data generators needs to become the default.

And experience suggests that when you make customising the data generation easy, people do
it. It's nice to be able to be more specific in your testing, but if you make it too high
effort people either don't do it, or do it using less effective methods like adding
preconditions to tests (assume in Hypothesis, or `==>` in QuickCheck) which reduce
the quality of your testing.

Fortunately, it already *is* the default in most of the newer implementations of
property-based testing. The only holdouts are ones that directly copied Haskell QuickCheck. 

Originally this was making a virtue of a necessity - most of the implementations
which started off the trend of data generator first tests are either for dynamic languages
(e.g. Erlang, Clojure, Python) or languages with very weak type systems (e.g. C) where
type first is more or less impossible, but it's proven to be a much more usable design.

And it's perfectly compatible with static typing too. [Hedgehog](https://hackage.haskell.org/package/hedgehog)
is a relatively recent property-based testing library for Haskell that takes this approach,
and it works just as well in Haskell as it does in any language.

It's also perfectly compatible with being able to derive a data generator from a type
for the cases where you really want to. We saw a hint at that with the upcoming
Hypothesis implementation above. You could easily do the same by having something
like the following in Haskell (mimicking the type class of QuickCheck):

```haskell
class Arbitrary a where
  arbitrary :: Gen a
```

You can then simply use `arbitrary` like you would any other data generator. As far as I know
Hedgehog doesn't do this anywhere (but you can use QuickCheck's Arbitrary with
the hedgehog-quickcheck package), but in principle there's nothing stopping it.

Having this also makes it much easier to define new data generators. I'm unlikely to use the
support for `@given` much, but I'm much more excited that it will also
work with `builds`, which will allow for a fairly seamless transition between
inferring the default strategy for a type and writing a custom generator. You
will, for example, be able to do `builds(MyType)` and have every constructor
argument automatically filled in (if it's suitably annotated), but you can
also do e.g. `builds(MyType, some_field=some_generator)` to override a particular
default while leaving the others alone.

(This API is somewhere where the dynamic nature of Python helps a fair bit, but you
could almost certainly do something equivalent in Haskell with a bit more noise
or a bit more template Haskell)

So this approach doesn't have to be data generator-only, even if it's data generator first,
but if you're going to pick one the flexibility of the data generator based test specification
is hard to beat, regardless of how good your type system is.
