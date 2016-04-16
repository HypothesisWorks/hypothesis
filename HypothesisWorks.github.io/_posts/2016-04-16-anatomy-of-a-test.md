---
layout: post
tags: python details
date: 2016-04-16 06:00
title: Anatomy of a Hypothesis Based Test
published: true
---

What happens when you run a test using Hypothesis? This article will help you understand.

<!--more-->

The Python version of Hypothesis uses *decorators* to transform a test function that
uses Hypothesis into one that does not.

Consider the following example using [py.test](http://pytest.org/latest/) style testing:

```python
from hypothesis.strategies import floats
from hypothesis import given


@given(floats(), floats())
def test_floats_are_commutative(x, y):
    assert x + y == y + x
```

The inner function takes two arguments, but the wrapping function defined by the @given
decorator takes none and may be invoked as a normal test:

```bash
python -m pytest test_floats.py
```

And we see the following output from py.test:

```
    @given(floats(), floats())
    def test_floats_are_commutative(x, y):
>       assert x + y == y + x
E       assert (0.0 + nan) == (nan + 0.0)

test_floats.py:7: AssertionError

Falsifying example: test_floats_are_commutative(x=0.0, y=nan)
```

The test fails, because [nan](https://en.wikipedia.org/wiki/NaN) is a valid floating
point number which is not equal to itself, and adding anything to nan yield nan.

When we ran this, Hypothesis invoked our test function with a number of randomly chosen
values for the arguments until it found one that failed. It then attempted to *shrink*
those values to produce a simpler one that would also fail.

If we wanted to see what it actually called our function with we can set the *verbosity
level*. This can either be done in code with settings, or by specifying an environment
variable:


```python
from hypothesis.strategies import floats
from hypothesis import given, settings, Verbosity


@settings(verbosity=Verbosity.verbose)
@given(floats(), floats())
def test_floats_are_commutative(x, y):
    assert x + y == y + x
```

```bash
HYPOTHESIS_VERBOSITY_LEVEL=verbose python -m pytest test_floats.py
```

Any verbosity values explicitly passed in settings will override whatever is set at
the environment level - the latter just provides a default.

Whichever one we choose, running it we'll see output something like the following:

```

Trying example: test_floats_are_commutative(x=-0.05851890381391768, y=-6.060045836901702e+300)
Trying example: test_floats_are_commutative(x=-0.06323690311413645, y=2.0324087421708266e-308)
Trying example: test_floats_are_commutative(x=-0.05738038380011458, y=-1.5993500302384265e-308)
Trying example: test_floats_are_commutative(x=-0.06598754758697359, y=-1.1412902232349034e-308)
Trying example: test_floats_are_commutative(x=-0.06472919559855002, y=1.7429441378277974e+35)
Trying example: test_floats_are_commutative(x=-0.06537123121982172, y=-8.136220566134233e-156)
Trying example: test_floats_are_commutative(x=-0.06016703321602157, y=1.9718842567475311e-215)
Trying example: test_floats_are_commutative(x=-0.055257588875432875, y=1.578407827448836e-308)
Trying example: test_floats_are_commutative(x=-0.06313031758042666, y=1.6749023021600297e-175)
Trying example: test_floats_are_commutative(x=-0.05886897920547916, y=1.213699633272585e+292)
Trying example: test_floats_are_commutative(x=-12.0, y=-0.0)
Trying example: test_floats_are_commutative(x=4.0, y=1.7976931348623157e+308)
Trying example: test_floats_are_commutative(x=-9.0, y=0.0)
Trying example: test_floats_are_commutative(x=-38.0, y=1.7976931348623157e+308)
Trying example: test_floats_are_commutative(x=-24.0, y=1.5686642754811104e+289)
Trying example: test_floats_are_commutative(x=-10.0, y=nan)
Traceback (most recent call last):
  ...
AssertionError: assert (-10.0 + nan) == (nan + -10.0)

Trying example: test_floats_are_commutative(x=10.0, y=nan)
Traceback (most recent call last):
  ...
AssertionError: assert (10.0 + nan) == (nan + 10.0)

Trying example: test_floats_are_commutative(x=0.0, y=nan)
Traceback (most recent call last):
  ...
AssertionError: assert (0.0 + nan) == (nan + 0.0)

Trying example: test_floats_are_commutative(x=0.0, y=0.0)
Trying example: test_floats_are_commutative(x=0.0, y=inf)
Trying example: test_floats_are_commutative(x=0.0, y=-inf)
Successfully shrunk example 5 times
Falsifying example: test_floats_are_commutative(x=0.0, y=nan)
```

Notice how the first failing example we got was ```-10.0, nan```, but Hypothesis was able
to turn that into 0.0, nan? That's the shrinking at work. For a simple case like this it
doesn't matter so much, but as your examples get complicated it's essential for making
Hypothesis's output easy to understand.


```
Trying example: test_floats_are_commutative(x=nan, y=0.0)
Traceback (most recent call last):
  ...
AssertionError: assert (nan + 0.0) == (0.0 + nan)

Trying example: test_floats_are_commutative(x=0.0, y=0.0)
Trying example: test_floats_are_commutative(x=inf, y=0.0)
Trying example: test_floats_are_commutative(x=-inf, y=0.0)
Successfully shrunk example 3 times
Falsifying example: test_floats_are_commutative(x=nan, y=0.0)
```

Now lets see what happens when we rerun the test:


```
Trying example: test_floats_are_commutative(x=0.0, y=nan)
Traceback (most recent call last):
  ...
AssertionError: assert (0.0 + nan) == (nan + 0.0)

Trying example: test_floats_are_commutative(x=0.0, y=0.0)
Trying example: test_floats_are_commutative(x=0.0, y=inf)
Trying example: test_floats_are_commutative(x=0.0, y=-inf)
Falsifying example: test_floats_are_commutative(x=0.0, y=nan)
```

Notice how the first example it tried was the failing example we had last time? That's
not an accident. Hypothesis has an example database where it saves failing examples.
When it starts up it looks for any examples it has seen failing previously and tries
them first before any random generation occurs. If any of them fail, we take that
failure as our starting point and move straight to the shrinking phase without any
generation.

The database format is safe to check in to version control if you like and will merge
changes correctly out of the box, but it's often clearer to specify the examples you
want to run every time in the source code as follows:


```python
from hypothesis.strategies import floats
from hypothesis import given, example


@example(0.0, float('nan'))
@given(floats(), floats())
def test_floats_are_commutative(x, y):
    assert x + y == y + x
```

Falsifying example: test_floats_are_commutative(x=0.0, y=nan)

If you run this in verbose mode it will print out
```Falsifying example: test_floats_are_commutative(x=0.0, y=nan)``` immediately and
not try to do any shrinks. Values you pass in via ```@example``` will not be shrunk.
This is partly a technical limitation but it can often be useful as well.

Explicitly provided examples are run before any generated examples.

So, to recap and elaborate, when you use a test written using Hypothesis:

1. Your test runner sees the decorated test as if it were a perfectly normal test function
   and invokes it.
2. Hypothesis calls your test function with each explicitly provided ```@example```. If one
   of these fails it stops immediately and bubbles up the exception for the test runner to handle.
3. Hypothesis reads examples out of its database of previously failing examples. If any of them
   fail, it stops there and proceeds to the shrinking step with that example. Otherwise it continues
   to the generation step.
4. Hypothesis tries generating a number of examples. If any of these raises an exception, it stops
   there and proceeds to the shrinking step. If none of them raise an exception, it silently returns
   and the test passes.
5. Hypothesis takes the previously failing example it's seen and tries to produce a "Simpler" version
   of it. Once it has found the simplest it possibly can, it saves that in the example database (in
   actual fact it saves every failing example in the example database as it shrinks, but the reasons
   why aren't important right now).
6. Hypothesis takes the simplest failing example and replays it, finally letting the test bubble up to
   the test runner.
