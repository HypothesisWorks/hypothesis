---
layout: post
tags: technical python properties
date: 2016-05-29 21:00
title: Testing Configuration Parameters
published: true
author: drmaciver
---

A lot of applications end up growing a complex configuration system,
with a large number of different knobs and dials you can turn to change
behaviour. Some of these are just for performance tuning, some change
operational concerns, some have other functions.

Testing these is tricky. As the number of parameters goes up, the number
of possible configuration goes up exponentially. Manual testing of the
different combinations quickly becomes completely unmanageable, not
to mention extremely tedious.

Fortunately, this is somewhere where property-based testing in general
and Hypothesis in particular can help a lot.

<!--more-->

Configuration parameters almost all have one thing in common: For the
vast majority of things, they shouldn't change the behaviour. A
configuration parameter is rarely going to be a complete reskin of your
application.

This means that they are relatively easy to test with property-based
testing. You take an existing test - either one that is already using
Hypothesis or a normal example based test test - and you vary some
configuration parameters and make sure the test still passes.

This turns out to be remarkably effective. Here's an example where I
used this technique and found some bugs in the [Argon2](
https://github.com/P-H-C/phc-winner-argon2) password hashing library,
using [Hynek](https://hynek.me/)'s
[CFFI based bindings](https://github.com/hynek/argon2_cffi).

The idea of password hashing is straightforward: Given a password, you
can create a hash against which the password can be verified without
ever storing the password (after all, you're not storing passwords in
plain text on your servers, right?). Although straightforward to
describe, there's a lot of difficulty in making a good implementation
of this. Argon2 is a fairly recent one which won [the Password Hashing
Competition](https://password-hashing.net/) so should be fairly good.

We can verify that hashing works correctly fairly immediately using
Hypothesis:

```python
from argon2 import PasswordHasher

from hypothesis import given
import hypothesis.strategies as st


class TestPasswordHasherWithHypothesis(object):
    @given(password=st.text())
    def test_a_password_verifies(self, password):
        ph = PasswordHasher()
        hash = ph.hash(password)
        assert ph.verify(hash, password)
```

This takes an arbitrary text password, hashes it and verifies it against
the generated hash.

This passes. So far, so good.

But as you probably expected from its context here, argon2 has quite
a lot of different parameters to it. We can expand the test to vary
them and see what happens:

```python
from argon2 import PasswordHasher

from hypothesis import given, assume
import hypothesis.strategies as st


class TestPasswordHasherWithHypothesis(object):
    @given(
        password=st.text(),
        time_cost=st.integers(1, 10),
        parallelism=st.integers(1, 10),
        memory_cost=st.integers(8, 2048),
        hash_len=st.integers(12, 1000),
        salt_len=st.integers(8, 1000),
    )
    def test_a_password_verifies(
        self,
        password, time_cost, parallelism, memory_cost, hash_len, salt_len,
    ):
        assume(parallelism * 8 <= memory_cost)
        ph = PasswordHasher(
            time_cost=time_cost, parallelism=parallelism,
            memory_cost=memory_cost,
            hash_len=hash_len, salt_len=salt_len,
        )
        hash = ph.hash(password)
        assert ph.verify(hash, password)
```


These parameters are mostly intended to vary the difficulty of
calculating the hash. Honestly I'm not entirely sure what all of them
do. Fortunately for the purposes of writing this test, understanding is
optional.

In terms of how I chose the specific strategies to get there, I just
picked some plausible looking parameters ranges and adjusted them until
I wasn't getting validation errors (I did look for documentation, I
promise). The assume() call comes from reading the argon2 source to try
to find out what the valid range of parallelism was.

This ended up finding
[two bugs](https://github.com/hynek/argon2_cffi/issues/4), which I duly
reported to Hynek, but they actually turned out to be upstream bugs!

In both cases, a password would no longer validate against itself:


```
Falsifying example: test_a_password_verifies(
    password='', time_cost=1, parallelism=1, memory_cost=8, hash_len=4,
    salt_len=8,
)
```

```
Falsifying example: test_a_password_verifies(
    password='', time_cost=1, parallelism=1, memory_cost=8,
    hash_len=513, salt_len=8
)
```

(I found the second one by manually determining that the first bug
happened whenever salt_len < 12 and manually ruling that case out).

One interesting thing about both of these bugs is that they're actually
not bugs in the Python library but are both downstream bugs. I hadn't
set out to do that when I wrote these tests, but it nicely validates
that Hypothesis is rather useful for testing C libraries as well as
Python, given how easy they are to bind to with CFFI.
