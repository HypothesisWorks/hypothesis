---
layout: post
tags: technical python intro
date: 2016-08-19 10:00
title: Generating recursive data
published: true
author: drmaciver
---

Sometimes you want to generate data which is *recursive*.
That is, in order to draw some data you may need to draw
some more data from the same strategy. For example we might
want to generate a tree structure, or arbitrary JSON.

Hypothesis has the *recursive* function in the hypothesis.strategies
module to make this easier to do. This is an article about how to
use it.

<!--more-->

Lets start with a simple example of drawing tree shaped data:
In our example a tree is either a single boolean value (a leaf
node), or a tuple of two child trees. So a tree might be e.g. True,
or (False, True), or ((True, True), False), etc.

First off, it might not be obvious that you *need* the recursive
strategy. In principle you could just do this with composite:


```python
import hypothesis.strategies as st

@st.composite
def composite_tree(draw):
    return draw(st.one_of(
        st.booleans(),
        st.tuples(composite_tree(), composite_tree()),
    ))
```

If you try drawing examples from this you'll probably see one of
three scenarios:

1. You'll get a single boolean value
2. You'll get a very large tree
3. You'll get a RecursionError from a stack overflow

It's unlikely that you'll see any non-trivial small examples.

The reason for this is that this sort of recursion tends to
explode in size: If this were implemneted as a naive random
generation process then the expected size of the tree would
be infinite. Hypothesis has some built in limiters to stop
it ever trying to actually generate infinitely large amounts
of data, but it will still tend to draw trees that are very
large if they're not trivial, and it can't do anything about
the recursion problem.

So instead of using this sort of unstructured recursion,
Hypothesis exposes a way of doing recursion in a slightly more
structured way that lets it control the size of the
generated data much more effectively. This is the recursive
strategy.

In order to use the recursive strategy you need two parts:

1. A base strategy for generating "simple" instances of the
   data that you want.
2. A function that takes a child strategy that generates data
   of the type you want and returns a new strategy generating
   "larger" instances.

So for example for our trees of booleans and tuples we could
use booleans() for the first and something for returning tuples
of children for the second:

```python
recursive_tree = st.recursive(
    st.booleans(), lambda children: st.tuples(children, children)
)
```

The way to think about the recursive strategy is that you're
repeatedly building up a series of strategies as follows:

```python
s1 = base
s2 = one_of(s1, extend(s1)
s3 = one_of(s2, extend(s2))
...

```

So at each level you augment the things from the previous
level with your extend function. Drawing from the resulting
recursive strategy then picks one of this infinite sequence
of strategies and draws from it (this isn't quite what happens
in practice, but it's pretty close).

The resulting strategy does a much better job of drawing small
and medium sized trees than our original composite based one
does, and should never raise a RecursionError:

```
>>> recursive_tree.example()
((False, True), ((True, True), False))

>>> recursive_tree.example()
((((False, False), True), False), False)

>>> recursive_tree.example()
(False, True)

>>> recursive_tree.example()
True

```

You can also control the size of the trees it draws with the
third parameter to recursive:

```
>>> st.recursive(st.booleans(), lambda children: st.tuples(children, children), max_leaves=2).example()
True

>>> st.recursive(st.booleans(), lambda children: st.tuples(children, children), max_leaves=2).example()
(True, False)
```

The max_leaves parameter controls the number of values drawn from
the 'base' strategy. It defaults to 50, which will tend to give you
moderately sized values. This helps keep example sizes under control,
as otherwise it can be easy to create extend functions which cause the
size to grow very rapidly.

In this particular example, Hypothesis will typically not hit the default,
but consider something like the following:

```
>>> st.recursive(st.booleans(), lambda children: st.lists(children, min_size=3)).example()
[[False,
  True,
  False,
  False,
  False,
  True,
  True,
  True,
  False,
  False,
  False,
  True,
  True,
  False],
 False,
 [False, True, False, True, False],
 [True, False, True, False, False, False]]  
```

In this case the size of the example will tend to push up against the max_leaves value
because extend() grows the strategy in size quite rapidly, so if you want larger
examples you will need to turn up max_leaves.
