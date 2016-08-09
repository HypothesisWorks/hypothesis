---
layout: post
tags: technical faq python
date: 2016-08-09 10:00
title: How do I use pytest fixtures with Hypothesis?
published: true
author: drmaciver
---

[pytest](http://doc.pytest.org/en/latest/) is a great test runner, and is the one
Hypothesis itself uses for testing (though Hypothesis works fine with other test
runners too).

It has a fairly elaborate [fixture system](http://doc.pytest.org/en/latest/fixture.html),
and people are often unsure how that interacts with Hypothesis. In this article we'll
go over the details of how to use the two together.

<!--more-->

Mostly, Hypothesis and py.test fixtures don't interact: Each just ignores the other's
presence.

When using a @given decorator, any arguments that are not provided in the @given
will be left visible in the final function:

```python
from hypothesis import given, strategies as st
from inspect import getargspec


@given(a=st.none(), c=st.none())
def test_stuff(a, b, c, d):
    pass


print(getargspec(test_stuff))
```

This then outputs the following:

```
ArgSpec(args=['b', 'd'], varargs=None, keywords=None, defaults=None)
```

We've hidden the arguments 'a' and 'c', but the unspecified arguments 'b' and 'd'
are still left to be passed in. In particular, they can be provided as py.test
fixtures:

```python

from hypothesis import given, strategies as st
from pytest import fixture


@fixture
def stuff():
    return "kittens"


@given(a=st.none())
def test_stuff(a, stuff):
    assert a is None
    assert stuff == "kittens"
```

This also works if we want to use @given with positional arguments: 

```python
from hypothesis import given, strategies as st
from pytest import fixture


@fixture
def stuff():
    return "kittens"


@given(t.none())
def test_stuff(stuff, a):
    assert a is None
    assert stuff == "kittens"

```

The positional argument fills in from the right, replacing the 'a'
argument and leaving us with 'stuff' to be provided by the fixture.

Personally I don't usually do this because I find it gets a bit
confusing - if I'm going to use fixtures then I always use the named
variant of given. There's no reason you *can't* do it this way if
you prefer though.

@given also works fine in combination with parametrized tests:

```python
from hypothesis import given, strategies as st
import pytest


@pytest.mark.parametrize('stuff', [1, 2, 3])
@given(a=st.none())
def test_stuff(a, stuff):
    assert a is None
    assert 1 <= stuff <= 3
```

This will run 3 tests, one for each value for 'stuff'.

There is one unfortunate feature of how this interaction works though: In pytest
you can declare fixtures which do set up and tear down per function. These will
"work" with Hypothesis, but they will run once for the entire test function
rather than once for each time given calls your test function. So the following
will fail:

```python

from hypothesis import given, strategies as st
from inspect import getargspec
from pytest import fixture


counter = 0

@fixture(scope='function')
def stuff():
    global counter
    counter = 0


@given(a=st.none())
def test_stuff(a, stuff):
    global counter
    counter += 1
    assert counter == 1
```

The counter will not get reset at the beginning of each call to the test function,
so it will be incremented each time and the test will start failing after the
first call.

There currently aren't any great ways around this unfortunately. The best you can
really do is do manual setup and teardown yourself in your tests using
Hypothesis (e.g. by implementing a version of your fixture as a context manager).

Long-term, I'd like to resolve this by providing a mechanism for allowing fixtures
to be run for each example (it's probably not correct to have *every* function scoped
fixture run for each example), but for now it's stalled because it [requires changes
on the py.test side as well as the Hypothesis side](https://github.com/pytest-dev/pytest/issues/916)
and we haven't quite managed to find the time and place to collaborate on figuring
out how to fix this yet.
