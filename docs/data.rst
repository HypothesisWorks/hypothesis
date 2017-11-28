=============================
What you can generate and how
=============================

*Most things should be easy to generate and everything should be possible.*

To support this principle Hypothesis provides strategies for most built-in
types with arguments to constrain or adjust the output, as well as higher-order
strategies that can be composed to generate more complex types.

This document is a guide to what strategies are available for generating data
and how to build them. Strategies have a variety of other important internal
features, such as how they simplify, but the data they can generate is the only
public part of their API.

Functions for building strategies are all available in the hypothesis.strategies
module. The salient functions from it are as follows:

.. automodule:: hypothesis.strategies
  :members:

.. _shrinking:

~~~~~~~~~
Shrinking
~~~~~~~~~

When using strategies it is worth thinking about how the data *shrinks*.
Shrinking is the process by which Hypothesis tries to produce human readable
examples when it finds a failure - it takes a complex example and turns it
into a simpler one.

Each strategy defines an order in which it shrinks - these aren't always
straightforward, and are somewhat subject to change, but are worth being aware
of.

Possibly the most important one to be aware of is
:func:`hypothesis.strategies.one_of`, which has a preference for values
produced by strategies earlier in its argument list. Most of the others should
largely "do the right thing" without you having to think about it.

~~~~~~~~~~~~~~~~~~~
Adapting strategies
~~~~~~~~~~~~~~~~~~~

Often it is the case that a strategy doesn't produce exactly what you want it
to and you need to adapt it. Sometimes you can do this in the test, but this
hurts reuse because you then have to repeat the adaption in every test.

Hypothesis gives you ways to build strategies from other strategies given
functions for transforming the data.

-------
Mapping
-------

``map`` is probably the easiest and most useful of these to use. If you have a
strategy ``s`` and a function ``f``, then an example ``s.map(f).example()`` is
``f(s.example())``, i.e. we draw an example from ``s`` and then apply ``f`` to it.

e.g.:

.. doctest::

    >>> lists(integers()).map(sorted).example()
    [-158104205405429173199472404790070005365, -131418136966037518992825706738877085689, -49279168042092131242764306881569217089, 2564476464308589627769617001898573635]

Note that many things that you might use mapping for can also be done with
:func:`~hypothesis.strategies.builds`.

.. _filtering:

---------
Filtering
---------

``filter`` lets you reject some examples. ``s.filter(f).example()`` is some
example of ``s`` such that ``f(example)`` is truthy.

.. doctest::

    >>> integers().filter(lambda x: x > 11).example()
    87034457550488036879331335314643907276
    >>> integers().filter(lambda x: x > 11).example()
    145321388071838806577381808280858991039

It's important to note that ``filter`` isn't magic and if your condition is too
hard to satisfy then this can fail:

.. doctest::

    >>> integers().filter(lambda x: False).example()
    Traceback (most recent call last):
        ...
    hypothesis.errors.NoExamples: Could not find any valid examples in 20 tries

In general you should try to use ``filter`` only to avoid corner cases that you
don't want rather than attempting to cut out a large chunk of the search space.

A technique that often works well here is to use map to first transform the data
and then use ``filter`` to remove things that didn't work out. So for example if
you wanted pairs of integers (x,y) such that x < y you could do the following:


.. doctest::

    >>> tuples(integers(), integers()).map(sorted).filter(lambda x: x[0] < x[1]).example()
    [-145066798798423346485767563193971626126, -19139012562996970506504843426153630262]

.. _flatmap:

----------------------------
Chaining strategies together
----------------------------

Finally there is ``flatmap``. ``flatmap`` draws an example, then turns that
example into a strategy, then draws an example from *that* strategy.

It may not be obvious why you want this at first, but it turns out to be
quite useful because it lets you generate different types of data with
relationships to each other.

For example suppose we wanted to generate a list of lists of the same
length:

.. code-block:: pycon

    >>> rectangle_lists = integers(min_value=0, max_value=10).flatmap(
    ... lambda n: lists(lists(integers(), min_size=n, max_size=n)))
    >>> find(rectangle_lists, lambda x: True)
    []
    >>> find(rectangle_lists, lambda x: len(x) >= 10)
    [[], [], [], [], [], [], [], [], [], []]
    >>> find(rectangle_lists, lambda t: len(t) >= 3 and len(t[0]) >= 3)
    [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    >>> find(rectangle_lists, lambda t: sum(len(s) for s in t) >= 10)
    [[0], [0], [0], [0], [0], [0], [0], [0], [0], [0]]

In this example we first choose a length for our tuples, then we build a
strategy which generates lists containing lists precisely of that length. The
finds show what simple examples for this look like.

Most of the time you probably don't want ``flatmap``, but unlike ``filter`` and
``map`` which are just conveniences for things you could just do in your tests,
``flatmap`` allows genuinely new data generation that you wouldn't otherwise be
able to easily do.

(If you know Haskell: Yes, this is more or less a monadic bind. If you don't
know Haskell, ignore everything in these parentheses. You do not need to
understand anything about monads to use this, or anything else in Hypothesis).


--------------
Recursive data
--------------

Sometimes the data you want to generate has a recursive definition. e.g. if you
wanted to generate JSON data, valid JSON is:

1. Any float, any boolean, any unicode string.
2. Any list of valid JSON data
3. Any dictionary mapping unicode strings to valid JSON data.

The problem is that you cannot call a strategy recursively and expect it to not just
blow up and eat all your memory.  The other problem here is that not all unicode strings
display consistently on different machines, so we'll restrict them in our doctest.

The way Hypothesis handles this is with the :py:func:`recursive` function
which you pass in a base case and a function that, given a strategy for your data type,
returns a new strategy for it. So for example:

.. doctest::

    >>> from string import printable; from pprint import pprint
    >>> json = recursive(none() | booleans() | floats() | text(printable),
    ... lambda children: lists(children) | dictionaries(text(printable), children))
    >>> pprint(json.example())
    {'': 'wkP!4',
     '\nLdy': None,
     '"uHuds:8a{h\\:694K~{mY>a1yA:#CmDYb': {},
     '#1J1': [')gnP',
              inf,
              ['6', 11881275561.716116, "v'A?qyp_sB\n$62g", ''],
              -1e-05,
              'aF\rl',
              [-2.599459969184803e+250, True, True, None],
              [True,
               '9qP\x0bnUJH5',
               3.0741121405774857e-131,
               None,
               '',
               -inf,
               'L&',
               1.5,
               False,
               None]],
     'cx.': None}
    >>> pprint(json.example())
    [5.321430774293539e+16, [], 1.1045114769709281e-125]
    >>> pprint(json.example())
    {'a': []}

That is, we start with our leaf data and then we augment it by allowing lists and dictionaries of anything we can generate as JSON data.

The size control of this works by limiting the maximum number of values that can be drawn from the base strategy. So for example if
we wanted to only generate really small JSON we could do this as:


.. doctest::

    >>> small_lists = recursive(booleans(), lists, max_leaves=5)
    >>> small_lists.example()
    True
    >>> small_lists.example()
    [False, False, True, True, True]
    >>> small_lists.example()
    True

.. _composite-strategies:

~~~~~~~~~~~~~~~~~~~~
Composite strategies
~~~~~~~~~~~~~~~~~~~~

The :func:`@composite <hypothesis.strategies.composite>` decorator lets you combine other strategies in more or less
arbitrary ways. It's probably the main thing you'll want to use for
complicated custom strategies.

The composite decorator works by giving you a function as the first argument
that you can use to draw examples from other strategies. For example, the
following gives you a list and an index into it:

.. doctest::

    >>> @composite
    ... def list_and_index(draw, elements=integers()):
    ...     xs = draw(lists(elements, min_size=1))
    ...     i = draw(integers(min_value=0, max_value=len(xs) - 1))
    ...     return (xs, i)

``draw(s)`` is a function that should be thought of as returning ``s.example()``,
except that the result is reproducible and will minimize correctly. The
decorated function has the initial argument removed from the list, but will
accept all the others in the expected order. Defaults are preserved.

.. doctest::

    >>> list_and_index()
    list_and_index()
    >>> list_and_index().example()
    ([-57328788235238539257894870261848707608], 0)

    >>> list_and_index(booleans())
    list_and_index(elements=booleans())
    >>> list_and_index(booleans()).example()
    ([True], 0)

Note that the repr will work exactly like it does for all the built-in
strategies: it will be a function that you can call to get the strategy in
question, with values provided only if they do not match the defaults.

You can use :func:`assume <hypothesis.assume>` inside composite functions:

.. code-block:: python

    @composite
    def distinct_strings_with_common_characters(draw):
        x = draw(text(), min_size=1)
        y = draw(text(alphabet=x))
        assume(x != y)
        return (x, y)

This works as :func:`assume <hypothesis.assume>` normally would, filtering out any examples for which the
passed in argument is falsey.


.. _interactive-draw:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Drawing interactively in tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There is also the :func:`~hypothesis.strategies.data` strategy, which gives you a means of using
strategies interactively. Rather than having to specify everything up front in
:func:`@given <hypothesis.given>` you can draw from strategies in the body of your test:

.. code-block:: python

    @given(data())
    def test_draw_sequentially(data):
        x = data.draw(integers())
        y = data.draw(integers(min_value=x))
        assert x < y

If the test fails, each draw will be printed with the falsifying example. e.g.
the above is wrong (it has a boundary condition error), so will print:

.. code-block:: pycon

    Falsifying example: test_draw_sequentially(data=data(...))
    Draw 1: 0
    Draw 2: 0

As you can see, data drawn this way is simplified as usual.

Test functions using the :func:`~hypothesis.strategies.data` strategy do not support explicit
:func:`@example(...) <hypothesis.example>`\ s.  In this case, the best option is usually to construct
your data with :func:`@composite <hypothesis.strategies.composite>` or the explicit example, and unpack this within
the body of the test.

Optionally, you can provide a label to identify values generated by each call
to ``data.draw()``.  These labels can be used to identify values in the output
of a falsifying example.

For instance:

.. code-block:: python

    @given(data())
    def test_draw_sequentially(data):
        x = data.draw(integers(), label='First number')
        y = data.draw(integers(min_value=x), label='Second number')
        assert x < y

will produce the output:

.. code-block:: pycon

    Falsifying example: test_draw_sequentially(data=data(...))
    Draw 1 (First number): 0
    Draw 2 (Second number): 0
