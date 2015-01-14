================
 Hypothesis
================

Hypothesis is a library for property based testing. You write tests encoding some invariant
that you believe should always be true. Hypothesis then tries to prove you wrong.

For example:

.. code:: python

    from hypothesis import given

    @given(str)
    def test_strings_are_palindromic(x):
        assert x == ''.join(reversed(x))

You can then run this with your favourite testing framework and get the following
output:

.. code:: python

    AssertionError: assert '01' == '10'

Hypothesis not only finds you counterexamples it finds you *simple* counter-examples.

Hypothesis is inspired by and strongly based on libraries
for testing like `Quickcheck <http://en.wikipedia.org/wiki/QuickCheck>`_, but in comparison
has a distinctly dynamic flavour and a novel approach to data generation.

Its most direct ancestor is `ScalaCheck <https://github.com/rickynils/scalacheck>`_
from which it acquired its original approach to test case minimization (modern Hypothesis
uses a different one) and the concept of stateful testing.

Hypothesis is not itself a testing framework (though it may grow one). It is a library
for generating and minimizing data to falsify properties you believe to be true which
should be easy to integrate into any testing library you use. Development and testing of
Hypothesis itself is done with `Pytest <http://pytest.org/>`_ but there is no dependency
on it and you should be able to use it just as easily with any other testing library.

-------------------
Discussion and help
-------------------

If you use or are interested in using Hypothesis, we have `a mailing list <https://groups.google.com/forum/#!forum/hypothesis-users>`_.
Feel free to use it to ask for help, provide feedback, or discuss anything remotely
Hypothesis related at all.


------
Usage
------

The entry point you are mostly likely to use for Hypothesis, at least initially, are
the test annotations. These can be used to wrap any test method which is parametrized
by some argument and turn it into a randomized test.

The way this works is that you provide a specification for what sort of arguments you
want (currently only positional arguments are supported). Hypothesis then generates random
examples matching that specification. If any of them cause an exception then the test fails,
otherwise the test passes.

So the following test will pass:

.. code:: python

    @given(int, int)
    def test_int_addition_is_commutative(x, y):
        assert x + y == y + x

And the following will fail:

.. code:: python

    @given(str, str)
    def test_str_addition_is_commutative(x, y):
        assert x + y == y + x

With an error message something like:
 
.. code:: python

        x = '0', y = '1'
        @given(str, str)
        def test_str_addition_is_commutative(x, y):
            assert x + y == y + x
    E       assert '01' == '10'
    E         - 01
    E         + 10


(that's py.test output. You'll get whatever your test framework displays here)

Note that the examples produced are quite simple. This is because as well as generating
examples hypothesis knows how to simplify them. Once it's found an example that breaks
the test it will try to turn that into a simpler example - e.g. by deleting characters,
replacing them with simpler ones, etc.

Not all tests which pass are neccessarily consistently going to pass. By its nature,
hypothesis is a form of randomized testing. However if you have a flaky test as a result
of using hypothesis then what you have is a test that sometimes gives you false negatives:
If it's sometimes broken then the test genuinely is falsifiable, it's just that Hypothesis
struggles to find an example.

It can also be true that a test which is in theory falsifiable will always pass. For example:

.. code:: python

    @given(str)
    def test_str_addition_is_commutative(x):
        assert x != "I am the very model of a modern major general"

Hypothesis is not magic and does not do any introspection on your code to find
constants like this. All it knows is how to generate random instances and simplify values.
It has a lot of careful tuning to create quite interesting distributions of values that
should hit a lot of plausible areas, but when you're trying to find something as
improbable as a single value you'll probably fail.

You can also write conditional tests if the data doesn't exactly match the shape of
what you want. For example if you only want to test your code on short lists:

.. code:: python

    @given([int])
    def test_some_expensive_operation(xs):
        assume(len(xs) <= 10)
        result = do_some_expensive_operation(xs) 
        assert is_good(result)


The "assume" call will halt execution by throwing an exception if it's not satisfied.
This will not cause the test to fail. Instead Hypothesis will try to control its data
generation so that it avoids data that is likely to violate your requirements.

If however Hypothesis is unable to find enough examples satisfying your requirement it
will fail the test, throwing an Unsatisfiable exception. This means that the match between
your requirements and the generated data is too bad and you should redesign your test to
accomodate it better. For example in the above you could just truncate the list you get to
be of size 10 (though in this case Hypothesis should have no difficulty satisfying this requirement).

Because of the way Hypothesis handles minimization it's important that the
functions you test not depend on anything except their arguments as handled by
Hypothesis. If you want to test randomized algorithms you can ask Hypothesis to
provide you with a Random object:

.. code:: python

    @given(Random)
    def test_randint_in_range(random):
        assert 0 <= random.randint(0, 10) <= 9

This results in:

.. code:: python

        assert 0 <= random.randint(0, 10) <= 9
    E   assert 10 <= 9
    E    +  where 10 = <bound method RandomWithSeed.randint of Random(211179787414642638728970637875071360079)>(0, 10)


Note the seed is provided for you so you can easily reproduce the specific problem.

As the use of Random demonstrates, side effects on arguments given to you by Hypothesis
are completely fine. Hypothesis copies mutable data before giving it to you. For example the following is fine:

.. code:: python

    @given([int], int)
    def test_deletion_results_in_element_not_in_list(xs, y):
        assume(y in xs)
        xs.remove(y)
        assert y not in xs

Unfortunately it runs into a problem with py.test where pytest does display the
modified rather than original output (not entirely surprisingly), so the display
can be a bit confusing. This is something that will improve when Hypothesis gets
its own test runner. In the meantime though it will give you correct answers even
if the display is a bit off.

---------
Stability
---------

In one sense, Hypothesis should be considered highly stable. In another it should be considered highly unstable.

It's highly stable in the sense that it should mostly work very well. It's extremely solidly tested and while
there are almost certainly bugs lurking in it, as with any non-trivial codebase, they should be few and far
between.

It's highly unstable in that until it reaches 1.0 I will free to break the API. 1.0 will occur when I have all
the features I desperately want in here hammered out, have decided what the public vs private APIs look like and
generally consider it a "This is likely to work very well and is ready for widespread use".

In the mean time you should feel free to use it because it's great, but expect some incompatibilities between versions.

Everything in the intro section above should be considered a public API which I'm committed to supporting. Everything
else should be considered somewhat provisional. I'll make some effort to not break things that people are actively using
but if there's a really good reason to break something I will.

------------------
Supported versions
------------------

2.7.x, 3.3.x and 3.4.x are all fully supported and should work correctly. If you find a bug please
let me know and I will fix it.

Earlier than 2.7 will not work and will probably never be supported.

pypy, 3.1.x and 3.2.x will *probably* work but are not part of CI and likely have some quirks.
If you find a bug let me know but I make no promises I'll fix it if it's too hard to do. If you
really really need hypothesis on one of these and find a bug that is preventing you, we can have
a talk about what you can do to help me support them.

I have no idea if Hypothesis works on Jython, IronPython, etc. Do people really use those?

------------
Contributing
------------

I'm generally super happy to accept contributions. The main requirement is that the Travis
build passes.

This will in particular require you to maintain 100% branch coverage of the code and flake8
cleanliness. The Hypothesis build is quite strict.

I'm also generally delighted with people providing issues, documentation, usage reports, etc.
so if that sounds a bit too hardcore, don't worry! There's plenty of other things you can do.

-----------------
Internals
-----------------

The main function which drives everything that Hypothesis does is falsify. This is essentially
a slightly more direct version of what the test annotations above are doing: Given a function
and a specification for how to call that function it tries to produce a value that makes
that function return False.

.. code:: python

    In [1]: from hypothesis import falsify

    In [2]: falsify(lambda x,y,z: (x + y) + z == x + (y + z), float,float,float)
    Out[2]: (1.0, 1.0, 0.0387906318128606)

    In [3]: falsify(lambda x: sum(x) < 100, [int])
    Out[3]: ([6, 29, 65],)

    In [4]: falsify(lambda x: sum(x) < 100, [int,float])
    Out[4]: ([18.0, 82],)

    In [5]: falsify(lambda x: "a" not in x, str)
    Out[5]: ('a',)

    In [6]: falsify(lambda x: "a" not in x, {str})
    Out[6]: (set(['a']),)

If you ask it to falsify things that are true:

.. code:: python

    In [7]: falsify(lambda x: x + 1 == 1 + x, int)
    Unfalsifiable: Unable to falsify hypothesis lambda x: x + 1 == 1 + x

(that's real output. Hypothesis goes to some length to nicely display the functions
you're trying to falsify even when they're lambdas. This isn't always possible to do
but it manages a lot of the time)

And of course the same thing will happen if we ask it to falsify things that are false but hard to find:

.. code:: python

    In [8]: falsify(lambda x: x != "I am the very model of a modern major general", str)
    Unfalsifiable: Unable to falsify hypothesis lambda x: x != "I am the very model of a modern major general"


------------------
 Stateful testing
------------------

You can also use hypothesis for a more stateful style of testing, to generate
sequences of operations to break your code.

Considering the following broken implementation of a set:

.. code:: python

    class BadSet:
        def __init__(self):
            self.data = []

        def add(self, arg):
            self.data.append(arg)

        def remove(self, arg):
            for i in xrange(0, len(self.data)):
                if self.data[i] == arg:
                    del self.data[i]
                    break

        def contains(self, arg):
            return arg in self.data

Can we use hypothesis to demonstrate that it's broken? We can indeed!

We can put together a stateful test as follows:

.. code:: python

    class BadSetTester(StatefulTest):
        def __init__(self):
            self.target = BadSet()

        @step
        @requires(int)
        def add(self, i):
            self.target.add(i)
            assert self.target.contains(i)

        @step
        @requires(int)
        def remove(self,i):
            self.target.remove(i)
            assert not self.target.contains(i)

The @step decorator says that this method is to be used as a test step.
The @requires decorator says what argument types it needs when it is 
(you can omit @requires if you don't need any arguments).

We can now ask hypothesis for an example of this being broken:

.. code:: python

    In [7]: BadSetTester.breaking_example()
    Out[7]: (('add', 1), ('add', 1), ('remove', 1)]

What does this mean? It means that if we were to do:

.. code:: python

    x = BadSetTester()
    x.add(1)
    x.add(1)
    x.remove(1)

then we would get an assertion failure. Which indeed we would because the
assertion that removing results in the element no longer being in the set
would now be failing.

The stateful testing doesn't currently have a clean way for integrating it into
a test suite, but you can always just run it and make assertions about the output.

---------------------
 Adding custom types
---------------------

Hypothesis comes with support for a lot of common built-in types out of the
box, but you may want to test over spaces that involve your own data types.
The easiest way to accomplish this is to derive a ``SearchStrategy`` from an
existing strategy by extending ``MappedSearchStrategy``.

The following example defines a search strategy for ``Decimal``.
It maps ``int`` values by dividing 100, so the generated values have
two digits after the decimal point.

.. code:: python

    from decimal import Decimal
    from hypothesis.searchstrategy import MappedSearchStrategy

    class DecimalStrategy(MappedSearchStrategy):
        def pack(self, x):
            return Decimal(x) / 100

        def unpack(self, x):
            return int(x * 100)

You then need to register this strategy so that when you just refer to Decimal,
Hypothesis knows that this is the one you intend to use:

.. code:: python

    from hypothesis.strategytable import StrategyTable
    StrategyTable.default().define_specification_for(
      Decimal,
      lambda s, d: DecimalStrategy(
        mapped_strategy=s.strategy(float),
        descriptor=Decimal,
      ))

Given a StrategyTable x, this means that when you call x.strategy(Decimal), this will
call your lambda as f(x, Decimal), which will build the relevant strategy.

----------------
 Under the hood
----------------

~~~~~~~~~~~~~~~~~~
Example generation
~~~~~~~~~~~~~~~~~~

How does hypothesis work?

The core object of how hypothesis generates examples hypothesis is the SearchStrategy.
It knows how to explore a state space, and has the following operations:

* produce(random, parameter). Generate a random element of the state space given a value from its class of parameters.
* simplify(element). Return a generator over a simplified versions of this element.
* could_have_produced(element). Say whether it's plausible that this element was produced by this strategy.
* copy(element). Provide a mutation safe copy of this value. If the data is immutable it's OK to just return the value itself.

These satisfy the following invariants:

* Any element produced by produce must return true when passed to could_have_produced
* Any element for which could_have_produced returns true must not throw an exception when passed to simplify
* simplify(x) should return a generator over a sequence of unique values
* x == copy(x) (but not necessarily x is copy(x))

It also has a parameter. This is an object of type Parameter that controls random data generation. Parameters are used
to shape the search space to try to find better examples.

A mix of drawing parameters and calling produce is ued to explore the search space, producing a sequence of
novel examples. If we ever find one which falsifies the hypothesis we stop there and proceed to simplification. 
If after a configurable number of examples or length of time we have not found anything we stop and declare the
hypothesis unfalsifiable.

Simplification occurs as a straightforward greedy algorithm: If any of the elements produced by simplify(x) also
falsify the hypothesis, replace x with that and try again. Stop when no simplified version of x falsifies the
hypothesis.

~~~~~~~~~~~~~~~
Strategy lookup
~~~~~~~~~~~~~~~

Hypothesis converts from e.g. (Int, Int, Int) to a TupleStrategy by use of a StrategyTable object. You probably
just want to use the default one, available at StrategyTable.default()

You can define new strategies on it for descriptors from the above example.

If you want to customize the generation of your data you can create a new StrategyTable and tinker with it. Anything
defined on the default StrategyTable will be inherited by it.

Talk to me if you actually want to do this beyond simple examples like the above. It's all a bit confusing and should
probably be considered semi-internal until it gets a better API.

---------
 Testing
---------

This version of hypothesis has been tested using Python series 2.7,
3.3, 3.4.  Builds are checked with `travis`_:

.. _travis: https://travis-ci.org/DRMacIver/hypothesis

.. image:: https://travis-ci.org/DRMacIver/hypothesis.png?branch=master
   :target: https://travis-ci.org/DRMacIver/hypothesis
