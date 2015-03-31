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

------------
Known issues
------------

Here are some known issues that you may need to work around when using
Hypothesis on some platform combinations. Do let me know if you encounter any
others.

-------------------------------------------
Windows, Python 2.7 and non-ascii filenames
-------------------------------------------

Some programs may experience issues if you try to use Hypothesis inside a
directory with a non-ascii character in the file path under python 2.7.
This will cause Hypothesis to add a unicode object to the sys.path, which
some programs which invoke subprocesses cannot correctly handle (this
behaviour is valid but may not always be handled correctly).

If you are unable to fix the programs and need to run in a directory with
a unicode filepath for some reason (e.g. a non-ascii username) then you can
work around this by changing the Hypothesis storage directory so that it is
in an ascii location. You can do this in one of two ways:

1. Set the HYPOTHESIS_STORAGE_DIRECTORY environment variable to the new location
2. Call hypothesis.settings.set_hypothesis_home_dir( ) with the new location.

This problem should not affect Python 3, which has much more sensible unicode
behaviour, or non-Windows platforms, which do not experience a problem with
passing a unicode environment to subprocesses.

-------
FreeBSD
-------

Hypothesis will not work correctly with just the basic python package
installed. You also need to install python-sqlite.

------------------------
Regularly verifying this
------------------------

Every supported version of Python and supported platform has CI builds happening
on every commit, and must be green for a release. This is done with 
with `Travis <https://travis-ci.org/>`_ and `Appveyor <https://appveyor.com>`_.

A mix of combinatorics and difficulty of setup means that not every pairwise
combination is tested. For example pypy is not currently tested on windows,
and 32-bit builds of Python are *only* tested on Windows. These should still
work, but the possibility of interactions that were not caught on the CI means
that bugs are more likely. I'll try to set up CI for any combinations that
exhibit a novel bug, but no promises (particularly if it's not one of Windows,
OSX or Linux, which I have access to free CI servers for).
