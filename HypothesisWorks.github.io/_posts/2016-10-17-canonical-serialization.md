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
def test_encode_inverts_decode(s):
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

To rescue this, we might imagine we had some sort of function make\_canonical which
took an encoded data representation and replaced it with a canonical version of that (e.g.
by normalizing whitespace). The test could then look like this:


```python
@given(lists(tuples(characters(), integers(1, 10))))
def test_encode_inverts_decode(s):
    assert make_canonical(encode(decode(s))) == make_canonical(s)
```

But where would we get that make\_canonical function from? It's not something we really
want to write ourselves.

Fortunately we can put together the pieces we already have to define such a function
fairly easily. To see this, lets think about what properties make\_canonical should have.

The following seem reasonable:

1. encode should always produce canonical data. i.e. encode(t) == make_canonical(encode(t))
2. Canonical data should represent the same value. i.e. decode(s) == decode(make_canonical(s))

But we already know that decode(encode(t)) == t from our original property, so we have a
natural source of data that is the output of encode: We just decode the data and then
encode it again.

This gives us the following natural definition of make_canonical:

```python
def make_canonical(data):
    return encode(decode(data))
```

But this is nearly the same as the thing we were testing, so we can rewrite our test as:

```python
@given(lists(tuples(characters(), integers(1, 10))))
def test_encode_inverts_decode(s):
    assert make_canonical(make_canonical(s)) == make_canonical(s)
```

This property is called
being idempotent (annoyingly "idempotent" gets used to mean something subtly different
in most API design, but this is the original mathematical meaning).

It's less obviously necessary than the original one, and you can certainly
write encode/decode pairs that are arguably correct but don't have it (e.g. because
they change the order of keys in a dictionary, or include a timestamp or sequence
number in the output), but I think it's
still worth having and testing. Enforcing consistency like this both helps with debugging
when things go wrong and also tends to flush out other bugs along the way.

Even if you don't want to enforce this property, it highlights an important issue: You
do need *some* sort of testing of the decoder that doesn't just operate on output from
the encoder, because the encoder will potentially only output a relatively small subset
of the valid range of the format.

Often however you'll get the property for free. If the encode and decode functions
have the property that whenever x == y then f(x) == f(y), then this property automatically
holds, because make_canonical(x) is encode(decode(encode(decode(x)))), and we know from the
first property that decode(encode(t)) == t, so with t = decode(x) this expression is
encode(decode(x)), which is make_canonical(x) as required.

Most encode/decode pairs will have this property, but not all.

The easiest ways to fail to have it are to have side-effects (the aforementioned sequence
number or randomization), but even without side effects it's possible for it to fail
if equality doesn't capture every detail about the type. For example in
Python, if 1.0 was serialized as 1, then the two would compare equal and the property
would pass, but when re-encoding it might exhibit very different properties (although
you'd hope that it wouldn't). Another example is that in Python an OrderedDict and a
dict compare equal regardless of iteration order, which means that two apparently
equal types might encode to different things if they have different iteration orders
defined.

Ultimately these issues are probably quite niche. It's likely still worth testing for
this property, both because of these problems and also because often [mathematically
equivalent properties can still catch different issues]({{site.url}}{% post_url 2016-06-30-tests-as-complete-specifications %}),
but it's significantly less important than the more general property we started
with.

--------------------------------------

Thanks to [Georges Dubus](https://twitter.com/georgesdubus) who pointed out
the key insight behind the last section on this property following from the original
one.
