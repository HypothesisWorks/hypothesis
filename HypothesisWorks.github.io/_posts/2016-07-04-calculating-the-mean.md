---
layout: post
tags: technical python properties intro
date: 2016-07-04 00:00
title: Calculating the mean of a list of numbers
published: true
author: drmaciver
---

Consider the following problem:

You have a list of floating point numbers. No nasty tricks - these
aren't NaN or Infinity, just normal "simple" floating point numbers.

Now: Calculate the mean (average). Can you do it?

It turns out this is a hard problem. It's hard to get it even *close* to
right. Lets see why.

<!--more-->

Consider the following test case using Hypothesis:

```python
from hypothesis import given
from hypothesis.strategies import lists, floats

@given(lists(floats(allow_nan=False, allow_infinity=False)), min_size=1)
def test_mean_is_within_reasonable_bounds(ls):
    assert min(ls) <= mean(ls) <= max(ls)
```

This isn't testing much about correctness, only that the value of the
mean is within reasonable bounds for the list: There are a lot of
functions that would satisfy this without being the mean. min and max
both satisfy this, as does the median, etc.

However, almost nobody's implementation of the mean satisfies this.

To see why, lets write our own mean:

```python
def mean(ls):
    return sum(ls) / len(ls)
```

This seems reasonable enough - it's just the definition of the mean -
but it's wrong:

```
assert inf <= 8.98846567431158e+307
 +  where inf = mean([8.988465674311579e+307, 8.98846567431158e+307])
 +  and   8.98846567431158e+307 = max([8.988465674311579e+307, 8.98846567431158e+307])

Falsifying example: test_mean_is_within_reasonable_bounds(
    ls=[8.988465674311579e+307, 8.98846567431158e+307]
)
```

The problem is that finite floating point numbers may be large enough
that their sum overflows to infinity. When you then divide infinity by a
finite number you still get infinity, which is out of the range.

So to prevent that overflow, lets try to bound the size of our numbers
by the length *first*:

```python
def mean(ls):
    return sum(l / len(ls) for l in ls)
```

```
assert min(ls) <= mean(ls) <= max(ls)
assert 1.390671161567e-309 <= 1.390671161566996e-309
where 1.390671161567e-309 = min([1.390671161567e-309, 1.390671161567e-309, 1.390671161567e-309])
and   1.390671161566996e-309 = mean([1.390671161567e-309, 1.390671161567e-309, 1.390671161567e-309])

Falsifying example: test_mean_is_within_reasonable_bounds(
    ls=[1.390671161567e-309, 1.390671161567e-309, 1.390671161567e-309]
)
```

In this case the problem you run into is not overflow, but the lack of
precision of floating point numbers: Floating point numbers are only
exact up to powers of two times an integer, so dividing by three will
cause rounding errors. In this case we have the problem that (x / 3) * 3
may not be equal to x in general.

So now we've got a sense of why this might be hard. Lets see how
existing implementations do at satisfying this test.

First let's try numpy:

```python
import numpy as np

def mean(ls):
    return np.array(ls).mean()
```

This runs into the problem we had in our first implementation:

```
assert min(ls) <= mean(ls) <= max(ls)
assert inf <= 8.98846567431158e+307

where inf = mean([8.988465674311579e+307, 8.98846567431158e+307])
and   8.98846567431158e+307 = max([8.988465674311579e+307, 8.98846567431158e+307])

Falsifying example: test_mean_is_within_reasonable_bounds(
    ls=[8.988465674311579e+307, 8.98846567431158e+307]
)
```

There's also the new statistics module from Python 3.4. Unfortunately,
this is broken too
([this is fixed in 3.5.2](https://bugs.python.org/issue25177)):

```
OverflowError: integer division result too large for a float

Falsifying example: test_mean_is_within_reasonable_bounds(
    ls=[8.988465674311579e+307, 8.98846567431158e+307]
)
```

In the case where we previously overflowed to infinity this instead
raises an error. The reason for this is that internally the statistics
module is converting everything to the Fraction type, which is an
arbitrary precision rational type. Because of the details of where and
when they were converting back to floats, this produced a rational that
couldn't be readily converted back to a float.

It's relatively easy to write an implementation which passes this test
by simply cheating and not actually calculating the mean:

```python
def clamp(lo, v, hi):
    return min(hi, max(lo, v))

def mean(ls):
    return clamp(min(ls), sum(ls) / len(ls), max(ls))
```

i.e. just restricting the value to lie in the desired range.

However getting an actually correct implementation of the mean (which
*would* pass this test) is quite hard:

To see just how hard, here's a [30 page
paper on calculating the mean of two numbers](https://hal.archives-ouvertes.fr/file/index/docid/576641/filename/computing-midpoint.pdf).

I wouldn't feel obliged to read that paper if I were you. I *have* read
it and I don't remember many of the details.

This test is a nice instance of a general one: Once you've got the
[this code doesn't crash]({{site.url}}{% post_url 2016-04-15-getting-started-with-hypothesis %}),
tests working, you can start to layer on additional constraints on the
result value. As this example shows, even when the constraints you
impose are *very* lax it can often catch interesting bugs.

It also demonstrates a problem: Floating point mathematics is *very*
hard, and this makes it somewhat unsuitable for testing with Hypothesis.

This isn't because Hypothesis is *bad* at testing floating point code,
it's because it's good at showing you how hard programming actually is,
and floating point code is much harder than people like to admit.

As a result, you probably don't care about the bugs it will find:
Generally speaking most peoples' attitude to floating point errors is
"Eh, those are weird numbers, we don't really care about that. It's
probably good enough". Very few people are actually prepared to do the
required work of a numerical sensitivity analysis that accurate floating
point code.

I used to use this example a lot for demonstrating Hypothesis to people,
but because of these problems I tend not to anyway: Telling people about
bugs they're not going to want to  fix isn't going to get you bug fixes
or friends.

But it's worth knowing that this is a problem: Programming is really
hard, and ignoring the problems won't make it less hard. You can ignore
the correctness issues until they actually bite you, but it's best not
to be surprised when they do.

And it's also worth remembering the general technique here, because this
isn't just useful for floating point numbers: Most code can benefit from
this, and most of the time the bugs it tells you won't be nearly this
unpleasant.