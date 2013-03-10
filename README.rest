================
 Hypothesis
================

Hypothesis is a library for falsifying its namesake.

The primary entry point into the library is the hypothesis.falsify method.

What does it do?

You give it a predicate and a specification for how to generate arguments to
that predicate and it gives you a counterexample.

Examples!

.. code:: python

    In [1]: from hypothesis import falsify

    In [2]: falsify(lambda x,y,z: (x + y) + z == x + (y +z), float,float,float)
    Out[2]: (1.0, 2.0507190744664223, -10.940188909437985)

    In [3]: falsify(lambda x: sum(x) < 100, [int])
    Out[3]: ([6, 29, 65],)

    In [4]: falsify(lambda x: sum(x) < 100, [int,float])
    Out[4]: ([18.0, 82],)

    In [12]: falsify(lambda x: "a" not in x, str)
    Out[12]: ('a',)

Sometimes we ask it to falsify things that are true:

.. code:: python

    In [13]: falsify(lambda x: x + 1 == 1 + x, int)
    Unfalsifiable: Unable to falsify hypothesis <function <lambda> at 0x2efb1b8>

of course sometimes we ask it to falsify things that are false but hard to find:

.. code:: python

    In [16]: falsify(lambda x: x != "I am the very model of a modern major general", str)
    Unfalsifiable: Unable to falsify hypothesis <function <lambda> at 0x2efb398>

It's not magic, and when the search space is large it won't be able to do very much
for hard to find examples.

How does it work?

Fundamentally it knows how to do two things with types: 

    1. Generate them
    2. Minimize them

The API for generation is that you give it a generator specification and a 
size parameter and it generates values of "about that size", for some completely 
unspecified interpretation of that meaning (each type is permitted to interpret 
it differently).

Mininimizing takes a value and returns an iterator over "minimized forms of that
value". Again for some completely unspecified and fuzzy meaning.

Falsification feeds various size parameters into the generation until it finds
a counter example it likes, then minimizes that counter-example in a depth first
manner to produce its end results. 

WARNING: This software should be considered super pre alpha. It probably works
pretty well, maybe, perhaps, but the API has had almost zero design gone into
it and is likely to change radically once I actually start thinking about what
it should look like.
