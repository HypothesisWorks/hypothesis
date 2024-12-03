==========
Strategies
==========

*Most things should be easy to generate and everything should be possible.*

To support this principle Hypothesis provides strategies for most built-in
types with arguments to constrain or adjust the output, as well as higher-order
strategies that can be composed to generate more complex types.

This document is a guide to what strategies are available for generating data
and how to build them. Strategies have a variety of other important internal
features, such as how they simplify, but the data they can generate is the only
public part of their API.

~~~~~~~~~~~~~~~
Core strategies
~~~~~~~~~~~~~~~

Functions for building strategies are all available in the hypothesis.strategies
module. The salient functions from it are as follows:

.. automodule:: hypothesis.strategies
  :members:
  :exclude-members: SearchStrategy

~~~~~~~~~~~~~~~~~~~~~~
Provisional strategies
~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: hypothesis.provisional
  :members:
  :exclude-members: DomainNameStrategy

.. _shrinking:

~~~~~~~~~
Shrinking
~~~~~~~~~

When using strategies it is worth thinking about how the data *shrinks*.
Shrinking is the process by which Hypothesis tries to produce human readable
examples when it finds a failure - it takes a complex example and turns it
into a simpler one.

Each strategy defines an order in which it shrinks - you won't usually need to
care about this much, but it can be worth being aware of as it can affect what
the best way to write your own strategies is.

The exact shrinking behaviour is not a guaranteed part of the API, but it
doesn't change that often and when it does it's usually because we think the
new way produces nicer examples.

Possibly the most important one to be aware of is
:func:`~hypothesis.strategies.one_of`, which has a preference for values
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

.. _mapping:

-------
Mapping
-------

``map`` is probably the easiest and most useful of these to use. If you have a
strategy ``s`` and a function ``f``, then an example ``s.map(f).example()`` is
``f(s.example())``, i.e. we draw an example from ``s`` and then apply ``f`` to it.

e.g.:

.. code-block:: pycon

    >>> lists(integers()).map(sorted).example()
    [-25527, -24245, -23118, -93, -70, -7, 0, 39, 40, 65, 88, 112, 6189, 9480, 19469, 27256, 32526, 1566924430]

Note that many things that you might use mapping for can also be done with
:func:`~hypothesis.strategies.builds`, and if you find yourself indexing
into a tuple within ``.map()`` it's probably time to use that instead.

.. _filtering:

---------
Filtering
---------

``filter`` lets you reject some examples. ``s.filter(f).example()`` is some
example of ``s`` such that ``f(example)`` is truthy.

.. code-block:: pycon

    >>> integers().filter(lambda x: x > 11).example()
    26126
    >>> integers().filter(lambda x: x > 11).example()
    23324

It's important to note that ``filter`` isn't magic and if your condition is too
hard to satisfy then this can fail:

.. code-block:: pycon

    >>> integers().filter(lambda x: False).example()
    Traceback (most recent call last):
        ...
    hypothesis.errors.Unsatisfiable: Could not find any valid examples in 20 tries

In general you should try to use ``filter`` only to avoid corner cases that you
don't want rather than attempting to cut out a large chunk of the search space.

A technique that often works well here is to use map to first transform the data
and then use ``filter`` to remove things that didn't work out. So for example if
you wanted pairs of integers (x,y) such that x < y you could do the following:


.. code-block:: pycon

    >>> tuples(integers(), integers()).map(sorted).filter(lambda x: x[0] < x[1]).example()
    [-8543729478746591815, 3760495307320535691]

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
    ...     lambda n: lists(lists(integers(), min_size=n, max_size=n))
    ... )
    >>> rectangle_lists.example()
    []
    >>> rectangle_lists.filter(lambda x: len(x) >= 10).example()
    [[], [], [], [], [], [], [], [], [], []]
    >>> rectangle_lists.filter(lambda t: len(t) >= 3 and len(t[0]) >= 3).example()
    [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    >>> rectangle_lists.filter(lambda t: sum(len(s) for s in t) >= 10).example()
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

The way Hypothesis handles this is with the :func:`~hypothesis.strategies.recursive`
strategy which you pass in a base case and a function that, given a strategy
for your data type, returns a new strategy for it. So for example:

.. code-block:: pycon

    >>> from string import printable
    ... from pprint import pprint
    >>> json = recursive(
    ...     none() | booleans() | floats() | text(printable),
    ...     lambda children: lists(children) | dictionaries(text(printable), children),
    ... )
    >>> pprint(json.example())
    [[1.175494351e-38, ']', 1.9, True, False, '.M}Xl', ''], True]
    >>> pprint(json.example())
    {'de(l': None,
     'nK': {'(Rt)': None,
            '+hoZh1YU]gy8': True,
            '8z]EIFA06^li^': 'LFE{Q',
            '9,': 'l{cA=/'}}

That is, we start with our leaf data and then we augment it by allowing lists and dictionaries of anything we can generate as JSON data.

The size control of this works by limiting the maximum number of values that can be drawn from the base strategy. So for example if
we wanted to only generate really small JSON we could do this as:


.. code-block:: pycon

    >>> small_lists = recursive(booleans(), lists, max_leaves=5)
    >>> small_lists.example()
    True
    >>> small_lists.example()
    [False]

.. _composite-strategies:

~~~~~~~~~~~~~~~~~~~~
Composite strategies
~~~~~~~~~~~~~~~~~~~~

The :func:`@composite <hypothesis.strategies.composite>` decorator lets
you combine other strategies in more or less
arbitrary ways. It's probably the main thing you'll want to use for
complicated custom strategies.

The composite decorator works by converting a function that returns one
example into a function that returns a strategy that produces such
examples - which you can pass to :func:`@given <hypothesis.given>`, modify
with ``.map`` or ``.filter``, and generally use like any other strategy.

It does this by giving you a special function ``draw`` as the first
argument, which can be used just like the corresponding method of the
:func:`~hypothesis.strategies.data` strategy within a test.  In fact,
the implementation is almost the same - but defining a strategy with
:func:`@composite <hypothesis.strategies.composite>` makes code reuse
easier, and usually improves the display of failing examples.

For example, the following gives you a list and an index into it:

.. code-block:: pycon

    >>> @composite
    ... def list_and_index(draw, elements=integers()):
    ...     xs = draw(lists(elements, min_size=1))
    ...     i = draw(integers(min_value=0, max_value=len(xs) - 1))
    ...     return (xs, i)
    ...

``draw(s)`` is a function that should be thought of as returning ``s.example()``,
except that the result is reproducible and will minimize correctly. The
decorated function has the initial argument removed from the list, but will
accept all the others in the expected order. Defaults are preserved.

.. code-block:: pycon

    >>> list_and_index()
    list_and_index()
    >>> list_and_index().example()
    ([15949, -35, 21764, 8167, 1607867656, -41, 104, 19, -90, 520116744169390387, 7107438879249457973], 0)

    >>> list_and_index(booleans())
    list_and_index(elements=booleans())
    >>> list_and_index(booleans()).example()
    ([True, False], 0)

Note that the repr will work exactly like it does for all the built-in
strategies: it will be a function that you can call to get the strategy in
question, with values provided only if they do not match the defaults.

You can use :func:`assume <hypothesis.assume>` inside composite functions:

.. code-block:: python

    @composite
    def distinct_strings_with_common_characters(draw):
        x = draw(text(min_size=1))
        y = draw(text(alphabet=x))
        assume(x != y)
        return (x, y)

This works as :func:`assume <hypothesis.assume>` normally would, filtering out any examples for which the
passed in argument is falsey.

Take care that your function can cope with adversarial draws, or explicitly rejects
them using the ``.filter()`` method or :func:`~hypothesis.assume` - our mutation
and shrinking logic can do some strange things, and a naive implementation might
lead to serious performance problems.  For example:

.. code-block:: python

    @composite
    def reimplementing_sets_strategy(draw, elements=st.integers(), size=5):
        # The bad way: if Hypothesis keeps generating e.g. zero,
        # we'll keep looping for a very long time.
        result = set()
        while len(result) < size:
            result.add(draw(elements))
        # The good way: use a filter, so Hypothesis can tell what's valid!
        for _ in range(size):
            result.add(draw(elements.filter(lambda x: x not in result)))
        return result

If :func:`@composite <hypothesis.strategies.composite>` is used to decorate a
method or classmethod, the ``draw`` argument must come before ``self`` or ``cls``.
While we therefore recommend writing strategies as standalone functions and using
the :func:`~hypothesis.strategies.register_type_strategy` function to associate
them with a class, methods are supported and the ``@composite`` decorator may be
applied either before or after ``@classmethod`` or ``@staticmethod``.
See :issue:`2578` and :pull:`2634` for more details.


.. _interactive-draw:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Drawing interactively in tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There is also the :func:`~hypothesis.strategies.data` strategy, which gives you a means of using
strategies interactively. Rather than having to specify everything up front in
:func:`@given <hypothesis.given>` you can draw from strategies in the body of your test.

This is similar to :func:`@composite <hypothesis.strategies.composite>`, but
even more powerful as it allows you to mix test code with example generation.
The downside of this power is that :func:`~hypothesis.strategies.data` is
incompatible with explicit :obj:`@example(...) <hypothesis.example>`\ s -
and the mixed code is often harder to debug when something goes wrong.

If you need values that are affected by previous draws but which *don't* depend
on the execution of your test, stick to the simpler
:func:`@composite <hypothesis.strategies.composite>`.

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

Optionally, you can provide a label to identify values generated by each call
to ``data.draw()``.  These labels can be used to identify values in the output
of a falsifying example.

For instance:

.. code-block:: python

    @given(data())
    def test_draw_sequentially(data):
        x = data.draw(integers(), label="First number")
        y = data.draw(integers(min_value=x), label="Second number")
        assert x < y

will produce the output:

.. code-block:: pycon

    Falsifying example: test_draw_sequentially(data=data(...))
    Draw 1 (First number): 0
    Draw 2 (Second number): 0
