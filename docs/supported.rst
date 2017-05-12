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

Hypothesis is supported and tested on CPython 2.7 and CPython 3.4+.

Hypothesis also supports PyPy2, and will support PyPy3 when there is a stable
release supporting Python 3.4+.  Hypothesis does not currently work on Jython,
though could feasibly be made to do so. IronPython might work but hasn't been
tested.  32-bit and narrow builds should work, though this is currently only
tested on Windows.

In general Hypothesis does not officially support anything except the latest
patch release of any version of Python it supports. Earlier releases should work
and bugs in them will get fixed if reported, but they're not tested in CI and
no guarantees are made.

-----------------
Operating systems
-----------------

In theory Hypothesis should work anywhere that Python does. In practice it is
only known to work and regularly tested on OS X, Windows and Linux, and you may
experience issues running it elsewhere.

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
  * Nose works fine with hypothesis, and this is tested as part of the CI. yield based
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
with `Travis <https://travis-ci.org/HypothesisWorks/hypothesis-python>`_ and
`Appveyor <https://ci.appveyor.com/project/DRMacIver/hypothesis-python/>`_
and goes green before a release happens, so when I say they're supported I
really mean it.

-------------------
Hypothesis versions
-------------------

Backwards compatibility is better than backporting fixes, so we use
:ref:`semantic versioning <release-policy>` and only support the most recent
version of Hypothesis.  See :doc:`support` for more information.
