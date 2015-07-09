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
reason to. Python 2.6 is supported on a "best effort" basis. It is supported in the 1.7.x
versions of Hypothesis and will most likely continue being supported through all of the 1.x
versions, however I'm not committing to that.

Hypothesis also supports PyPy (PyPy3 should also work but isn't part of
the CI at the moment), and should support 32-bit and narrow builds, though
this is currently only tested on Windows.

No testing has been performed on Jython or IronPython. It might work but I'd
be surprised. Let me know if you need these supported. It might be possible
but I make no promises.

-----------------
Operating systems
-----------------

In theory Hypothesis should work anywhere that Python does. In practice it is
only known to work and regularly tested on OS X, Windows and Linux, and you may
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
  * Integration with Django's testing requires use of the :ref:`hypothesis-django` package.
    The issue is that in Django's tests' normal mode of execution it will reset the
    database one per test rather than once per example, which is not what you want.

Coverage works out of the box with Hypothesis (and Hypothesis has 100% branch
coverage in its own tests). However you should probably not use Coverage, Hypothesis
and PyPy together. Because Hypothesis does quite a lot of CPU heavy work compared
to normal tests, it really exacerbates the performance problems the two normally
have working together.

------------------------
Regularly verifying this
------------------------

Everything mentioned above as explicitly supported is checked on every commit 
with `Travis <https://travis-ci.org/>`_ and `Appveyor <http://www.appveyor.com>`_
and goes green before a release happens, so when I say they're supported I really
mean it.
