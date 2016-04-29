====================
Packaging Guidelines
====================

Downstream packagers often want to package Hypothesis. Here are some guidelines.

The primary guideline is this: If you are not prepared to keep up with the Hypothesis release schedule,
don't. You will annoy me and are doing your users a disservice.

Hypothesis has quite a frequent release schedule. It's very rare that it goes a month without a release,
and there are often multiple releases in a given month.

Many people not only fail to follow the release schedule but also seem included to package versions
which are months out of date even at the point of packaging. This will cause me to be very annoyed with you and
you will consequently get very little co-operation from me.

If you *are* prepared to keep up with the Hypothesis release schedule, the rest of this document outlines
some information you might find useful.

----------------
Release tarballs
----------------

These are available from `the GitHub releases page <https://github.com/HypothesisWorks/hypothesis-python/releases>`_. The
tarballs on pypi are intended for installation from a Python tool such as pip or easy_install and should not
be considered complete releases. Requests to include additional files in them will not be granted. Their absence
is not a bug.


------------
Dependencies
------------

~~~~~~~~~~~~~~~
Python versions
~~~~~~~~~~~~~~~

Hypothesis is designed to work with a range of Python versions. Currently supported are:

* pypy-2.6.1 (earlier versions of pypy *may* work)
* CPython 2.7.x
* CPython 3.4.x
* CPython 3.5.x

If you feel the need to have separate Python 3 and Python 2 packages you can, but Hypothesis works unmodified
on either.

~~~~~~~~~~~~~~~~~~~~~~
Other Python libraries
~~~~~~~~~~~~~~~~~~~~~~

Hypothesis has *optional* dependencies on the following libraries:

* pytz (almost any version should work)
* fake-factory (0.5.2 or 0.5.3)
* Django, 1.7 through 1.9 (This requires fake-factory to be installed)
* numpy, 1.10.x (earlier versions will probably work fine)
* py.test (2.7.0 or greater). This is a mandatory dependency for testing Hypothesis itself but optional for users.

The way this works when installing Hypothesis normally is that these features become available if the relevant
library is installed.

------------------
Testing Hypothesis
------------------

If you want to test Hypothesis as part of your packaging you will probably not want to use the mechanisms
Hypothesis itself uses for running its tests, because it has a lot of logic for installing and testing against
different versions of Python.

The tests must be run with py.test. A version more recent than 2.7.0 is strongly encouraged, but it may work
with earlier versions (however py.test specific logic is disabled before 2.7.0).

Tests are organised into a number of top level subdirectories of the tests/ directory.

* cover: This is a small, reasonably fast, collection of tests designed to give 100% coverage of all but a select
  subset of the files when run under Python 3.
* nocover: This is a much slower collection of tests that should not be run under coverage for performance reasons.
* py2: Tests that can only be run under Python 2
* py3: Tests that can only be run under Python 3
* datetime: This tests the subset of Hypothesis that depends on pytz
* fakefactory: This tests the subset of Hypothesis that depends on fakefactory.
* django: This tests the subset of Hypothesis that depends on django (this also depends on fakefactory).


An example invocation for running the coverage subset of these tests:

.. code-block:: bash

  python setup.py install
  pip install pytest # you will probably want to use your own packaging here
  python -m pytest tests/cover

--------
Examples
--------

* `arch linux <https://www.archlinux.org/packages/community/any/python-hypothesis/>`_
* `gentoo <https://packages.gentoo.org/packages/dev-python/hypothesis>`_ (slightly behind at the time of this writing)

Other distros appear to really like Hypothesis 1.11. I do not encourage following their example.
