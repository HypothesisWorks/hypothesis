================
 Hypothesis
================

.. image:: https://badges.gitter.im/Join%20Chat.svg
   :alt: Join the chat at https://gitter.im/DRMacIver/hypothesis
   :target: https://gitter.im/DRMacIver/hypothesis?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge

Hypothesis is a library for property based testing in Python. You write tests encoding some invariant
that you believe should always be true for a variety of inputs and then Hypothesis tries to prove you wrong.

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

Hypothesis will also print out the example for you:

.. code:: python

    Falsifying example: x='01'

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

----------
Installing
----------

Hypothesis is `available on pypi as "hypothesis" <https://pypi.python.org/pypi/hypothesis>`_. You can install it with:

.. code:: bash

  pip install hypothesis

or 

.. code:: bash 

  easy_install hypothesis

If you want to install directly from the source code (e.g. because you want to make changes and install the changed version)
you can do this with:

.. code:: bash

  python setup.py install

You should probably run the tests first to make sure nothing is broken. You can do this with:

.. code:: bash

  python setup.py test 

(note that if they're not already installed this will try to install the test dependencies)

You may wish to do all of this in a `virtualenv <https://virtualenv.pypa.io/en/latest/>`_. For example:

.. code:: bash

  virtualenv venv
  source venv/bin/activate
  pip install hypothesis

Will create an isolated environment for you to try hypothesis out in without affecting your system
installed packages.

-------------------
Discussion and help
-------------------

If you use or are interested in using Hypothesis, we have `a mailing list <https://groups.google.com/forum/#!forum/hypothesis-users>`_.
We also have the IRC channel #hypothesis on freenode.

Feel free to use these to ask for help, provide feedback, or discuss anything remotely
Hypothesis related at all. When you do, please abide by the `Hacker School social rules <https://www.hackerschool.com/manual#sub-sec-social-rules>`_.

In particular this is an inclusive environment for people from a variety of backgrounds and skill levels. Prejudice and aggression are unwelcome and everyone
should be treated with respect.

I'll do my best to pay attention to peoples' behaviour, but if you see anyone violating these rules and I haven't noticed, please alert me and I'll deal with it. Usually I will simply ask people to modify their behaviour,
but for particularly severe transgressions, repeat offenders or those unwilling to change their ways I'll ban them from the community.

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

Running this then gives you:

.. code:: python

    Falsifying example: xs=[-10, -10], y=-10
        (...)
        assert y not in xs
    AssertionError

As a side note, the example is not as minimized as it could be. The reason for
this is that it would require simultaneous minimization of three values, which
is not something Hypothesis does currently - although it's obvious to a human
observer that the interesting thing about those -10 values is just that they're
the same, Hypothesis doesn't know anything about that and can't shrink it further.
It did however produce a pleasantly small list at least, which is the main goal -
examples will not necessarily be the simplest possible example but they should always
be simple enough to understand.

~~~~~~~~
Settings
~~~~~~~~

You can control the behaviour of Hypothesis by altering the settings
object. You can either do this by passing in an explicit settings object or
modifying the defaults:


.. code:: python

    import hypothesis.settings as hs

    hs.settings.default.max_examples = 500

    @given([int], settings=hs.Settings(timeout=10))
    def test_something(xs):
        something(hs)


Any changes you make to the default parameter will be inherited in any settings
you create unless you explicitly override them.

The three settings which are available as part of the stable API are:

* timeout - try not to take more than this many seconds to falsify
* max_examples - stop looking for new examples after this many have been considered
* derandomize - run in deterministic mode, where the random seed for each run is
  determined as a hash of the function to test. This allows you to run your builds
  in such a way that failure is not random. It does decrease their power somewhat
  in that it means they will never discover new examples, but it may make it
  better to use in some situations where you e.g. have a large number of tests
  running in CI. If you use this setting you may wish to raise timeout and max_examples.
* database - specify the database object you wish to use. See next section
  for what this means.

~~~~~~~~~~~~
The Database
~~~~~~~~~~~~

Hypothesis stores examples for reuse the next time you run your test suite (or
inded for other tests in the same run). It attaches them to the type of the arguments
rather than the test, so if for example you had two tests with @given(int, int)
then these two would share the same pool of shared examples. This is a deliberate
design choice: Generally if an example provokes a failure in one test it is in
some sense "interesting" and thus is a good choice to try for other similar tests.

A Hypothesis database is an instance of hypothesis.database.ExampleDatabase. It
knows how to save most common types, and custom serializations can be defined if
you need them.

The feature is not on by default as randomly creating a database for you would
be surprising behaviour, but it's easy to turn on.


.. code:: python

    from hypothesis.database import ExampleDatabase
    import hypothesis.settings as hs

    # This will create an in memory database. Examples will be shared between
    # tests in the current run but will not be persisted to disk
    hs.default.database = ExampleDatabase()

    # This will create an on-disk database that will be used across runs at the
    # specified path
    from hypothesis.database.backend import SQLiteBackend
    hs.default.database = ExampleDatabase(
        backend=SQLiteBackend('/path/to/my/example.db')
    )

You can also set this by setting the environment variable HYPOTHESIS_DATABASE_FILE=/path/to/my/example.db

This uses the default format (and the only one supported out of the box), which is
a simple subset of JSON stored in an SQLite database. However the storage API is
very straight forward (it's a key: unique multi value store) and it's easy to define other backends if you want to for operational reasons
(e.g. having a common DB server storing your values across multiple runs).

If you want to write your own serializers it's not too hard to do so, but for
now the best documentation on how is I'm afraid `the source code <https://github.com/DRMacIver/hypothesis/blob/master/src/hypothesis/database/converter.py>`_.

Generally the example database should be entirely transparent: The only thing
you should see is that Hypothesis gets a lot better at consistently finding
examples. Some types are not serializable and will not be stored in the database.
However the feature is quite new and somewhat experimental, so although it has
been well tested you can probably expect there to be some bugs lurking in there.


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
    Out[7]: [('add', 1), ('add', 1), ('remove', 1)]

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

This strategy is going to wrap some strategy for producing integers. Pack takes
an integer and returns a Decimal and unpack takes a Decimal and returns an integer.

You then need to register this strategy so that when you just refer to Decimal,
Hypothesis knows that this is the one you intend to use:

.. code:: python

    from hypothesis.strategytable import StrategyTable
    StrategyTable.default().define_specification_for(
      Decimal,
      lambda s, d: DecimalStrategy(
        strategy=s.strategy(float),
        descriptor=Decimal,
      ))

Given a StrategyTable x, this means that when you call x.strategy(Decimal), this will
call your lambda as f(x, Decimal), which will build the relevant strategy.

Note that it's important that pack returns a decimal here. A descriptor can be anything
you like, but if it's not the type of the things you are returning then you may have problems.

For example:

.. code:: python

    from hypothesis.searchstrategy import MappedSearchStrategy
    class smallint(int):
      pass

    class SmallintStrategy(MappedSearchStrategy):
        def pack(self, x):
            return min(abs(x), 100)

        def unpack(self, x):
            return x


(Note: This is a silly example chosen for simplicity. You should use integers_in_range(0, 100) for this)

If you try to use the above strategy you will get errors! The problem is that
the values produced by a strategy (in the case of a MappedSearchStrategy these
will be the values returned by pack) have to return True when passed to the could_have_produced method
of that strategy.

You can fix this in one of two ways. You could either return something of the right type:

.. code:: python

    from hypothesis.searchstrategy import MappedSearchStrategy
    class smallint(int):
      pass

    class SmallintStrategy(MappedSearchStrategy):
        def pack(self, x):
            return smallint(min(abs(x), 100))

        def unpack(self, x):
            return x


Or if this is difficult for some reason you can also override could_have_produced instead:

.. code:: python

    from hypothesis.searchstrategy import MappedSearchStrategy
    class smallint(int):
      pass

    class SmallintStrategy(MappedSearchStrategy):
        def pack(self, x):
            return smallint(min(abs(x), 100))

        def unpack(self, x):
            return x

        def could_have_produced(self, value):
            return isinstance(value, int)


Descriptors can be anything you like as long as you're willing to define that
custom could_have_produced.

Once you've defined your custom type, there is a standard test suite you can use
to validate that your implementation is correct.


.. code:: python

    from hypothesis.descriptortests import descriptor_test_suite

    TestSmallint = descriptor_test_suite(smallint)


This is a unittest.TestCase. You can either run it explicitly or let pytest or
similar pick it up automatically. It will run a battery of standard tests against
your implementation to check that it is correct.

-------------------------
Hypothesis extra packages
-------------------------

Hypothesis avoids dependencies in the core package, so there's a notion of extra
packages which are basically Hypothesis + one or more dependencies. So far there are
two:

* hypothesis-datetime: Gives you datetime support, depends on pytz
* hypothesis-pytest: A pytest plugin for better reporting, depends on pytest


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

This version of hypothesis has been tested on OSX, Windows and Linux using CPython 2.7, 3.2,
3.3, 3.4 and Pypy 2.5.0.  Builds are checked with `Travis <https://travis-ci.org/>`_ and `Appveyor <https://appveyor.com>`_.

------------
Contributing
------------

I'm not incredibly keen on external contributions prior to the 1.0 release. I think you're going to have a hard time of it.

In the meantime I'd rather you do any of the following

* Submit bug reports
* Submit feature requests
* Write about Hypothesis
* Build libraries and tools on top of Hypothesis outside the main repo

If you need any help with any of these, get in touch and I'll be extremely happy to provide it.

However if you really really want to submit code to Hypothesis, the process is as follows:

You must own the copyright to the patch you're submitting as an individual. I'm not currently clear on how to accept patches from organisations and other legal entities.

If you have not already done so, you must sign a CLA assigning copyright to me. Send an email to hypothesis@drmaciver.com with
an attached copy of `the current version of the CLA <https://github.com/DRMacIver/hypothesis/blob/master/docs/Hypothesis-CLA.pdf?raw=true>`_
and the text in the body "I, (your name), have read the attached CLA and agree to its terms" (you should in fact have actually read it).
Note that it's important to attach a copy of the CLA because I may change it from time to time as new things come up and this keeps a record of
which version of it you agreed to.

Then submit a pull request on Github. This will be checked by Travis and Appveyor to see if the build passes.

Advance warning that passing the build requires:

1. Really quite a lot of tests to pass (it looks like it's only 600+ but many of these use Hypothesis itself to run 1000 examples through them, and the build is run in 4 configurations across 16 different OS/python version combinations).
2. Your code to have 100% branch coverage.
3. Your code to be flake8 clean.
4. Your code to be a fixed point for a variety of reformatting operations (defined in lint.sh)

It is a fairly strict process.

(Unfortunately right now the build is also a bit flaky. I'm working on fixing that, but in the meantime if a test fails and you don't understand why you should probably just run the build again to see what happens. Sorry)

Once all this has happened I'll review your patch. I don't promise to accept it, but I do promise to review it as promptly as I can and to tell you why if I reject it.
