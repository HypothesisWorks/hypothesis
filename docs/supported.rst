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

Hypothesis is supported and tested on python 2.7
and python 3.3+. Python 3.0 through 3.2 are unsupported and definitely don't work.
It's not infeasible to make them work but would need a very good reason.

Python 2.6 and 3.3 are supported on a "best effort" basis. They probably work,
and bugs that affect them *might* get fixed.

Hypothesis also supports PyPy (PyPy3 does not work because it only runs 3.2 compatible
code, but if and when there's a 3.3 compatible version it will be supported), and
should support 32-bit and narrow builds, though this is currently only tested on Windows.

Hypothesis does not currently work on Jython (it requires sqlite), though could feasibly
be made to do so. IronPython might work but hasn't been tested.

In general Hypothesis does not officially support anything except the latest
patch release of any version of Python it supports. Earlier releases should work
and bugs in them will get fixed if reported, but they're not tested in CI and
no guarantees are made.

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

If your testing relies on doing something other than calling a function and seeing
if it raises an exception then it probably *won't* work out of the box. In particular
things like tests which return generators and expect you to do something with them
(e.g. nose's yield based tests) will not work. Use a decorator or similar to wrap the
test to take this form.

In terms of what's actually *known* to work:

  * Hypothesis integrates as smoothly with py.test and unittest as I can make it,
    and this is verified as part of the CI.
  * py.test fixtures work correctly with Hypothesis based functions, but note that
    function based fixtures will only run once for the whole function, not once per
    example.
  * Nose has been tried at least once and works fine, and I'm aware of people who
    use Hypothesis with Nose, but this isn't tested as part of the CI. yield based
    tests simply won't work.
  * Integration with Django's testing requires use of the :ref:`hypothesis-django` package.
    The issue is that in Django's tests' normal mode of execution it will reset the
    database one per test rather than once per example, which is not what you want.

Coverage works out of the box with Hypothesis (and Hypothesis has 100% branch
coverage in its own tests). However you should probably not use Coverage, Hypothesis
and PyPy together. Because Hypothesis does quite a lot of CPU heavy work compared
to normal tests, it really exacerbates the performance problems the two normally
have working together.

---------------
Django Versions
---------------

The Hypothesis Django integration is supported on 1.7 and 1.8. It will probably
not work on versions prior to that.

------------------------
Regularly verifying this
------------------------

Everything mentioned above as explicitly supported is checked on every commit 
with `Travis <https://travis-ci.org/>`_ and `Appveyor <http://www.appveyor.com>`_
and goes green before a release happens, so when I say they're supported I really
mean it.
