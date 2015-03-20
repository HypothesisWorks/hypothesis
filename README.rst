================
 Hypothesis
================

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

Hypothesis is not itself a testing framework, and should play nicely with your
existing one. Development and testing of Hypothesis itself is done with `Pytest <http://pytest.org/>`_,
but pytest is not a dependency and Hypothesis should work with just about
anything.

If you want to learn more about how to use Hypothesis, comprehensive
documentation is `available at readthedocs <http://hypothesis.readthedocs.org/en/master/>`_.

There is also `a separate document describing some of the internals <http://hypothesis.readthedocs.org/en/master/internals.html>`_,
mostly for the benefit of people who are interested in porting Hypothesis to
other languages, but it may be of general interest.

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


---------
Stability
---------

Hypothesis should be considered fairly stable.

It's highly stable in the sense that it should mostly work very well. It's extremely solidly tested and while
there are almost certainly bugs lurking in it, as with any non-trivial codebase, they should be few and far
between.

For the moment, until 1.0 is reached, the API may still be prone to breaking
between minor releases, but the 0.7 release should be considered as very close
to the final version and it's unlikely that anything will break very much
between now and 1.0.

------------------
Supported versions
------------------

2.7.x, 3.2.x, 3.3.x and 3.4.x, as well as both pypy-2.5.0 and pypy3-2.5.0 are
all fully supported and tested on.

Builds are checked with `Travis <https://travis-ci.org/>`_ and `Appveyor <https://appveyor.com>`_.

Versions of Python earlier than 2.7 will not work and will probably never be
supported. Jython and IronPython might work but I haven't checked and will
probably only fix bugs with them if it's really easy to do so.

------------
Contributing
------------

External contributions to Hypothesis are currently less easy than I would like
them to be. You might want to consider any of the following in preference to
trying to work on the main Hypothesis code base:

* Submit bug reports
* Submit feature requests
* Write about Hypothesis
* Build libraries and tools on top of Hypothesis outside the main repo

And indeed I'll be delighted with you if you do! If you need any help with any
of these, get in touch and I'll be extremely happy to provide it.

However if you really really want to submit code to Hypothesis, the process is
as follows:

You must own the copyright to the patch you're submitting as an individual.
I'm not currently clear on how to accept patches from organisations and other
legal entities.

If you have not already done so, you must sign a CLA assigning copyright to me.
Send an email to hypothesis@drmaciver.com with an attached copy of
`the current version of the CLA <https://github.com/DRMacIver/hypothesis/blob/master/docs/Hypothesis-CLA.pdf?raw=true>`_
and the text in the body "I, (your name), have read the attached CLA and agree
to its terms" (you should in fact have actually read it).

Note that it's important to attach a copy of the CLA because I may change it
from time to time as new things come up and this keeps a record of which
version of it you agreed to.

Then submit a pull request on Github. This will be checked by Travis and
Appveyor to see if the build passes.

Advance warning that passing the build requires:

1. All the tests to pass, naturally.
2. Your code to have 100% branch coverage.
3. Your code to be flake8 clean.
4. Your code to be a fixed point for a variety of reformatting operations (defined in lint.sh)

It is a fairly strict process.

Once all this has happened I'll review your patch. I don't promise to accept
it, but I do promise to review it as promptly as I can and to tell you why if
I reject it.
