---
layout: post
tags: python intro 
date: 2016-04-16 06:00
title: The Encode/Decode invariant
published: true
---

One of the simplest types of invariant to find once you move past
[just fuzzing your code](/articles/getting-started-with-hypothesis/) is asserting that two
different operations should produce the same result, and one of the simplest instances of
*that* is looking for encode/decode pairs. That is, you have some function that takes a
value and encodes it as another value, and another that is supposed to reverse the process.

This is ripe for testing with Hypothesis because it has a natural completely defined
specification: Encoding and then decoding should be exactly the same as doing nothing.

Lets look at a concrete example. The following code is a lightly reformatted version of
an implementation of [Run Length Encoding](https://en.wikipedia.org/wiki/Run-length_encoding)
taken [from Rosetta Code](http://rosettacode.org/wiki/Run-length_encoding).

```python
def encode(input_string):
    count = 1
    prev = ''
    lst = []
    for character in input_string:
        if character != prev:
            if prev:
                entry = (prev, count)
                lst.append(entry)
            count = 1
            prev = character
        else:
            count += 1
    else:
        entry = (character, count)
        lst.append(entry)
    return lst


def decode(lst):
    q = ''
    for character, count in lst:
        q += character * count
    return q
```

We can test this using Hypothesis and py.test as follows:


```python

from hypothesis import given
from hypothesis.strategies import text

@given(text())
def test_decode_inverts_encode(s):
    assert decode(encode(s)) == s
```

This asserts what we described above: If we encode a string as run length encoded and then
decode it, we get back to where we started.

This test finds a bug, not through the actual invariant. Instead it finds one through pure
fuzzing: The code does not correctly handle the empty string.


```
Falsifying example: test_decode_inverts_encode(s='')

UnboundLocalError: local variable 'character' referenced before assignment
```

One of the nice features of testing invariants is that they incorporate the fuzzing you
could be doing anyway, more or less for free, so even trivial invariants can often
find interesting problems.

We can fix this bug by adding a guard to the encode function:

```python

if not input_string:
    return []
```

The test now passes, which isn't very interesting, so lets break the code. We'll delete
a line from our implementation of encode which resets the count when the character changes:


```python

def encode(input_string):
    if not input_string:
        return []
    count = 1
    prev = ''
    lst = []
    for character in input_string:
        if character != prev:
            if prev:
                entry = (prev, count)
                lst.append(entry)
            # count = 1  # Missing reset operation
            prev = character
        else:
            count += 1
    else:
        entry = (character, count)
        lst.append(entry)
    return lst
```

Now the test fails:

```
    @given(text())
    def test_decode_inverts_encode(s):
>       assert decode(encode(s)) == s
E       assert '1100' == '110'
E         - 1100
E         ?    -
E         + 110

test_encoding.py:35: AssertionError
------------------------------------ Hypothesis ------------------------------------ 
Falsifying example: test_decode_inverts_encode(s='110')

```

Not resetting the count did indeed produce unintended data that doesn't translate back
to the original thing.

Encode/decode loops like this are *very* common, because you will frequently want to
serialize your domain objects to other representations - into forms, into APIs, into
the database, and these are things that are so integral to your applications that it's
worth getting all the edge cases right.

Other examples of this:

* [This talk by Matt Bacchman](https://speakerdeck.com/bachmann1234/property-based-testing-hypothesis)
  in which he discovers an eccentricity of formats for dates.
* Mercurial bugs [4927](https://bz.mercurial-scm.org/show_bug.cgi?id=4927) and [5031](https://bz.mercurial-scm.org/show_bug.cgi?id=5031)
  were found by applying this sort of testing to their internal UTF8b encoding functions.
* This [issue in qutebrowser's Javascript escaping](https://github.com/The-Compiler/qutebrowser/commit/24a71e5c2ebbffd9021694f32fa9ec51d0046d5a)
  was found with [this test](https://github.com/The-Compiler/qutebrowser/blob/24a71e5c2ebbffd9021694f32fa9ec51d0046d5a/tests/unit/browser/test_webelem.py#L652).
  This issue was particularly obscure and was only found because Hypothesis's text strategy became better at finding edge cases.
