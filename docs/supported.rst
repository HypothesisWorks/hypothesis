=============
Compatibility
=============

Hypothesis does its level best to be compatible with everything you could
possibly need it to be compatible with. Generally you should just try it and
expect it to work. If it doesn't, you can be surprised and check this document
for the details.

---------------
Python versions
---------------

Hypothesis has quite wide version support. It is supported and tested on python 2.7
and python 3.2+. Supporting 3.0 or 3.1 wouldn't be infeasible but I'd need a good
reason to. Supporting python before 2.7 isn't going to happen.

Hypothesis also support pypy (pypy3 should also work but isn't part of
the CI at the moment), and should support 32-bit and narrow builds, though
this is currently only tested on Windows.

No testing has been performed on Jython or IronPython. It might work but I'd
be surprised. Let me know if you need these supported. It might be possible
but I make no promises.

-----------------
Operating systems
-----------------

In theory Hypothesis should work anywhere that Python does. In practice it is
only known to work and regularly tested on OSX, Windows and Linux, and you may
experience issues running it elsewhere. For example a known issue is that FreeBSD
splits out the python-sqlite package from the main python package, and you will
need to install that in order for it to work.

If you're using something else and it doesn't work, do get in touch and I'll try
to help, but unless you can come up with a way for me to run a CI server on that
operating system it probably won't stay fixed due to the inevitable march of time.

------------------
Testing frameworks
------------------

In general Hypothesis goes to quite a lot of effort to generate things that
look like normal Python test functions that behave as closely to the originals
as possible, so it should work sensibly out of the box with every test framework.

In terms of what's actually *known* to work:

  * Hypothesis integrates as smoothly with py.test and unittest as I can make it,
    and this is verified as part of the CI.
  * Nose has been tried at least once and works fine, and I'm aware of people who
    use Hypothesis with Nose, but this isn't tested as part of the CI.
  * Django unit testing doesn't work entirely well with Hypothesis at the moment
    but proper support is coming. Right now the issue is that the database will
    be reset once per test rather than once per example, which is not what you
    want.

Coverage works out of the box with Hypothesis (and Hypothesis has 100% branch
coverage in its own tests). However you should probably not use Coverage, Hypothesis
and pypy together. Because Hypothesis does quite a lot of CPU heavy work compared
to normal tests it really exacerbates 

------------------------
Regularly verifying this
------------------------

Everything mentioned above as explicitly supported is checked on every commit 
with `Travis <https://travis-ci.org/>`_ and `Appveyor <https://appveyor.com>`_
and goes green before a release happens, so when I say they're supported I really
mean it.
