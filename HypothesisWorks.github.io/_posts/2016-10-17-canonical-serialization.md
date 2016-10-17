---
layout: post
tags: python intro technical properties
date: 2016-10-17 06:00
title: Another invariant to test for encoders
published: true
author: drmaciver
---

[The encode/decode invariant]({{site.url}}{% post_url 2016-04-16-encode-decode-invariant %})
is one of the most important properties to know about for testing your code with Hypothesis
or other property-based testing systems, because it captures a very common pattern and is
very good at finding bugs.

But how do you go beyond it? If encoders are that common, surely there must be other things
to test with them?

<!--more-->

The first thing that people tend to try is to simply reverse the order of operations. Continuing
the same example from the encode/decode post, this would look something like this:

```python
from hypothesis import given
from hypothesis.strategies import lists, tuples, characters, integers


@given(lists(tuples(characters(), integers(1, 10))))
def test_decode_inverts_encode(s):
    assert encode(decode(s)) == s
```

But unlike the other way around, this test can fail for reasons that are not obviously
errors in the system under test. In particular this will fail with the example [('0', 1), ('0', 1)],
because this will be decoded into '00', which will then be encoded into [('0', 2)].

In general, it is quite common to have multiple non-canonical representations of data
when encoding: e.g. JSON has non-significant whitespace, an IP address has a wide range
of human readable representations, most compressors will evolve to improve their compression
over time but will still be able to handle compressed files made with old versions of
the code, etc.

So this test *shouldn't* be expected to pass.

You can try to rescue it by replacing == with some sort of semantic equality, but the best
sort of semantic equality is really just decode(x) == decode(y), so if you do that you mostly
just end up at the original way around.

But there is another interesting property that emerges out of this, from the idea that some
of these representations are "non-canonical": That you should be able to produce a single
canonical representation.

Fortunately you don't have to write much new code to do this, because there's a natural
choice: The output of your encoder.

So we can define a function as follows that takes a serialized representation and outputs
a canonical form:

```python
def make_canonical(data):
    return encode(decode(data))
```

Once you have that, the interesting property you can test is this: That the canonical
version of canonical data is the same as what you've started with. This property is called
being idempotent (annoyingly "idempotent" gets used to mean something somewhat different
in most API design, but this is the original mathematical meaning):


```python
@given(lists(tuples(characters(), integers(1, 10))))
def test_make_canonical_is_idempotent(s):
    t = make_canonical(s)
    assert t == make_canonical(t)
```

This property is less obviously necessary than the original one, and you can certainly
write encode/decode pairs that are arguably correct but don't have it, but I think it's
still worth having and testing. Enforcing consistency like this both helps with debugging
when things go wrong and also tends to flush out other bugs along the way.

Even if you don't want to enforce this property, it highlights an important issue: You
do need *some* sort of testing of the decoder that doesn't just operate on output from
the encoder, because the encoder will potentially only output a relatively small subset
of the valid range of the format.
